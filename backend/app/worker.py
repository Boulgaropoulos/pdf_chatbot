import time
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import SessionLocal, init_db
from app.models import Document, ProcessingJob, ProcessingStatus
from app.services.document_processor import process_document


POLL_SECONDS = 2


def utc_now() -> datetime:
    return datetime.now(UTC)


def claim_next_job(db: Session) -> ProcessingJob | None:
    job = db.scalars(
        select(ProcessingJob)
        .where(ProcessingJob.status == ProcessingStatus.queued)
        .order_by(ProcessingJob.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    ).first()

    if job is None:
        return None

    job.status = ProcessingStatus.processing
    job.started_at = utc_now()
    job.document.status = ProcessingStatus.processing
    db.commit()
    db.refresh(job)
    return job


def run_once() -> bool:
    with SessionLocal() as db:
        job = claim_next_job(db)
        if job is None:
            return False

        document = db.scalars(
            select(Document).where(Document.id == job.document_id).options(selectinload(Document.chunks))
        ).one()

        try:
            chunk_count = process_document(db, document)
            document.status = ProcessingStatus.ready
            job.status = ProcessingStatus.ready
            job.finished_at = utc_now()
            db.commit()
            print(f"Processed {document.filename}: {chunk_count} chunks", flush=True)
        except Exception as exc:
            db.rollback()
            failed_job = db.get(ProcessingJob, job.id)
            failed_document = db.get(Document, job.document_id)
            if failed_job is not None:
                failed_job.status = ProcessingStatus.failed
                failed_job.error_message = str(exc)
                failed_job.finished_at = utc_now()
            if failed_document is not None:
                failed_document.status = ProcessingStatus.failed
            db.commit()
            print(f"Failed to process document {job.document_id}: {exc}", flush=True)

        return True


def main() -> None:
    init_db()
    print("Worker running. Waiting for queued PDF processing jobs.", flush=True)
    while True:
        did_work = run_once()
        if not did_work:
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
