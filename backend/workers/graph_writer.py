"""Kafka consumer: entities-raw -> entity resolution -> Neo4j upserts.
Also runs the LLM-assisted relationship inference pass per README 4.1 step 7."""
import logging

from app.config import settings
from app.services import kafka_service, neo4j_service
from app.services.llm_service import chat_json
from app.utils.entity_resolver import normalize_tag, resolve_equipment

logger = logging.getLogger(__name__)

REL_INFERENCE_PROMPT = """You are building an industrial knowledge graph.
Given a text chunk and the entities found in it, infer relationships.

Allowed relationships (source_label, REL, target_label):
- Equipment HAS_MAINTENANCE_RECORD WorkOrder
- Equipment FOLLOWS_PROCEDURE Procedure
- Equipment GOVERNED_BY Regulation
- Equipment INVOLVED_IN Incident
- Person PERFORMED WorkOrder
- Person KNOWS_ABOUT Equipment
- Document REFERENCES Equipment
- Document CITES Regulation
- Procedure REQUIRED_BY Regulation

Return JSON: {"relationships": [{"source": "...", "source_label": "...",
"rel": "...", "target": "...", "target_label": "..."}]}
Use entity texts exactly as given. Only include relationships supported by the text."""


def _upsert_entity_nodes(chunk: dict, file_id: str):
    """Create/link nodes for entities in a chunk. Returns tag list for the doc node."""
    referenced_tags = []
    for ent in chunk["entities"]:
        label, text = ent["label"], ent["text"]
        if label == "EQUIPMENT_TAG":
            existing = resolve_equipment(text)
            tag = existing or normalize_tag(text)
            if not existing:
                neo4j_service.upsert_node("Equipment", tag, {"tag_id": tag, "name": text, "source": "ner"})
            referenced_tags.append(tag)
        elif label == "PERSON":
            pid = "EMP-" + normalize_tag(text).replace("-", "")[:24]
            neo4j_service.upsert_node("Person", pid, {"person_id": pid, "name": text})
        elif label == "PROCEDURE_REF" and text.upper().startswith("SOP"):
            neo4j_service.upsert_node("Procedure", text.upper(), {"proc_id": text.upper(), "title": text})
        elif label == "REGULATORY_REF":
            reg_id = normalize_tag(text)[:40]
            neo4j_service.upsert_node("Regulation", reg_id, {"reg_id": reg_id, "title": text})
    return referenced_tags


def _infer_relationships(chunk: dict):
    if len(chunk["entities"]) < 2:
        return
    try:
        result = chat_json([
            {"role": "system", "content": REL_INFERENCE_PROMPT},
            {"role": "user", "content":
                f"Text: {chunk['text'][:1500]}\n\nEntities: "
                f"{[{'text': e['text'], 'label': e['label']} for e in chunk['entities']][:20]}"},
        ])
    except Exception:
        logger.exception("Relationship inference failed for chunk %s", chunk.get("chunk_id"))
        return
    for rel in result.get("relationships", []):
        try:
            src = normalize_tag(rel["source"]) if rel["source_label"] == "Equipment" else rel["source"]
            tgt = normalize_tag(rel["target"]) if rel["target_label"] == "Equipment" else rel["target"]
            if rel["source_label"] == "Person":
                src = "EMP-" + normalize_tag(rel["source"]).replace("-", "")[:24]
            if rel["target_label"] == "Person":
                tgt = "EMP-" + normalize_tag(rel["target"]).replace("-", "")[:24]
            neo4j_service.upsert_relationship(
                rel["source_label"], src, rel["rel"], rel["target_label"], tgt,
                {"inferred": True, "chunk_id": chunk.get("chunk_id", "")})
        except Exception:
            logger.warning("Skipped invalid inferred relationship: %s", rel)


def handle(msg: dict):
    file_id = msg["file_id"]
    doc_id = file_id
    neo4j_service.upsert_node("Document", doc_id, {
        "doc_id": doc_id, "type": msg.get("doc_type", "UNKNOWN"),
    })
    all_tags = set()
    for chunk in msg["chunks"]:
        tags = _upsert_entity_nodes(chunk, file_id)
        all_tags.update(tags)
        _infer_relationships(chunk)
    for tag in all_tags:
        neo4j_service.upsert_relationship("Document", doc_id, "REFERENCES", "Equipment", tag)
    logger.info("Graph updated for %s: %d equipment references", file_id, len(all_tags))


def main():
    consumer = kafka_service.make_consumer([settings.kafka_topic_entities_raw], "graph-writer")
    logger.info("Graph writer listening on %s", settings.kafka_topic_entities_raw)
    kafka_service.consume_loop(consumer, handle)
