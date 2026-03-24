"""
Celery tasks for video crawling and downloading
Uses dependency injection via ServiceContainer
Saves to posts table with content_type='video'
"""
import os
import tempfile
from typing import Optional
from datetime import datetime
import yt_dlp
from celery import Task
from celery_app import celery_app
from database.supabase_client import get_service_supabase
from services.container import get_container, ServiceContainer
from services.video_sources import VideoSourceFactory
from models.schemas import PostStatus, ContentType
from config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


class CrawlerTask(Task):
    """
    Base task for video crawling with dependency injection.
    Services are lazily loaded and reused across task executions.
    """
    _container: Optional[ServiceContainer] = None
    
    @property
    def container(self) -> ServiceContainer:
        """Get service container (singleton per worker)"""
        if self._container is None:
            self._container = get_container()
        return self._container
    
    @property
    def content_processor(self):
        """Get content processor from container"""
        return self.container.content_processor
    
    @property
    def tus_client(self):
        """Get TUS client from container"""
        return self.container.tus_client


@celery_app.task(
    base=CrawlerTask,
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def download_video_task(
    self,
    source_url: str,
    title: Optional[str] = None,
    user_id: Optional[str] = None
):
    """
    Download video from external source and process it.
    
    Flow:
    1. Download video using yt-dlp
    2. Process content (subtitles + quiz) via ContentProcessor
    3. Upload to cloud via TUS
    4. Save everything to database
    """
    supabase = get_service_supabase()
    source_factory = VideoSourceFactory()
    temp_video_path = None
    
    try:
        logger.info("Starting video download", source_url=source_url)
        
        # Check if post already exists to prevent duplicates
        existing = supabase.table("posts").select("id").eq("source_url", source_url).execute()
        if existing.data:
            logger.info("Post already exists, skipping", source_url=source_url, post_id=existing.data[0]['id'])
            return {
                "status": "skipped",
                "reason": "duplicate",
                "post_id": existing.data[0]['id']
            }
        
        # Get appropriate source handler
        source_handler = source_factory.get_source(source_url)
        if not source_handler:
            raise Exception(f"Unsupported video source: {source_url}")
        
        platform = source_handler.get_platform_name()
        logger.info("Using source handler", platform=platform)
        
        # Configure yt-dlp with platform-specific options
        temp_video_path = tempfile.mktemp(suffix=".mp4")
        ydl_opts = source_handler.get_download_options(temp_video_path)
        
        # Download video
        logger.info("Downloading video", platform=platform)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source_url, download=True)
            metadata = source_handler.extract_metadata(info)
        
        # Override title if provided
        if title:
            metadata['title'] = title
        
        logger.info("Video downloaded, processing content")
        
        # Process video using ContentProcessor (DI)
        result = self.content_processor.process_video(
            video_path=temp_video_path,
            language="en",
            generate_quiz=True,
            video_title=metadata['title']
        )
        
        metadata['duration'] = result.duration
        
        # Upload to cloud provider via TUS
        now = datetime.now()
        filename = f"{platform}_{hash(source_url)}.mp4"
        file_path = f"/{now.year}/{now.month:02d}/{now.day:02d}/{filename}"
        
        logger.info("Uploading to cloud via TUS", file_path=file_path)
        
        # Use upload_file_sync with file path for better reliability
        # This also verifies the video has both video and audio streams
        upload_result = self.tus_client.upload_file_sync(
            file_path=temp_video_path,
            metadata={
                "file_path": file_path,
                "dash_qualities": "360,720",
                "hls_qualities": "720",
                "creator": metadata.get('creator', 'crawler'),
                "creator_name": metadata.get('creator_name', 'crawler'),
                "default_thumb_timepct": "0,5",
                "source_url": source_url,
                "platform": platform
            },
            verify_video=True  # Verify video has both audio and video streams
        )
        
        cloud_urls = self.tus_client.get_cloud_urls(upload_result.get("file_path", file_path))
        
        logger.info("Upload completed", video_url=cloud_urls["video_url"])
        
        # Cleanup temp file
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
            temp_video_path = None
        
        # Save to database (including embedding for recommendations)
        post_id = _save_to_database(
            supabase=supabase,
            metadata=metadata,
            cloud_urls=cloud_urls,
            source_url=source_url,
            user_id=user_id,
            subtitles_data=result.subtitles,
            quiz_questions=result.quiz_questions,
            tags=result.tags,
            embedding=result.embedding
        )
        
        logger.info(
            "Video crawl completed", 
            post_id=post_id, 
            source_url=source_url,
            platform=platform
        )
        
        return {
            "status": "success",
            "post_id": post_id,
            "source_url": source_url,
            "platform": platform
        }
        
    except Exception as e:
        logger.error("Video download failed", source_url=source_url, error=str(e))
        
        # Cleanup
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        
        raise self.retry(exc=e)


def _save_to_database(
    supabase,
    metadata: dict,
    cloud_urls: dict,
    source_url: str,
    user_id: Optional[str],
    subtitles_data: list,
    quiz_questions: Optional[list],
    tags: Optional[list] = None,
    embedding: Optional[list] = None
) -> str:
    """Save post (video), subtitles, quiz, and embedding to database"""
    
    # Use extracted tags if available, fallback to metadata tags
    final_tags = tags if tags else metadata.get('tags', [])
    
    # Create post record with content_type='video'
    post_data = {
        "title": metadata['title'],
        "description": metadata.get('description'),
        "content_type": ContentType.VIDEO.value,
        "video_url": cloud_urls["video_url"],
        "hls_url": cloud_urls["hls_url"],
        "dash_url": cloud_urls["dash_url"],
        "thumbnail_url": cloud_urls["thumbnail_url"],
        "source_url": source_url,
        "duration": metadata.get('duration', 0),
        "status": PostStatus.READY.value,
        "tags": final_tags,
        "topic": final_tags[0] if final_tags else None,
        "creator_name": metadata.get('creator_name'),
        "user_id": user_id,
        "difficulty_level": "beginner",
        "views_count": 0,
        "likes_count": 0,
        "embedding": embedding  # Vector for AI recommendations
    }
    
    result = supabase.table("posts").insert(post_data).execute()
    
    if not result.data:
        raise Exception("Failed to create post record")
    
    post_id = result.data[0]["id"]
    
    # Save subtitles
    subtitle_record = {
        "post_id": post_id,
        "language": "en",
        "subtitles": subtitles_data
    }
    supabase.table("subtitles").insert(subtitle_record).execute()
    logger.info("Subtitles saved", post_id=post_id)
    
    # Save quiz if generated
    if quiz_questions:
        quiz_data = {
            "post_id": post_id,
            "questions": [q.dict() for q in quiz_questions],
            "total_points": sum(q.points for q in quiz_questions)
        }
        supabase.table("quizzes").insert(quiz_data).execute()
        logger.info("Quiz saved", post_id=post_id)
    
    return post_id



