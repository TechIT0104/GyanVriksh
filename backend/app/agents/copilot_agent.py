"""Expert Knowledge Copilot — hybrid RAG per README 4.4.

3 steps: query understanding -> hybrid retrieval (Qdrant + Neo4j) -> cited generation.
"""
import json
import logging
import re
import time

from app.services import analytics, embedding_service, neo4j_service, qdrant_service
from app.services.llm_service import chat, chat_json, stream_chat
from app.utils.fusion_ranker import rrf_merge

logger = logging.getLogger(__name__)

# Queries about retirement / expertise loss get the computed workforce analytics
# injected as context, so the Copilot answers the "knowledge cliff" from facts.
CLIFF_KEYWORDS = ("retire", "retiring", "retirement", "knowledge cliff", "at risk",
                  "successor", "who knows", "expert on", "expertise", "leaving",
                  "years of experience", "walk out", "before they")

QUERY_UNDERSTANDING_PROMPT = """Analyze this industrial plant query. Return JSON:
{"intent": "MAINTENANCE_LOOKUP|COMPLIANCE_CHECK|PROCEDURE_QUERY|FAILURE_ANALYSIS|GENERAL",
 "equipment_tags": ["P-101"], "regulations": ["OISD-116"], "language": "en|hi|hinglish",
 "time_scope": "historical|current|predictive"}
Equipment tags follow patterns like P-101, HE-302, FI-101, V-201, C-401, K-101."""

COPILOT_SYSTEM = """You are GyanVriksh, an expert AI assistant for industrial plant operations.
You have access to indexed maintenance records, safety procedures, regulatory documents,
and expert knowledge from experienced engineers.

RULES:
1. ONLY answer based on the provided context. Never hallucinate.
2. EVERY factual claim must include a citation: [Doc: {{doc_id}}, Page {{page}}]
3. If information is not in context, say: "This information is not in my indexed documents.
   Please consult the relevant engineer."
4. For safety-critical queries, always add: "Verify with the designated safety officer
   before proceeding."
5. If the query is in Hindi or Hinglish, respond in the same language.
6. If expert knowledge capsules are in context, attribute them by expert name and
   mention they are verified spoken knowledge.

CONTEXT:
{context}

KNOWLEDGE GRAPH DATA:
{graph_data}"""


def understand_query(query: str) -> dict:
    """Lightweight, LLM-free query analysis. Extracting equipment tags and
    regulation refs by regex is just as reliable for retrieval as an LLM call,
    and it removes a full model round-trip (~halves latency on CPU Ollama)."""
    up = query.upper()
    tags = list(dict.fromkeys(re.findall(r"\b[A-Z]{1,4}-\d{2,4}\b", up)))
    regs = list(dict.fromkeys(re.findall(r"\bOISD-\d{3}\b", up)))
    # crude language hint: Devanagari -> hi, else en (model still mirrors input)
    lang = "hi" if re.search(r"[ऀ-ॿ]", query) else "en"
    return {"intent": "GENERAL", "equipment_tags": tags, "regulations": regs,
            "language": lang, "time_scope": "current"}


def retrieve(query: str, analysis: dict, equipment_filter: list[str],
             include_capsules: bool = True) -> tuple[list[dict], dict]:
    """Returns (fused chunk list, graph data dict)."""
    qvec = embedding_service.embed_query(query)
    tags = list({*analysis.get("equipment_tags", []), *equipment_filter})

    vector_hits = qdrant_service.search("chunks", qvec, limit=10)
    vector_results = [
        {"key": h["payload"]["chunk_id"], "text": h["payload"]["text"],
         "doc_id": h["payload"]["file_id"], "page": h["payload"]["page"]}
        for h in vector_hits
    ]

    graph_data: dict = {}
    graph_results: list[dict] = []
    for tag in tags[:3]:
        view = neo4j_service.equipment_360(tag)
        if not view:
            continue
        graph_data[tag] = view
        for wo in view["workorders"][:5]:
            graph_results.append({
                "key": f"wo-{wo.get('wo_id')}", "doc_id": wo.get("wo_id", "WO"),
                "page": 1, "text": f"Work order {wo.get('wo_id')} on {wo.get('date')}: "
                f"{wo.get('description', '')}. Findings: {wo.get('findings', '')}"})
        for inc in view["incidents"][:3]:
            graph_results.append({
                "key": f"inc-{inc.get('incident_id')}", "doc_id": inc.get("incident_id", "INC"),
                "page": 1, "text": f"Incident {inc.get('incident_id')} ({inc.get('date')}): "
                f"{inc.get('description', '')} Root cause: {inc.get('root_cause', '')}"})
        if include_capsules:
            for kc in view["capsules"]:
                graph_results.append({
                    "key": f"kc-{kc.get('capsule_id')}", "doc_id": kc.get("capsule_id", "KC"),
                    "page": 1, "is_capsule": True, "capsule": kc,
                    "text": f"Expert knowledge from {kc.get('expert')} (recorded "
                    f"{kc.get('recorded_date')}): {kc.get('insight_text', kc.get('transcript', ''))}"})

    fused = rrf_merge([vector_results, graph_results], limit=12)

    # Inject computed workforce/knowledge-cliff analytics for retirement queries.
    if any(k in query.lower() for k in CLIFF_KEYWORDS):
        try:
            fused.insert(0, {"key": "cliff", "doc_id": "WORKFORCE-ANALYTICS", "page": 1,
                             "text": analytics.cliff_context()})
        except Exception:
            logger.exception("cliff context injection failed")

    return fused, graph_data


