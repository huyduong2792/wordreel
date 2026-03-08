"""
Celery configuration and task queue setup
"""
from celery import Celery
from config import get_settings

settings = get_settings()

# Initialize Celery
celery_app = Celery(
    "wordreel",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.crawler_tasks"  # Video crawling and content processing
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3000,  # 50 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Task routes
celery_app.conf.task_routes = {
    "tasks.crawler_tasks.*": {"queue": "crawler"},
}

if __name__ == "__main__":
    celery_app.start()
