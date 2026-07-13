"""Industrial NER: GPT-4o few-shot backend (default) or fine-tuned BERT backend."""
import logging
import re

from app.config import settings
from app.services.llm_service import chat_json

logger = logging.getLogger(__name__)

ENTITY_LABELS = [
    "EQUIPMENT_TAG", "EQUIPMENT_TYPE", "PROCESS_PARAM", "REGULATORY_REF",
    "PERSON", "DATE", "LOCATION", "FAILURE_MODE", "ACTION_TAKEN",
    "MATERIAL", "PROCEDURE_REF", "HAZARD_CLASS",
]

NER_SYSTEM_PROMPT = f"""You are an industrial document parser for Indian process plants
(refineries, chemical plants). Extract entities from the given text.

Valid labels: {", ".join(ENTITY_LABELS)}

Guidance:
- EQUIPMENT_TAG: ISA 5.1 style tags like P-101, HE-302, V-15, C-401, K-101, FI-101, PSV-204
- REGULATORY_REF: OISD-116 §4.2, Factory Act Section 36, PESO Rule 2016, IS 2825
- PROCESS_PARAM: numeric value + unit, e.g. 45°C, 8 bar, 120 SLPM, pH 7.2
- PROCEDURE_REF: internal references like SOP-MAINT-047, PTW-2024-0831
- FAILURE_MODE: seal failure, cavitation, corrosion, bearing wear, fouling, vibration
- ACTION_TAKEN: replaced impeller, tightened gland, flushed line, calibrated

Return strict JSON:
{{"entities": [{{"text": "...", "label": "...", "start": 0, "end": 0}}]}}
start/end are character offsets in the input text. Only include entities present verbatim."""

# Regex pre-pass: equipment tags and procedure refs are highly patterned —
# catch them deterministically, LLM handles the rest.
TAG_RE = re.compile(r"\b([A-Z]{1,4})-(\d{2,4})([A-Z]?)\b")
PROC_RE = re.compile(r"\b(SOP|PTW|WO|INC|KC|DOC)-[A-Z0-9-]{2,20}\b")
REG_RE = re.compile(r"\bOISD-\d{3}(?:\s*§?\s*[\d.]+)?\b|\bFactory Act(?:\s*(?:S\.|Section)\s*\d+)?\b|\bPESO[- ]?\d{4}\b")

_bert_pipeline = None


def _regex_entities(text: str) -> list[dict]:
    ents = []
    for m in TAG_RE.finditer(text):
        ents.append({"text": m.group(0), "label": "EQUIPMENT_TAG", "start": m.start(), "end": m.end()})
    for m in PROC_RE.finditer(text):
        ents.append({"text": m.group(0), "label": "PROCEDURE_REF", "start": m.start(), "end": m.end()})
    for m in REG_RE.finditer(text):
        ents.append({"text": m.group(0), "label": "REGULATORY_REF", "start": m.start(), "end": m.end()})
    return ents


def _gpt4o_entities(text: str) -> list[dict]:
    result = chat_json([
        {"role": "system", "content": NER_SYSTEM_PROMPT},
        {"role": "user", "content": f"Extract entities from:\n\n{text}"},
    ])
    ents = result.get("entities", [])
    return [e for e in ents if e.get("label") in ENTITY_LABELS and e.get("text")]


def _bert_entities(text: str) -> list[dict]:
    global _bert_pipeline
    if _bert_pipeline is None:
        from transformers import pipeline
        _bert_pipeline = pipeline(
            "token-classification", model=settings.ner_model_path,
            aggregation_strategy="simple",
        )
    out = _bert_pipeline(text)
    return [
        {"text": e["word"], "label": e["entity_group"], "start": int(e["start"]), "end": int(e["end"])}
        for e in out
    ]


def extract_entities(text: str) -> list[dict]:
    """Merge regex pre-pass with model extraction, dedupe by (text, label)."""
    ents = _regex_entities(text)
    try:
        model_ents = _bert_entities(text) if settings.ner_backend == "bert" else _gpt4o_entities(text)
    except Exception:
        logger.exception("Model NER failed; returning regex entities only")
        model_ents = []
    seen = {(e["text"].lower(), e["label"]) for e in ents}
    for e in model_ents:
        key = (e["text"].lower(), e["label"])
        if key not in seen:
            seen.add(key)
            ents.append(e)
    return ents
