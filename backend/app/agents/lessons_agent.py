"""Lessons Learned & Failure Intelligence Engine per README 4.8.
Clusters incident embeddings, LLM-labels each cluster, powers proactive alerts."""
import json
import logging

import numpy as np
from sklearn.cluster import DBSCAN

from app.models.db_models import MaintenanceAlert, SessionLocal
from app.services import embedding_service, neo4j_service
from app.services.llm_service import chat_json

logger = logging.getLogger(__name__)

CLUSTER_LABEL_PROMPT = """These industrial incidents were grouped by similarity.
Summarize the pattern. Return JSON:
{"pattern_name": "short name", "common_thread": "one sentence",
 "locations": ["Unit 3"], "time_pattern": "if any", "severity": "HIGH|MEDIUM|LOW",
 "preventive_recommendation": "one actionable sentence"}"""


def _load_incidents() -> list[dict]:
    return neo4j_service.run(
        """MATCH (i:Incident)
        OPTIONAL MATCH (e:Equipment)-[:INVOLVED_IN]->(i)
        RETURN i.incident_id AS id, toString(i.date) AS date, i.type AS type,
               i.severity AS severity, i.description AS description,
               i.root_cause AS root_cause, collect(e.tag_id) AS equipment""")


def detect_patterns() -> list[dict]:
    incidents = _load_incidents()
    if len(incidents) < 2:
        return []
    texts = [f"{i['description'] or ''} Root cause: {i['root_cause'] or ''}" for i in incidents]
    vecs = np.array([v["dense"] for v in embedding_service.embed(texts)])
    labels = DBSCAN(eps=0.35, min_samples=2, metric="cosine").fit_predict(vecs)

    patterns = []
    for cluster_id in sorted(set(labels)):
        if cluster_id == -1:
            continue
        members = [incidents[i] for i in range(len(incidents)) if labels[i] == cluster_id]
        try:
            meta = chat_json([
                {"role": "system", "content": CLUSTER_LABEL_PROMPT},
                {"role": "user", "content": json.dumps(members, default=str)[:8000]},
            ])
        except Exception:
            logger.exception("Cluster labeling failed")
            meta = {"pattern_name": f"Pattern {cluster_id + 1}",
                    "common_thread": "Similar incidents", "severity": "MEDIUM"}
        patterns.append({
            "pattern_id": int(cluster_id) + 1,
            "incident_count": len(members),
            "incidents": members,
            **meta,
        })
    patterns.sort(key=lambda p: -p["incident_count"])
    return patterns


def check_new_work(equipment_tag: str, work_description: str) -> list[dict]:
    """Proactive push: does this planned work match a historical incident pattern?"""
    rows = neo4j_service.run(
        """MATCH (e:Equipment {tag_id: $tag})-[:INVOLVED_IN]->(i:Incident)
        RETURN i.incident_id AS id, i.description AS description,
               i.root_cause AS root_cause, toString(i.date) AS date""",
        tag=equipment_tag)
    warnings = []
    if rows:
        warnings.append({
            "equipment_tag": equipment_tag,
            "message": f"Warning: {equipment_tag} has been involved in {len(rows)} historical "
                       f"incident(s). Review prior root causes before starting this work.",
            "incidents": rows,
        })
        db = SessionLocal()
        try:
            db.add(MaintenanceAlert(
                equipment_tag=equipment_tag, alert_type="PATTERN", severity="MEDIUM",
                message=f"New work on {equipment_tag} matches historical incident pattern "
                        f"({len(rows)} prior incidents)"))
            db.commit()
        finally:
            db.close()
    return warnings


def knowledge_cliff_report() -> list[dict]:
    """Experts retiring within 3 years and what knowledge is / isn't captured."""
    return neo4j_service.run(
        """MATCH (p:Person)
        WHERE p.retirement_date IS NOT NULL AND date(p.retirement_date) <= date() + duration({years: 3})
        OPTIONAL MATCH (p)-[:PERFORMED]->(:WorkOrder)<-[:HAS_MAINTENANCE_RECORD]-(e:Equipment)
        WITH p, collect(DISTINCT e.tag_id) AS expertise
        OPTIONAL MATCH (p)-[:SHARED_KNOWLEDGE]->(kc:KnowledgeCapsule)-[:ABOUT]->(covered:Equipment)
        WITH p, expertise, collect(DISTINCT covered.tag_id) AS captured
        RETURN p.name AS name, toString(p.retirement_date) AS retirement_date,
               p.years_experience AS years_experience, expertise,
               captured, [t IN expertise WHERE NOT t IN captured] AS uncaptured
        ORDER BY p.retirement_date""")
