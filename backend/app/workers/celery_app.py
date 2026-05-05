from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery = Celery(
    "medspa",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Beat schedule: every minute sweep for due follow-up jobs.
celery.conf.beat_schedule = {
    "run-due-followups": {
        "task": "app.workers.tasks.run_due_followups",
        "schedule": crontab(minute="*"),
    },
}
