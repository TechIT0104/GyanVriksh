"""Maintenance Intelligence & RCA Agent per README 4.6."""
import logging
from datetime import date, datetime

from app.models.db_models import MaintenanceAlert, SessionLocal
from app.services import neo4j_service
from app.services.llm_service import chat

logger = logging.getLogger(__name__)

RCA_PROMPT = """You are a senior reliability engineer. Based on the equipment's work order
findings and incident history below, write a Maintenance Intelligence Report with sections:

FAILURE PATTERN DETECTED: (frequency, average interval vs maintenance interval, recommendation)
ROOT CAUSE ANALYSIS: (common failure threads across records, probable root cause, corrective action)
SIMILAR FAILURES IN PLANT: (from the similar-equipment data, insight)
NEXT MAINTENANCE DUE: (compute from last_maintained + interval; say if overdue)
CRITICALITY: (equipment criticality + scheduling recommendation)

Be specific and quantitative. Cite work order and incident IDs inline like [WO-2024-0831]."""


def _parse_date(value) -> date | None:
    if value is None:
        return None
    if hasattr(value, "to_native"):
        value = value.to_native()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def compute_mtbf(workorders: list[dict]) -> float | None:
    """Mean days between corrective work orders."""
    dates = sorted(d for d in (_parse_date(w.get("date")) for w in workorders
                               if w.get("type") == "CORRECTIVE") if d)
    if len(dates) < 2:
        return None
    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    return round(sum(gaps) / len(gaps), 1)


def health_score(equipment: dict, workorders: list[dict], incidents: list[dict]) -> int:
    """0-100 per README weights: overdue 40%, failure trend 30%, severity 20%, criticality 10%."""
    today = date.today()
    interval = int(equipment.get("maintenance_interval_days") or 180)

    last = _parse_date(equipment.get("last_maintained"))
    if last:
        overdue_ratio = max(0.0, ((today - last).days - interval) / interval)
        overdue_component = max(0.0, 1 - overdue_ratio)
    else:
        overdue_component = 0.5

    corrective_12mo = sum(
        1 for w in workorders
        if w.get("type") == "CORRECTIVE" and (_parse_date(w.get("date")) or date.min) > date(today.year - 1, today.month, 1))
    trend_component = max(0.0, 1 - corrective_12mo / 4)

    severe = sum(1 for i in incidents if str(i.get("severity", "")).upper() in ("HIGH", "CRITICAL"))
    severity_component = max(0.0, 1 - severe / 2)

    crit_component = {"LOW": 1.0, "MEDIUM": 0.7, "HIGH": 0.4}.get(
        str(equipment.get("criticality", "MEDIUM")).upper(), 0.7)

    score = 100 * (0.4 * overdue_component + 0.3 * trend_component
                   + 0.2 * severity_component + 0.1 * crit_component)
    return int(round(score))


def similar_failures(tag_id: str) -> list[dict]:
    return neo4j_service.run(
        """
        MATCH (e:Equipment {tag_id: $tag})-[:INVOLVED_IN]->(inc:Incident)
        WITH e, collect(DISTINCT inc.root_cause) AS causes
        MATCH (other:Equipment)-[:INVOLVED_IN]->(oi:Incident)
        WHERE other.tag_id <> $tag
          AND any(c IN causes WHERE c IS NOT NULL AND oi.root_cause CONTAINS split(c, ' ')[0])
        RETURN other.tag_id AS tag_id, other.name AS name, other.type AS type,
               collect({id: oi.incident_id, date: toString(oi.date), cause: oi.root_cause}) AS incidents
        """,
        tag=tag_id)


def equipment_view(tag_id: str) -> dict:
    view = neo4j_service.equipment_360(tag_id)
    if not view:
        return {}
    eq, wos, incs = view["equipment"], view["workorders"], view["incidents"]
    score = health_score(eq, wos, incs)
    mtbf = compute_mtbf(wos)
    neo4j_service.run("MATCH (e:Equipment {tag_id: $tag}) SET e.health_score = $s, e.mtbf_days = $m",
                      tag=tag_id, s=score, m=mtbf)
    view["health_score"] = score
    view["mtbf_days"] = mtbf
    view["similar_failures"] = similar_failures(tag_id)

    if score < 40:
        db = SessionLocal()
        try:
            exists = db.query(MaintenanceAlert).filter(
                MaintenanceAlert.equipment_tag == tag_id,
                MaintenanceAlert.acknowledged == False).first()  # noqa: E712
            if not exists:
                db.add(MaintenanceAlert(
                    equipment_tag=tag_id, alert_type="HEALTH_SCORE", severity="HIGH",
                    message=f"{tag_id} health score dropped to {score} — schedule maintenance"))
                db.commit()
        finally:
            db.close()
    return view


def generate_rca(tag_id: str) -> str:
    view = equipment_view(tag_id)
    if not view:
        return f"No data found for equipment {tag_id}."
    context = {
        "equipment": view["equipment"],
        "mtbf_days": view["mtbf_days"],
        "health_score": view["health_score"],
        "workorders": view["workorders"],
        "incidents": view["incidents"],
        "similar_equipment": view["similar_failures"],
    }
    import json
    return chat([
        {"role": "system", "content": RCA_PROMPT},
        {"role": "user", "content": f"Equipment data:\n{json.dumps(context, default=str)[:12000]}"},
    ])


def health_queue() -> list[dict]:
    tags = [r["tag"] for r in neo4j_service.run("MATCH (e:Equipment) RETURN e.tag_id AS tag")]
    queue = []
    for tag in tags:
        view = neo4j_service.equipment_360(tag)
        if not view:
            continue
        eq = view["equipment"]
        score = health_score(eq, view["workorders"], view["incidents"])
        last = _parse_date(eq.get("last_maintained"))
        interval = int(eq.get("maintenance_interval_days") or 180)
        overdue_days = 0
        if last:
            overdue_days = max(0, (date.today() - last).days - interval)
        queue.append({"tag_id": tag, "name": eq.get("name"), "type": eq.get("type"),
                      "unit": eq.get("unit"), "criticality": eq.get("criticality"),
                      "health_score": score, "overdue_days": overdue_days,
                      "last_maintained": str(eq.get("last_maintained", ""))})
    return sorted(queue, key=lambda x: x["health_score"])
