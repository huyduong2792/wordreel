"""
Admin API endpoints for content management
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from tasks.crawler_tasks import download_video_task
import structlog

logger = structlog.get_logger()

router = APIRouter()


class CrawlRequest(BaseModel):
    """Request to crawl a video"""
    source_url: str
    title: str | None = None


class CrawlResponse(BaseModel):
    """Response from crawl request"""
    status: str
    message: str
    task_id: str | None = None


@router.post("/crawl", response_model=CrawlResponse)
async def crawl_video(request: CrawlRequest):
    """
    Trigger video crawling from external source.

    Supported platforms:
    - TikTok
    - YouTube
    - Instagram

    The video will be downloaded, processed (subtitles + quiz generated),
    and saved to the posts table.
    """
    try:
        logger.info("Crawl request received", source_url=request.source_url)

        # Queue the download task
        task = download_video_task.delay(
            source_url=request.source_url,
            title=request.title
        )

        return CrawlResponse(
            status="queued",
            message=f"Video crawl task queued. Check task status or wait for processing.",
            task_id=task.id
        )

    except Exception as e:
        logger.error("Failed to queue crawl task", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue crawl task: {str(e)}"
        )
