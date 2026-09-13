import logging
import os
import time
from datetime import timedelta

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Job, utc_now
from worker.executor import execute


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
POLL_SECONDS = float(os.getenv("POLL_SECONDS", "1"))
JOB_TIMEOUT_SECONDS = int(os.getenv("JOB_TIMEOUT_SECONDS", "60"))


def retry_or_fail(job: Job, reason: str, now):
    job.error = reason
    job.locked_at = None
    if job.attempt_count < job.max_attempts:
        job.status = "queued"
        job.available_at = now + timedelta(seconds=5 * (2 ** (job.attempt_count - 1)))
        job.started_at = None
    else:
        job.status = "failed"
        job.finished_at = now


def recover_stale_jobs():
    cutoff = utc_now() - timedelta(seconds=JOB_TIMEOUT_SECONDS)
    with SessionLocal.begin() as session:
        stale = session.scalars(
            select(Job)
            .where(Job.status == "running", Job.locked_at < cutoff)
            .with_for_update(skip_locked=True)
        ).all()
        for job in stale:
            retry_or_fail(job, "Worker timeout or crash", utc_now())
            logger.warning("Recovered stale job %s: %s", job.id, job.status)


def claim_job():
    with SessionLocal.begin() as session:
        job = session.scalar(
            select(Job)
            .where(Job.status == "queued", Job.available_at <= utc_now())
            .order_by(Job.priority.desc(), Job.created_at.asc(), Job.id.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return None
        now = utc_now()
        job.status = "running"
        job.attempt_count += 1
        job.started_at = now
        job.locked_at = now
        job.error = None
        return job.id, job.payload, job.attempt_count


def finish_job(job_id, attempt, result=None, error=None):
    with SessionLocal.begin() as session:
        job = session.get(Job, job_id, with_for_update=True)
        if job.status != "running" or job.attempt_count != attempt:
            return
        if error is None:
            job.status = "succeeded"
            job.result = result
            job.error = None
            job.finished_at = utc_now()
            job.locked_at = None
        else:
            retry_or_fail(job, str(error), utc_now())


def main():
    Base.metadata.create_all(bind=engine)
    logger.info("Worker started")
    while True:
        try:
            recover_stale_jobs()
            claimed = claim_job()
            if claimed is None:
                time.sleep(POLL_SECONDS)
                continue
            job_id, payload, attempt = claimed
            logger.info("Running job %s (attempt %s)", job_id, attempt)
            try:
                result = execute(payload, attempt)
            except Exception as exc:
                finish_job(job_id, attempt, error=exc)
                logger.warning("Job %s failed: %s", job_id, exc)
            else:
                finish_job(job_id, attempt, result=result)
                logger.info("Job %s succeeded", job_id)
        except Exception:
            logger.exception("Worker loop failed")
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
