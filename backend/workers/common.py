"""Shared helpers for Kafka workers: status updates + Redis pub for WebSocket relay."""
import json
import logging
import tempfile

import redis

from app.config import settings
from app.models.db_models import Document, SessionLocal

logger = logging.getLogger(__name__)
_redis = redis.from_url(settings.redis_url)


def update_status(file_id: str, status: str, detail: str = "", **fields):
    """Write status to Postgres and publish to Redis channel doc-status:<file_id>
    (the API layer relays this to WebSocket clients)."""
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.file_id == file_id).first()
        if doc:
            doc.status = status
            doc.status_detail = detail
            for k, v in fields.items():
                setattr(doc, k, v)
            db.commit()
    finally:
        db.close()
    _redis.publish(f"doc-status:{file_id}", json.dumps(
        {"file_id": file_id, "status": status, "detail": detail}))


def download_document(storage_path: str, original_name: str) -> str:
    """storage_path format: s3://bucket/object. Returns local temp file path."""
    from app.services import minio_service
    _, _, bucket, *obj = storage_path.split("/")
    object_name = "/".join(obj)
    suffix = "." + original_name.rsplit(".", 1)[-1] if "." in original_name else ""
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.close()
    minio_service.download_to_file(bucket, object_name, tmp.name)
    return tmp.name
