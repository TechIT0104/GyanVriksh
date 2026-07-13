"""Compliance endpoints per README section 9."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents import compliance_agent
from app.auth.rbac import require
from app.models.db_models import AuditLog, ComplianceCheck, get_db
from app.models.pydantic_models import ComplianceCheckRequest
from app.services import neo4j_service

router = APIRouter()


@router.post("/check")
def run_check(body: ComplianceCheckRequest, user: dict = Depends(require("compliance")),
              db: Session = Depends(get_db)):
    result = compliance_agent.run_check(body.procedure_id, body.regulation_ids, user["email"])
    db.add(AuditLog(user_email=user["email"], action="compliance_check",
                    detail={"check_id": result["check_id"], "procedure": body.procedure_id,
                            "regulations": result["regulations_checked"]}))
    db.commit()
    return result


@router.get("/report/{check_id}")
def get_report(check_id: str, user: dict = Depends(require("compliance")),
               db: Session = Depends(get_db)):
    check = db.query(ComplianceCheck).filter(ComplianceCheck.check_id == check_id).first()
    if not check:
        raise HTTPException(404, "Check not found")
    return {"check_id": check.check_id, "procedure_id": check.procedure_id,
            "regulations": check.regulations, "summary": check.summary,
            "gaps": check.gaps, "report_text": check.report_text,
            "created_at": check.created_at.isoformat(), "by": check.user_email}


@router.get("/dashboard")
def dashboard(user: dict = Depends(require("compliance"))):
    return compliance_agent.dashboard()


@router.get("/regulations")
def regulations(user: dict = Depends(require("compliance"))):
    rows = neo4j_service.run(
        "MATCH (r:Regulation) RETURN r.reg_id AS reg_id, r.standard AS standard, "
        "r.section AS section, r.title AS title ORDER BY r.reg_id")
    return rows
