"""Knowledge Preservation Agent — audio -> transcript -> insights -> verification -> graph.
Per README 4.7 (flagship innovation)."""
import logging
import uuid
from datetime import date

from app.models.db_models import PreservationSession, SessionLocal
from app.services import neo4j_service, whisper_service
from app.services.llm_service import chat_json
from app.utils.entity_resolver import normalize_tag, resolve_equipment

logger = logging.getLogger(__name__)

INSIGHT_PROMPT = """You are extracting preservable expert knowledge from a transcript of a
veteran industrial technician speaking (possibly Hinglish).

Extract each distinct actionable insight. Categories:
CALIBRATION_INSIGHT, FAILURE_PRECURSOR, OPERATING_TIP, WORKAROUND, SAFETY_WARNING, HISTORY

Return JSON:
{"insights": [{
  "quote": "verbatim or lightly cleaned quote from the transcript",
  "insight_text": "the insight restated clearly in one or two sentences (English)",
  "category": "...",
  "equipment_mentioned": ["FI-101"],
  "timestamp_sec": 0,
  "confidence": "HIGH|MEDIUM|LOW"
}]}
Use the segment timestamps provided to set timestamp_sec (start of the relevant segment)."""


def process_session(session_id: str):
    """Celery task body: transcribe, extract insights, set status VERIFYING."""
    db = SessionLocal()
    try:
        session = db.query(PreservationSession).filter(
            PreservationSession.session_id == session_id).first()
        if not session or not session.audio_path:
            logger.error("Session %s missing or has no audio", session_id)
            return
        session.status = "TRANSCRIBING"
        db.commit()

        from workers.common import download_document
        local_path = download_document(session.audio_path, "audio.wav")
        result = whisper_service.transcribe(local_path, session.equipment_focus)

        session.transcript = result["text"]
        session.word_timestamps = result["segments"]
        db.commit()

        segments_for_llm = [
            {"start_sec": round(s["start"]), "text": s["text"]}
            for s in result["segments"]
        ]
        out = chat_json([
            {"role": "system", "content": INSIGHT_PROMPT},
            {"role": "user", "content": f"Transcript segments:\n{segments_for_llm}"},
        ])
        insights = out.get("insights", [])
        for ins in insights:
            linked = []
            for eq_text in ins.get("equipment_mentioned", []):
                tag = resolve_equipment(eq_text) or normalize_tag(eq_text)
                linked.append(tag)
            ins["linked_equipment"] = linked
            ins["status"] = "PENDING"
        session.insights = insights
        session.status = "VERIFYING"
        db.commit()
        logger.info("Session %s: %d insights ready for verification", session_id, len(insights))
    except Exception:
        logger.exception("Preservation processing failed for %s", session_id)
        db.rollback()
        session = db.query(PreservationSession).filter(
            PreservationSession.session_id == session_id).first()
        if session:
            session.status = "ERROR"
            db.commit()
    finally:
        db.close()


def publish_approved(session_id: str, decisions: list[dict], verified_by: str) -> dict:
    """Create KnowledgeCapsule nodes for approved insights."""
    db = SessionLocal()
    try:
        session = db.query(PreservationSession).filter(
            PreservationSession.session_id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        insights = list(session.insights or [])
        published = []
        for d in decisions:
            idx = d["insight_index"]
            if idx >= len(insights):
                continue
            ins = insights[idx]
            if d["action"] == "reject":
                ins["status"] = "REJECTED"
                continue
            if d["action"] == "edit" and d.get("edited_text"):
                ins["insight_text"] = d["edited_text"]
            if d.get("category"):
                ins["category"] = d["category"]
            if d.get("linked_equipment"):
                ins["linked_equipment"] = [normalize_tag(d["linked_equipment"])]
            ins["status"] = "APPROVED"
            ins["notes"] = d.get("notes", "")

            capsule_id = f"KC-{date.today().year}-{uuid.uuid4().hex[:6].upper()}"
            neo4j_service.upsert_node("KnowledgeCapsule", capsule_id, {
                "capsule_id": capsule_id,
                "expert": session.expert_name,
                "recorded_date": str(date.today()),
                "duration_seconds": session.duration_seconds,
                "audio_path": session.audio_path,
                "insight_text": ins["insight_text"],
                "quote": ins.get("quote", ""),
                "category": ins.get("category", "OPERATING_TIP"),
                "timestamp_sec": ins.get("timestamp_sec", 0),
                "confidence": "EXPERT_VERIFIED",
                "verified": True,
                "verified_by": verified_by,
                "notes": ins.get("notes", ""),
                "session_id": session_id,
            })
            person_id = "EMP-" + normalize_tag(session.expert_name).replace("-", "")[:24]
            neo4j_service.upsert_node("Person", person_id,
                                      {"person_id": person_id, "name": session.expert_name})
            neo4j_service.upsert_relationship(
                "Person", person_id, "SHARED_KNOWLEDGE", "KnowledgeCapsule", capsule_id)
            for tag in ins.get("linked_equipment", []):
                neo4j_service.upsert_node("Equipment", tag, {"tag_id": tag})
                neo4j_service.upsert_relationship(
                    "KnowledgeCapsule", capsule_id, "ABOUT", "Equipment", tag)
                neo4j_service.upsert_relationship(
                    "Person", person_id, "KNOWS_ABOUT", "Equipment", tag)
            ins["capsule_id"] = capsule_id
            published.append(capsule_id)

        session.insights = insights
        if published:
            session.status = "PUBLISHED"
        db.commit()
        return {"published_capsules": published, "session_status": session.status}
    finally:
        db.close()


def suggested_prompts(equipment_tag: str) -> list[str]:
    """Interview prompts generated from equipment history per README page 8."""
    view = neo4j_service.equipment_360(equipment_tag)
    if not view:
        return [f"Ask about: General experience with {equipment_tag}"]
    prompts = []
    for inc in view["incidents"][:3]:
        prompts.append(f"Ask about: {inc.get('type', 'incident')} on {inc.get('date')} "
                       f"({inc.get('description', '')[:60]})")
    for wo in view["workorders"][:3]:
        prompts.append(f"Ask about: {wo.get('description', 'work order')} ({wo.get('date')})")
    prompts.append(f"Ask about: Early warning signs before {equipment_tag} fails")
    prompts.append(f"Ask about: Unofficial workarounds or calibration quirks for {equipment_tag}")
    return prompts
