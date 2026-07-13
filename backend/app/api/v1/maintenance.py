"""Maintenance intelligence endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents import lessons_agent, maintenance_agent
from app.auth.rbac import require
from app.models.db_models import MaintenanceAlert, get_db

router = APIRouter()


@router.get("/health-queue")
def health_queue(user: dict = Depends(require("maintenance"))):
    return maintenance_agent.health_queue()


@router.get("/alerts")
def alerts(user: dict = Depends(require("maintenance")), db: Session = Depends(get_db)):
    rows = (db.query(MaintenanceAlert).filter(MaintenanceAlert.acknowledged == False)  # noqa: E712
            .order_by(MaintenanceAlert.created_at.desc()).limit(100).all())
    return [{"id": a.id, "equipment_tag": a.equipment_tag, "alert_type": a.alert_type,
             "message": a.message, "severity": a.severity,
             "created_at": a.created_at.isoformat()} for a in rows]


@router.post("/alerts/{alert_id}/ack")
def ack_alert(alert_id: int, user: dict = Depends(require("maintenance")),
              db: Session = Depends(get_db)):
    a = db.query(MaintenanceAlert).get(alert_id)
    if a:
        a.acknowledged = True
        db.commit()
    return {"ok": True}


@router.get("/{tag_id}/360")
def full_view(tag_id: str, user: dict = Depends(require("maintenance"))):
    view = maintenance_agent.equipment_view(tag_id.upper())
    if not view:
        raise HTTPException(404, f"Equipment {tag_id} not found")
    return view


@router.get("/{tag_id}/timeline")
def timeline(tag_id: str, user: dict = Depends(require("maintenance"))):
    view = maintenance_agent.equipment_view(tag_id.upper())
    if not view:
        raise HTTPException(404, f"Equipment {tag_id} not found")
    events = (
        [{"date": str(w.get("date", "")), "kind": "workorder",
          "type": w.get("type", ""), "id": w.get("wo_id"),
          "description": w.get("description", "")} for w in view["workorders"]]
        + [{"date": str(i.get("date", "")), "kind": "incident",
            "type": i.get("severity", ""), "id": i.get("incident_id"),
            "description": i.get("description", "")} for i in view["incidents"]]
    )
    return sorted(events, key=lambda e: e["date"], reverse=True)


@router.get("/{tag_id}/rca")
def rca(tag_id: str, user: dict = Depends(require("maintenance"))):
    return {"tag_id": tag_id.upper(), "report": maintenance_agent.generate_rca(tag_id.upper())}


@router.post("/{tag_id}/check-work")
def check_work(tag_id: str, description: str = "", user: dict = Depends(require("maintenance"))):
    """Lessons Learned proactive check when drafting a new work order."""
    return {"warnings": lessons_agent.check_new_work(tag_id.upper(), description)}
