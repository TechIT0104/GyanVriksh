"""Celery app for long-running background jobs (Whisper transcription, re-indexing)."""
from celery import Celery

from app.config import settings

celery_app = Celery("gyanvriksh", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_track_started = True


@celery_app.task(name="transcribe_session")
def transcribe_session_task(session_id: str):
    from app.agents.preservation_agent import process_session
    process_session(session_id)
    return {"session_id": session_id, "status": "done"}


@celery_app.task(name="reindex_all")
def reindex_all_task():
    from app.config import settings as s
    from app.models.db_models import Document, SessionLocal
    from app.services import kafka_service
    db = SessionLocal()
    try:
        docs = db.query(Document).all()
        for d in docs:
            d.status = "QUEUED"
            kafka_service.publish(s.kafka_topic_raw_docs,
                                  {"file_id": d.file_id, "storage_path": d.storage_path})
        db.commit()
        return {"requeued": len(docs)}
    finally:
        db.close()