def _build_context(chunks: list[dict], max_chunks: int = 5, max_chars: int = 700) -> str:
    """Keep the prompt small so CPU Ollama stays fast: top few chunks, each
    truncated. Retrieval still ranks all chunks; we just cap what the LLM reads."""
    return "\n\n".join(
        f"[Doc: {c['doc_id']}, Page {c['page']}]\n{c['text'][:max_chars]}"
        for c in chunks[:max_chunks])


def _confidence(chunks: list[dict], graph_data: dict) -> str:
    if len(chunks) >= 3 and graph_data:
        return "HIGH"
    if chunks:
        return "MEDIUM"
    return "LOW"


def _citations(answer: str, chunks: list[dict]) -> list[dict]:
    cited_ids = set(re.findall(r"\[Doc:\s*([^,\]]+)", answer))
    cites = []
    for c in chunks:
        if str(c["doc_id"]).strip() in {x.strip() for x in cited_ids}:
            cites.append({"doc_id": str(c["doc_id"]), "page": int(c.get("page", 1)),
                          "excerpt": c["text"][:200]})
    return cites


def answer_query(query: str, equipment_filter: list[str] = [],
                 include_capsules: bool = True, language: str = "en") -> dict:
    t0 = time.time()
    analysis = understand_query(query)
    chunks, graph_data = retrieve(query, analysis, equipment_filter, include_capsules)

    graph_summary = {
        tag: {"workorders": len(v["workorders"]), "incidents": len(v["incidents"]),
              "equipment": v["equipment"]}
        for tag, v in graph_data.items()
    }
    system = COPILOT_SYSTEM.format(
        context=_build_context(chunks) or "(no indexed content matched)",
        graph_data=json.dumps(graph_summary, default=str)[:4000],
    )
    answer = chat([{"role": "system", "content": system},
                   {"role": "user", "content": query}])

    capsules = [
        {"capsule_id": c["capsule"].get("capsule_id"), "expert": c["capsule"].get("expert"),
         "timestamp_sec": c["capsule"].get("timestamp_sec", 0)}
        for c in chunks if c.get("is_capsule")
    ]
    related = sorted({*analysis.get("equipment_tags", []), *equipment_filter})
    return {
        "answer": answer,
        "confidence": _confidence(chunks, graph_data),
        "citations": _citations(answer, chunks),
        "related_entities": related,
        "knowledge_capsules": capsules,
        "graph_nodes_highlighted": related + [c["doc_id"] for c in chunks[:5]],
        "response_time_ms": int((time.time() - t0) * 1000),
    }


def stream_answer(query: str, equipment_filter: list[str] = [],
                  include_capsules: bool = True):
    """Agentic stream: emits ('status', dict) reasoning steps, ('meta', dict),
    then ('token', str) repeatedly, then ('done', dict). The status events let
    the UI show a live reasoning trace so the model's work is transparent."""
    t0 = time.time()

    yield "status", {"step": "understand", "label": "Understanding the question",
                     "state": "active"}
    analysis = understand_query(query)
    tags = sorted(set(analysis.get("equipment_tags", []) + equipment_filter))
    lang = analysis.get("language", "en")
    yield "status", {"step": "understand", "label": "Question parsed", "state": "done",
                     "detail": (("equipment: " + ", ".join(tags)) if tags else "general query")
                     + f" · language: {lang}"}

    yield "status", {"step": "retrieve", "label": "Searching knowledge graph + documents",
                     "state": "active"}
    chunks, graph_data = retrieve(query, analysis, equipment_filter, include_capsules)
    n_docs = len({c["doc_id"] for c in chunks})
    n_caps = sum(1 for c in chunks if c.get("is_capsule"))
    yield "status", {"step": "retrieve", "label": f"Retrieved {len(chunks)} sources", "state": "done",
                     "detail": f"{n_docs} documents · {len(graph_data)} equipment 360° views · "
                     f"{n_caps} expert knowledge capsule(s)"}

    confidence = _confidence(chunks, graph_data)
    # graph_nodes: names the frontend can light up in the 3D knowledge graph
    graph_nodes = tags + [str(c["doc_id"]) for c in chunks[:8]]
    yield "meta", {"confidence": confidence, "related_entities": tags,
                   "language": lang, "graph_nodes": sorted(set(graph_nodes))}

    yield "status", {"step": "generate", "label": "Generating grounded, cited answer",
                     "state": "active"}
    system = COPILOT_SYSTEM.format(
        context=_build_context(chunks) or "(no indexed content matched)",
        graph_data=json.dumps({t: v["equipment"] for t, v in graph_data.items()}, default=str)[:4000],
    )
    full = []
    for token in stream_chat([{"role": "system", "content": system},
                              {"role": "user", "content": query}]):
        full.append(token)
        yield "token", token
    answer = "".join(full)
    citations = _citations(answer, chunks)
    yield "status", {"step": "generate", "label": "Answer grounded in "
                     f"{len(citations)} citation(s)", "state": "done"}
    yield "done", {
        "citations": citations,
        "knowledge_capsules": [
            {"capsule_id": c["capsule"].get("capsule_id"), "expert": c["capsule"].get("expert")}
            for c in chunks if c.get("is_capsule")],
        "response_time_ms": int((time.time() - t0) * 1000),
        "answer": answer,
        "graph_nodes": sorted(set(graph_nodes + [str(x["doc_id"]) for x in citations])),
    }
