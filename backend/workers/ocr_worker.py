"""Kafka consumer: raw-documents -> OCR/extraction -> ocr-complete."""
import logging
import os

from app.config import settings
from app.models.db_models import Document, ExtractedTable, SessionLocal
from app.services import kafka_service, ocr_service
from workers.common import download_document, update_status

logger = logging.getLogger(__name__)


def handle(msg: dict):
    file_id = msg["file_id"]
    update_status(file_id, "OCR", "Extracting text...")
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.file_id == file_id).first()
        if not doc:
            logger.error("Unknown file_id %s", file_id)
            return
        local_path = download_document(doc.storage_path, doc.original_name)
        try:
            result = ocr_service.extract_any(local_path, doc.original_name)
        finally:
            os.unlink(local_path)

        for t in result["tables"]:
            db.add(ExtractedTable(document_id=doc.id, page_number=t["page"], table_json=t["table"]))
        doc.page_count = len(result["pages"])
        db.commit()

        # Append table sentences to page text so tabular facts are embeddable
        table_text = " ".join(ocr_service.table_to_sentences(t["table"]) for t in result["tables"])
        pages = result["pages"]
        if table_text.strip() and pages:
            pages[-1]["text"] += "\n\n" + table_text

        update_status(file_id, "OCR_DONE", f"{len(pages)} pages via {result['method']}")
        kafka_service.publish(settings.kafka_topic_ocr_complete,
                              {"file_id": file_id, "pages": pages, "doc_type": doc.doc_type})
    except Exception as e:
        logger.exception("OCR failed for %s", file_id)
        update_status(file_id, "ERROR", detail=str(e)[:500], error=str(e)[:2000])
    finally:
        db.close()


def main():
    consumer = kafka_service.make_consumer([settings.kafka_topic_raw_docs], "ocr-worker")
    logger.info("OCR worker listening on %s", settings.kafka_topic_raw_docs)
    kafka_service.consume_loop(consumer, handle)
