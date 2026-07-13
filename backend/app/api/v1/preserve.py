"""Knowledge Preservation endpoints per README section 9."""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.agents import preservation_agent
from app.auth.rbac import require
from app.config import settings
from app.models.db_models import PreservationSession, get_db
from app.models.pydantic_models import ApproveRequest, SessionStart
from app.services import minio_service, neo4j_service

router = APIRouter()


@router.post("/session/start")
def start_session(body: SessionStart, user: dict = Depends(require("preserve")),
                  db: Session = Depends(get_db)):
    session_id = f"PS-{uuid.uuid4().hex[:10].upper()}"
    db.add(PreservationSession(session_id=session_id, expert_name=body.expert_name,
                               equipment_focus=body.equipment_focus))
    db.commit()
    prompts = (preservation_agent.suggested_prompts(body.equipment_focus.upper())
               if body.equipment_focus else [])
    return {"session_id": session_id, "suggested_prompts": prompts}


@router.post("/session/{session_id}/upload")
async def upload_audio(session_id: str, file: UploadFile = File(...),
                       duration_seconds: float = 0,
                       user: dict = Depends(require("preserve")),
                       db: Session = Depends(get_db)):
    session = db.query(PreservationSession).filter(
        PreservationSession.session_id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    data = await file.read()
    ext = (file.filename or "rec.webm").rsplit(".", 1)[-1]
    path = minio_service.upload_bytes(
        settings.minio_bucket_audio, f"{session_id}/recording.{ext}", data,
        content_type=file.content_type or "audio/webm")
    session.audio_path = path
    session.duration_seconds = duration_seconds
    session.status = "QUEUED_TRANSCRIPTION"
    db.commit()

    from app.celery_app import transcribe_session_task
    transcribe_session_task.delay(session_id)
    return {"session_id": session_id, "status": "QUEUED_TRANSCRIPTION"}


@router.get("/session/{session_id}/status")
def session_status(session_id: str, user: dict = Depends(require("preserve")),
                   db: Session = Depends(get_db)):
    s = db.query(PreservationSession).filter(
        PreservationSession.session_id == session_id).first()
    if not s:
        raise HTTPException(404, "Session not found")
    return {"session_id": s.session_id, "status": s.status,
            "transcript": s.transcript, "insight_count": len(s.insights or [])}


@router.get("/session/{session_id}/verify")
def get_verification(session_id: str, user: dict = Depends(require("preserve")),
                     db: Session = Depends(get_db)):
    s = db.query(PreservationSession).filter(
        PreservationSession.session_id == session_id).first()
    if not s:
        raise HTTPException(404, "Session not found")
    return {"session_id": s.session_id, "expert": s.expert_name,
            "transcript": s.transcript, "segments": s.word_timestamps,
            "insights": s.insights or []}


@router.post("/session/{session_id}/approve")
def approve(session_id: str, body: ApproveRequest,
            user: dict = Depends(require("preserve"))):
    return preservation_agent.publish_approved(
        session_id, [d.model_dump() for d in body.decisions], body.verified_by)


@router.get("/capsules/")
def list_capsules(user: dict = Depends(require("preserve"))):
    return neo4j_service.run(
        """MATCH (kc:KnowledgeCapsule)
        OPTIONAL MATCH (kc)-[:ABOUT]->(e:Equipment)
        RETURN kc.capsule_id AS capsule_id, kc.expert AS expert,
               kc.recorded_date AS recorded_date, kc.category AS category,
               kc.insight_text AS insight_text, kc.verified_by AS verified_by,
               collect(e.tag_id) AS equipment
        ORDER BY kc.recorded_date DESC""")


@router.get("/capsules/{capsule_id}")
def get_capsule(capsule_id: str, user: dict = Depends(require("preserve")),
                db: Session = Depends(get_db)):
    rows = neo4j_service.run(
        "MATCH (kc:KnowledgeCapsule {capsule_id: $cid}) "
        "OPTIONAL MATCH (kc)-[:ABOUT]->(e:Equipment) "
        "RETURN kc, collect(e.tag_id) AS equipment", cid=capsule_id)
    if not rows:
        raise HTTPException(404, "Capsule not found")
    capsule = dict(rows[0]["kc"])
    capsule["equipment"] = rows[0]["equipment"]
    # Presigned audio URL if stored
    if capsule.get("audio_path", "").startswith("s3://"):
        _, _, bucket, *obj = capsule["audio_path"].split("/")
        capsule["audio_url"] = minio_service.presigned_url(bucket, "/".join(obj))
    # Session transcript if available
    session = db.query(PreservationSession).filter(
        PreservationSession.session_id == capsule.get("session_id", "")).first()
    if session:
        capsule["transcript"] = session.transcript
    return capsule
