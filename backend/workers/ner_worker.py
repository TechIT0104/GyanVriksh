"""Kafka consumer: ocr-complete -> chunk + NER -> entities-raw + entities-tagged."""
import logging

from app.config import settings
from app.models.db_models import Chunk, Document, SessionLocal
from app.services import kafka_service, ner_service
from app.utils.chunker import chunk_pages
from workers.common import update_status

logger = logging.getLogger(__name__)


def handle(msg: dict):
    file_id = msg["file_id"]
    update_status(file_id, "NER", "Chunking and extracting entities...")
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.file_id == file_id).first()
        chunks = chunk_pages(msg["pages"])

        all_entities = []
        tagged_chunks = []
        for i, ch in enumerate(chunks):
            entities = ner_service.extract_entities(ch["text"])
            equipment_tags = sorted({e["text"].upper() for e in entities if e["label"] == "EQUIPMENT_TAG"})
            chunk_id = f"{file_id}-c{ch['chunk_index']}"
            db.add(Chunk(chunk_id=chunk_id, document_id=doc.id, page_number=ch["page"],
                         chunk_index=ch["chunk_index"], text=ch["text"],
                         meta={"entities": entities, "equipment_tags": equipment_tags}))
            all_entities.extend(entities)
            tagged_chunks.append({**ch, "chunk_id": chunk_id, "entities": entities,
                                  "equipment_tags": equipment_tags})
            if i % 5 == 0:
                update_status(file_id, "NER", f"NER running ({int(100 * (i + 1) / max(len(chunks), 1))}%)")

        doc.chunk_count = len(chunks)
        doc.entity_count = len(all_entities)
        db.commit()

        update_status(file_id, "NER_DONE", f"{len(chunks)} chunks, {len(all_entities)} entities")
        kafka_service.publish(settings.kafka_topic_entities_raw,
                              {"file_id": file_id, "doc_type": msg.get("doc_type", "UNKNOWN"),
                               "chunks": tagged_chunks})
        kafka_service.publish(settings.kafka_topic_entities_tagged,
                              {"file_id": file_id, "doc_type": msg.get("doc_type", "UNKNOWN"),
                               "chunks": tagged_chunks})
    except Exception as e:
        logger.exception("NER failed for %s", file_id)
        update_status(file_id, "ERROR", detail=str(e)[:500], error=str(e)[:2000])
    finally:
        db.close()


def main():
    consumer = kafka_service.make_consumer([settings.kafka_topic_ocr_complete], "ner-worker")
    logger.info("NER worker listening on %s", settings.kafka_topic_ocr_complete)
    kafka_service.consume_loop(consumer, handle)
