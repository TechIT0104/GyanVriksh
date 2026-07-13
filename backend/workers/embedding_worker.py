"""Kafka consumer: entities-tagged -> BGE-M3 embeddings -> Qdrant. Final stage: INDEXED."""
import logging
import uuid

from app.config import settings
from app.services import embedding_service, kafka_service, qdrant_service
from workers.common import update_status

logger = logging.getLogger(__name__)

DOC_TYPE_COLLECTION = {
    "SOP": "procedures", "PROCEDURE": "procedures",
    "REGULATION": "regulations",
    "INCIDENT": "incidents", "INCIDENT_REPORT": "incidents",
}


def handle(msg: dict):
    file_id = msg["file_id"]
    update_status(file_id, "EMBEDDING", "Computing embeddings...")
    try:
        chunks = msg["chunks"]
        if not chunks:
            update_status(file_id, "INDEXED", "No text content")
            return
        vectors = embedding_service.embed([c["text"] for c in chunks])
        collection = DOC_TYPE_COLLECTION.get(msg.get("doc_type", ""), "chunks")
        points = []
        for ch, vec in zip(chunks, vectors):
            points.append({
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, ch["chunk_id"])),
                "dense": vec["dense"],
                "sparse": vec["sparse"],
                "payload": {
                    "chunk_id": ch["chunk_id"], "file_id": file_id,
                    "page": ch["page"], "text": ch["text"],
                    "doc_type": msg.get("doc_type", "UNKNOWN"),
                    "equipment_tags": ch.get("equipment_tags", []),
                },
            })
        qdrant_service.upsert_chunks(collection, points)
        # Always index in main chunks collection too for unified copilot search
        if collection != "chunks":
            qdrant_service.upsert_chunks("chunks", points)
        update_status(file_id, "INDEXED", f"{len(points)} vectors in '{collection}'")
    except Exception as e:
        logger.exception("Embedding failed for %s", file_id)
        update_status(file_id, "ERROR", detail=str(e)[:500], error=str(e)[:2000])


def main():
    consumer = kafka_service.make_consumer([settings.kafka_topic_entities_tagged], "embedding-worker")
    logger.info("Embedding worker listening on %s", settings.kafka_topic_entities_tagged)
    kafka_service.consume_loop(consumer, handle)
