"""Admin endpoints: system monitoring, users, ingestion config, lessons patterns."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents import lessons_agent
from app.auth.jwt import hash_password
from app.auth.rbac import ROLES, require
from app.models.db_models import AuditLog, Document, QueryLog, User, get_db
from app.services import neo4j_service, qdrant_service

router = APIRouter()


@router.get("/stats")
def system_stats(user: dict = Depends(require("admin")), db: Session = Depends(get_db)):
    docs = db.query(Document).count()
    indexed = db.query(Document).filter(Document.status == "INDEXED").count()
    queries = db.query(QueryLog).count()
    return {
        "documents": {"total": docs, "indexed": indexed},
        "queries_served": queries,
        "qdrant": qdrant_service.collection_stats(),
        "neo4j": neo4j_service.stats(),
    }


@router.get("/users")
def list_users(user: dict = Depends(require("admin")), db: Session = Depends(get_db)):
    return [{"id": u.id, "email": u.email, "name": u.name, "role": u.role,
             "is_active": u.is_active} for u in db.query(User).all()]


@router.post("/users")
def create_user(email: str, password: str, name: str, role: str,
                user: dict = Depends(require("admin")), db: Session = Depends(get_db)):
    if role not in ROLES:
        raise HTTPException(400, f"Role must be one of {ROLES}")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email already exists")
    db.add(User(email=email, password_hash=hash_password(password), name=name, role=role))
    db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/deactivate")
def deactivate(user_id: int, user: dict = Depends(require("admin")),
               db: Session = Depends(get_db)):
    u = db.query(User).get(user_id)
    if u:
        u.is_active = False
        db.commit()
    return {"ok": True}


@router.get("/audit-log")
def audit_log(user: dict = Depends(require("admin")), db: Session = Depends(get_db)):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
    return [{"user": a.user_email, "action": a.action, "detail": a.detail,
             "at": a.created_at.isoformat()} for a in rows]


@router.post("/reindex")
def reindex(user: dict = Depends(require("admin"))):
    from app.celery_app import reindex_all_task
    task = reindex_all_task.delay()
    return {"task_id": task.id}


# Lessons Learned endpoints (admin-adjacent config per README page 9)
@router.get("/lessons/patterns")
def lessons_patterns(user: dict = Depends(require("maintenance"))):
    return lessons_agent.detect_patterns()


@router.get("/lessons/knowledge-cliff")
def knowledge_cliff(user: dict = Depends(require("maintenance"))):
    return lessons_agent.knowledge_cliff_report()
