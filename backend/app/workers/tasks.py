from __future__ import annotations

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.services.followup_service import due_jobs, run_followup
from app.workers.celery_app import celery

log = get_logger(__name__)


@celery.task(name="app.workers.tasks.run_due_followups")
def run_due_followups() -> dict:
    """Sweep ScheduledJob rows where run_at <= now and status == pending."""
    db = SessionLocal()
    processed = 0
    try:
        for job in due_jobs(db):
            try:
                run_followup(db, job)
                processed += 1
            except Exception as e:
                log.exception("followup_failed", job_id=str(job.id), err=str(e))
        db.commit()
    except Exception as e:
        db.rollback()
        log.exception("run_due_followups_failed", err=str(e))
    finally:
        db.close()
    return {"processed": processed}
