"""Document endpoints + processing-status WebSocket (relays Redis pubsub)."""
import asyncio
import json
import uuid

import redis.asyncio as aioredis
from fastapi import (APIRouter, Depends, File, HTTPException, UploadFile,
                     WebSocket, WebSocketDisconnect)
from sqlalchemy.orm import Session

from app.auth.rbac import require
from app.config import settings
from app.models.db_models import Chunk, Document, get_db
from app.services import kafka_service, minio_service

router = APIRouter()
ws_router = APIRouter()

DOC_TYPES = ["SOP", "MAINTENANCE_REPORT", "REGULATION", "INCIDENT_REPORT",
             "INSPECTION_RECORD", "AUDIT_REPORT", "UNKNOWN"]


@router.post("/upload")
async def upload(file: UploadFile = File(...), doc_type: str = "UNKNOWN",
                 user: dict = Depends(require("documents")),
                 db: Session = Depends(get_db)):
    data = await file.read()
    if len(data) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.max_upload_size_mb}MB limit")
    if doc_type not in DOC_TYPES:
        doc_type = "UNKNOWN"

    file_id = f"DOC-{uuid.uuid4().hex[:10].upper()}"
    object_name = f"{file_id}/{file.filename}"
    storage_path = minio_service.upload_bytes(
        settings.minio_bucket_docs, object_name, data,
        content_type=file.content_type or "application/octet-stream")

    doc = Document(file_id=file_id, original_name=file.filename, doc_type=doc_type,
                   storage_path=storage_path, uploader=user["email"], status="QUEUED")
    db.add(doc)
    db.commit()

    kafka_service.publish(settings.kafka_topic_raw_docs,
                          {"file_id": file_id, "storage_path": storage_path})
    return {"file_id": file_id, "status": "QUEUED"}


@router.get("/")
def list_documents(status: str | None = None, doc_type: str | None = None,
                   user: dict = Depends(require("documents")),
                   db: Session = Depends(get_db)):
    q = db.query(Document).order_by(Document.upload_time.desc())
    if status:
        q = q.filter(Document.status == status)
    if doc_type:
        q = q.filter(Document.doc_type == doc_type)
    return [
        {"file_id": d.file_id, "original_name": d.original_name, "doc_type": d.doc_type,
         "status": d.status, "status_detail": d.status_detail,
         "upload_time": d.upload_time.isoformat() if d.upload_time else None,
         "page_count": d.page_count, "chunk_count": d.chunk_count,
         "entity_count": d.entity_count}
        for d in q.limit(500)
    ]


@router.get("/{file_id}")
def get_document(file_id: str, user: dict = Depends(require("documents")),
                 db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.file_id == file_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    chunks = db.query(Chunk).filter(Chunk.document_id == doc.id).order_by(Chunk.chunk_index).all()
    return {
        "file_id": doc.file_id, "original_name": doc.original_name,
        "doc_type": doc.doc_type, "status": doc.status, "error": doc.error,
        "page_count": doc.page_count,
        "download_url": _download_url(doc),
        "chunks": [{"chunk_id": c.chunk_id, "page": c.page_number,
                    "text": c.text, "entities": (c.meta or {}).get("entities", [])}
                   for c in chunks],
    }


def _download_url(doc: Document) -> str:
    _, _, bucket, *obj = doc.storage_path.split("/")
    return minio_service.presigned_url(bucket, "/".join(obj))


@router.get("/{file_id}/status")
def get_status(file_id: str, user: dict = Depends(require("documents")),
               db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.file_id == file_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return {"file_id": file_id, "status": doc.status, "detail": doc.status_detail}


@router.delete("/{file_id}")
def delete_document(file_id: str, user: dict = Depends(require("documents")),
                    db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.file_id == file_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    db.delete(doc)
    db.commit()
    return {"deleted": file_id}


@ws_router.websocket("/ws/documents/{file_id}/status")
async def ws_status(websocket: WebSocket, file_id: str):
    """Relay Redis doc-status channel to the client."""
    await websocket.accept()
    r = aioredis.from_url(settings.redis_url)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"doc-status:{file_id}")
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
            if msg:
                await websocket.send_text(msg["data"].decode())
            else:
                await websocket.send_text(json.dumps({"ping": True}))
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"doc-status:{file_id}")
        await r.aclose()
