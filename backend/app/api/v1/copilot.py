"""Copilot endpoints: query, streaming WS, history, feedback."""
import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.agents import copilot_agent
from app.auth.jwt import decode_token
from app.auth.rbac import require
from app.models.db_models import QueryLog, get_db
from app.models.pydantic_models import CopilotAnswer, CopilotQuery, FeedbackIn

router = APIRouter()
ws_router = APIRouter()


@router.post("/query", response_model=CopilotAnswer)
def query(body: CopilotQuery, user: dict = Depends(require("copilot")),
          db: Session = Depends(get_db)):
    result = copilot_agent.answer_query(
        body.query, body.equipment_filter, body.include_knowledge_capsules, body.language)
    log = QueryLog(user_email=user["email"], query=body.query, answer=result["answer"],
                   confidence=result["confidence"], citations=result["citations"],
                   response_time_ms=result["response_time_ms"])
    db.add(log)
    db.commit()
    result["query_log_id"] = log.id
    return result


@router.get("/history")
def history(user: dict = Depends(require("copilot")), db: Session = Depends(get_db)):
    logs = (db.query(QueryLog).filter(QueryLog.user_email == user["email"])
            .order_by(QueryLog.created_at.desc()).limit(50).all())
    return [{"id": l.id, "query": l.query, "answer": l.answer,
             "confidence": l.confidence, "citations": l.citations,
             "created_at": l.created_at.isoformat()} for l in logs]


@router.get("/benchmark")
def benchmark(user: dict = Depends(require("copilot"))):
    """Serve the latest benchmark run summary (accuracy, citation rate, latency).
    Returns {available: false} until scripts/run_benchmark.py has been run."""
    path = Path(__file__).resolve().parents[3] / "data" / "benchmark_results.json"
    if not path.exists():
        return {"available": False}
    try:
        data = json.loads(path.read_text())
        return {"available": True, "summary": data.get("summary", {})}
    except Exception:
        return {"available": False}


@router.post("/feedback")
def feedback(body: FeedbackIn, user: dict = Depends(require("copilot")),
             db: Session = Depends(get_db)):
    log = db.query(QueryLog).get(body.query_log_id)
    if log:
        log.feedback = body.feedback
        db.commit()
    return {"ok": True}


@ws_router.websocket("/ws/copilot/stream")
async def ws_stream(websocket: WebSocket):
    """Client sends {token, query, equipment_filter?}; server streams
    {type: meta|token|done|error, ...} messages."""
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            req = json.loads(raw)
            try:
                decode_token(req.get("token", ""))
            except Exception:
                await websocket.send_text(json.dumps({"type": "error", "detail": "auth failed"}))
                continue

            loop = asyncio.get_event_loop()
            gen = copilot_agent.stream_answer(
                req["query"], req.get("equipment_filter", []),
                req.get("include_knowledge_capsules", True))

            def next_item(g=gen):
                try:
                    return next(g)
                except StopIteration:
                    return None

            while True:
                item = await loop.run_in_executor(None, next_item)
                if item is None:
                    break
                kind, payload = item
                if kind == "token":
                    await websocket.send_text(json.dumps({"type": "token", "token": payload}))
                else:
                    await websocket.send_text(json.dumps({"type": kind, **payload}))
    except WebSocketDisconnect:
        pass
