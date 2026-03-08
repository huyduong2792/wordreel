"""
Celery tasks for subtitle and quiz generation
Handles video and audio content processing
"""
import os
import tempfile
import httpx
from typing import Optional
from celery_app import celery_app
from database.supabase_client import get_service_supabase
from services.container import get_content_processor
from models.schemas import PostStatus
import structlog

logger = structlog.get_logger()


@celery_app.task(max_retries=3, default_retry_delay=120)
def generate_subtitles_and_quiz_task(
    post_id: str,
    media_url: str,
    content_type: str = "video"
):
    """
    Generate subtitles, quiz, tags, and embedding for a video or audio post.
    
    Args:
        post_id: UUID of the post
        media_url: URL to the video or audio file
        content_type: 'video' or 'audio'
    """
    supabase = get_service_supabase()
    content_processor = get_content_processor()
    temp_file = None
    
    try:
        logger.info(
            "Starting content processing",
            post_id=post_id,
            content_type=content_type
        )
        
        # Update status to transcribing
        supabase.table("posts").update({
            "status": PostStatus.TRANSCRIBING.value
        }).eq("id", post_id).execute()
        
        # Get post data for title
        post_response = supabase.table("posts").select("title").eq(
            "id", post_id
        ).execute()
        
        title = "Untitled"
        if post_response.data:
            title = post_response.data[0].get("title", "Untitled")
        
        # Download media file
        suffix = ".mp4" if content_type == "video" else ".mp3"
        temp_file = tempfile.mktemp(suffix=suffix)
        
        logger.info("Downloading media", url=media_url[:100])
        
        with httpx.Client(timeout=300) as client:
            response = client.get(media_url)
            response.raise_for_status()
            
            with open(temp_file, "wb") as f:
                f.write(response.content)
        
        logger.info("Media downloaded, processing")
        
        # Process content
        result = content_processor.process_video(
            video_path=temp_file,
            language="en",
            generate_quiz=True,
            generate_embedding=True,
            video_title=title
        )
        
        # Save subtitles
        if result.subtitles:
            subtitle_record = {
                "post_id": post_id,
                "language": "en",
                "subtitles": result.subtitles
            }
            supabase.table("subtitles").insert(subtitle_record).execute()
            logger.info("Subtitles saved", post_id=post_id, count=len(result.subtitles))
        
        # Save quiz
        if result.quiz_questions:
            quiz_data = {
                "post_id": post_id,
                "questions": [q.dict() for q in result.quiz_questions],
                "total_points": sum(q.points for q in result.quiz_questions)
            }
            supabase.table("quizzes").insert(quiz_data).execute()
            logger.info("Quiz saved", post_id=post_id, questions=len(result.quiz_questions))
        
        # Update post with duration, tags, embedding, and status
        update_data = {
            "status": PostStatus.READY.value,
            "duration": result.duration,
            "tags": result.tags if result.tags else []
        }
        
        if result.embedding:
            update_data["embedding"] = result.embedding
        
        supabase.table("posts").update(update_data).eq("id", post_id).execute()
        
        logger.info(
            "Content processing complete",
            post_id=post_id,
            content_type=content_type,
            duration=result.duration
        )
        
        return {
            "status": "success",
            "post_id": post_id,
            "subtitles_count": len(result.subtitles) if result.subtitles else 0,
            "quiz_questions": len(result.quiz_questions) if result.quiz_questions else 0
        }
        
    except Exception as e:
        logger.error(
            "Content processing failed",
            post_id=post_id,
            error=str(e)
        )
        
        # Update status to failed
        supabase.table("posts").update({
            "status": PostStatus.FAILED.value
        }).eq("id", post_id).execute()
        
        raise
        
    finally:
        # Cleanup temp file
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)


@celery_app.task(max_retries=3, default_retry_delay=60)
def regenerate_subtitles_task(post_id: str):
    """
    Regenerate subtitles for an existing post.
    Useful when transcription quality needs improvement.
    """
    supabase = get_service_supabase()
    
    try:
        # Get post details
        post = supabase.table("posts").select(
            "id, content_type, video_url, audio_url, title"
        ).eq("id", post_id).execute()
        
        if not post.data:
            logger.error("Post not found", post_id=post_id)
            return {"status": "error", "message": "Post not found"}
        
        post_data = post.data[0]
        content_type = post_data.get("content_type")
        
        if content_type not in ["video", "audio"]:
            return {"status": "skipped", "message": "Content type does not support subtitles"}
        
        media_url = post_data.get("video_url") or post_data.get("audio_url")
        
        if not media_url:
            return {"status": "error", "message": "No media URL found"}
        
        # Delete existing subtitles
        supabase.table("subtitles").delete().eq("post_id", post_id).execute()
        
        # Regenerate
        return generate_subtitles_and_quiz_task(post_id, media_url, content_type)
        
    except Exception as e:
        logger.error("Subtitle regeneration failed", post_id=post_id, error=str(e))
        raise
