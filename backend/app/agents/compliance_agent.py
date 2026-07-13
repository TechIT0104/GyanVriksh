"""Compliance Intelligence Agent — gap detection per README 4.5."""
import json
import logging
import uuid
from datetime import datetime, timezone

from app.models.db_models import Chunk, ComplianceCheck, Document, SessionLocal
from app.services import neo4j_service
from app.services.llm_service import chat_json

logger = logging.getLogger(__name__)

REGULATION_HINTS = {
    "rotating equipment": "OISD-116", "pump": "OISD-116", "compressor": "OISD-116",
    "confined space": "OISD-118", "layout": "OISD-118",
    "hot work": "OISD-105", "lpg": "OISD-105",
    "pressure vessel": "OISD-137",
    "fire": "OISD-141", "explosion": "OISD-141",
    "safe job": "OISD-145", "permit to work": "OISD-145", "ptw": "OISD-145",
    "safety system": "OISD-117",
    "factory": "FACTORIES-ACT-1948", "worker": "FACTORIES-ACT-1948",
    "petroleum storage": "PESO-1934",
}

GAP_CHECK_PROMPT = """You are a regulatory compliance auditor for Indian process industry.
Compare each regulation requirement against the procedure text.

For EACH requirement clause, classify:
- COMPLIANT: procedure fully addresses the requirement
- PARTIAL: procedure addresses it but misses specifics (authority, frequency, thresholds)
- NON_COMPLIANT: procedure does not address the requirement

Return JSON:
{"results": [{
  "regulation_ref": "OISD-116 §5.3.2",
  "regulation_clause": "quoted requirement",
  "status": "COMPLIANT|PARTIAL|NON_COMPLIANT",
  "severity": "CRITICAL|MODERATE|MINOR",
  "procedure_text": "what the procedure says (or 'Not addressed')",
  "risk": "one-line audit risk",
  "recommended_action": "specific fix"
}]}"""


def suggest_regulations(procedure_text: str) -> list[str]:
    """Graph links first, then keyword inference."""
    text = procedure_text.lower()
    suggested = {reg for kw, reg in REGULATION_HINTS.items() if kw in text}
    return sorted(suggested) or ["OISD-116"]


def get_procedure_text(procedure_id: str, db) -> str:
    doc = db.query(Document).filter(Document.file_id == procedure_id).first()
    if doc:
        chunks = (db.query(Chunk).filter(Chunk.document_id == doc.id)
                  .order_by(Chunk.chunk_index).all())
        return "\n".join(c.text for c in chunks)
    rows = neo4j_service.run(
        "MATCH (p:Procedure {proc_id: $pid}) RETURN p.full_text AS text, p.title AS title",
        pid=procedure_id)
    if rows and rows[0].get("text"):
        return rows[0]["text"]
    raise ValueError(f"Procedure {procedure_id} not found in index or graph")


def get_regulation_text(reg_id: str) -> str:
    rows = neo4j_service.run(
        "MATCH (r:Regulation) WHERE r.reg_id STARTS WITH $rid "
        "RETURN r.reg_id AS id, r.section AS section, r.title AS title, r.text AS text",
        rid=reg_id)
    parts = [f"[{r['id']}] {r.get('title', '')}: {r.get('text', '')}" for r in rows if r.get("text")]
    return "\n\n".join(parts)


def run_check(procedure_id: str, regulation_ids: list[str], user_email: str) -> dict:
    db = SessionLocal()
    try:
        proc_text = get_procedure_text(procedure_id, db)
        if not regulation_ids:
            regulation_ids = suggest_regulations(proc_text)

        all_results = []
        for reg_id in regulation_ids:
            reg_text = get_regulation_text(reg_id)
            if not reg_text:
                logger.warning("No regulation text for %s", reg_id)
                continue
            out = chat_json([
                {"role": "system", "content": GAP_CHECK_PROMPT},
                {"role": "user", "content":
                    f"REGULATION ({reg_id}):\n{reg_text[:8000]}\n\n"
                    f"PROCEDURE ({procedure_id}):\n{proc_text[:8000]}"},
            ])
            all_results.extend(out.get("results", []))

        summary = {
            "checked": len(all_results),
            "compliant": sum(1 for r in all_results if r["status"] == "COMPLIANT"),
            "partial": sum(1 for r in all_results if r["status"] == "PARTIAL"),
            "non_compliant": sum(1 for r in all_results if r["status"] == "NON_COMPLIANT"),
        }
        gaps = [r for r in all_results if r["status"] != "COMPLIANT"]
        gaps.sort(key=lambda g: {"CRITICAL": 0, "MODERATE": 1, "MINOR": 2}.get(g["severity"], 3))

        report_lines = [
            f"COMPLIANCE REPORT — {procedure_id} vs {', '.join(regulation_ids)}",
            f"Generated: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC | By: GyanVriksh Compliance Agent",
            "",
            f"SUMMARY: {summary['checked']} requirements checked | "
            f"{summary['compliant']} COMPLIANT | {summary['partial']} PARTIAL | "
            f"{summary['non_compliant']} NON-COMPLIANT", "",
        ]
        for i, g in enumerate(gaps, 1):
            label = "NON-COMPLIANT" if g["status"] == "NON_COMPLIANT" else "PARTIAL COMPLIANCE"
            report_lines += [
                f"GAP #{i} [{g['severity']} — {label}]",
                f"Regulation: {g['regulation_ref']}",
                f"Requirement: {g['regulation_clause']}",
                f"Procedure: {g['procedure_text']}",
                f"Risk: {g['risk']}",
                f"Recommended Action: {g['recommended_action']}", "",
            ]
        report_text = "\n".join(report_lines)

        check_id = f"CHK-{uuid.uuid4().hex[:10].upper()}"
        db.add(ComplianceCheck(
            check_id=check_id, procedure_id=procedure_id, regulations=regulation_ids,
            user_email=user_email, summary=summary, gaps=gaps, report_text=report_text))
        db.commit()

        return {"check_id": check_id, "procedure_id": procedure_id,
                "regulations_checked": regulation_ids, "summary": summary,
                "gaps": gaps, "report_text": report_text}
    finally:
        db.close()


def dashboard() -> dict:
    """Plant-wide view: latest check per procedure + trend."""
    db = SessionLocal()
    try:
        checks = db.query(ComplianceCheck).order_by(ComplianceCheck.created_at.desc()).all()
        latest: dict[str, ComplianceCheck] = {}
        for c in checks:
            latest.setdefault(c.procedure_id, c)
        cells = [
            {"procedure_id": pid, "check_id": c.check_id, "regulations": c.regulations,
             "summary": c.summary, "checked_at": c.created_at.isoformat()}
            for pid, c in latest.items()
        ]
        trend = [
            {"date": c.created_at.date().isoformat(),
             "score": round(100 * c.summary["compliant"] / max(c.summary["checked"], 1))}
            for c in reversed(checks)
        ]
        return {"procedures": cells, "trend": trend, "total_checks": len(checks)}
    finally:
        db.close()
