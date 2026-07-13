"""Fuzzy entity resolution against existing Neo4j Equipment nodes."""
import re

from rapidfuzz import fuzz

from app.services import neo4j_service

ABBREVIATIONS = {
    "p.": "P-", "pump unit ": "P-", "heat exchanger ": "HE-",
    "vessel ": "V-", "column ": "C-", "compressor ": "K-",
}


def normalize_tag(text: str) -> str:
    """'P.101' -> 'P-101', 'Pump Unit 101' -> 'P-101' etc."""
    t = text.strip()
    lower = t.lower()
    for abbr, canonical in ABBREVIATIONS.items():
        if lower.startswith(abbr):
            rest = re.sub(r"[^0-9A-Za-z]", "", t[len(abbr):])
            return f"{canonical}{rest}".upper()
    return re.sub(r"[.\s_]+", "-", t).upper()


def resolve_equipment(entity_text: str, threshold: int = 85) -> str | None:
    """Returns the canonical tag_id of an existing Equipment node, or None."""
    candidate = normalize_tag(entity_text)
    rows = neo4j_service.run("MATCH (e:Equipment) RETURN e.tag_id AS tag, e.name AS name")
    best_tag, best_score = None, 0
    for row in rows:
        for field in (row["tag"], row.get("name") or ""):
            score = fuzz.ratio(candidate, normalize_tag(field))
            if score > best_score:
                best_tag, best_score = row["tag"], score
    return best_tag if best_score >= threshold else None
