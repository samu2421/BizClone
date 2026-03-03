"""
Celery application configuration for background task processing.
"""
from celery import Celery
from app.config.settings import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "bizclone",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Reject task if worker dies
    result_expires=3600,  # Results expire after 1 hour
)

# Task routing
celery_app.conf.task_routes = {
    "app.workers.tasks.transcribe_audio_task": {"queue": "transcription"},
    "app.workers.tasks.process_transcript_task": {"queue": "processing"},
}

logger.info(
    "celery_app_configured",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

