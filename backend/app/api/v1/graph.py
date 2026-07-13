"""Knowledge graph endpoints."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.auth.rbac import require
from app.models.pydantic_models import GraphQueryRequest
from app.services import neo4j_service

router = APIRouter()


def _months_left(ret, today: date):
    if not ret:
        return None
    try:
        y, m, _ = (int(x) for x in str(ret)[:10].split("-"))
    except Exception:
        return None
    return (y - today.year) * 12 + (m - today.month)


@router.get("/cliff-risk")
def cliff_risk(years: int = 3, user: dict = Depends(require("graph"))):
    """Knowledge Cliff Risk: which expertise is about to walk out the door.

    Flags experts retiring within `years`, the equipment whose knowledge depends
    on them (no recorded capsule = unpreserved), and the share of the plant's
    hands-on work-order history held by soon-to-retire people.
    """
    data = neo4j_service.cliff_data()
    today = date.today()
    horizon = years * 12

    experts = []
    for p in data["persons"]:
        ml = _months_left(p.get("retirement"), today)
        retiring = ml is not None and 0 <= ml <= horizon
        if retiring and (p.get("capsules") or 0) == 0:
            status = "KNOWLEDGE AT RISK"
        elif retiring:
            status = "RETIRING SOON"
        else:
            status = "ACTIVE"
        experts.append({
            "name": p["name"], "designation": p.get("designation"),
            "department": p.get("department"), "expertise": p.get("expertise") or [],
            "years": p.get("years"), "retirement": p.get("retirement"),
            "months_left": ml, "retiring": retiring,
            "equipment": p.get("equipment") or [], "workorders": p.get("workorders") or 0,
            "capsules": p.get("capsules") or 0, "status": status,
        })

    retiring_names = {p["name"] for p in experts if p["retiring"]}
    at_risk_equipment = []
    for e in data["equipment"]:
        retiring_experts = sorted({
            x["name"] for x in e.get("experts", []) if x.get("name") in retiring_names
        })
        if retiring_experts and (e.get("capsules") or 0) == 0:
            at_risk_equipment.append({"tag": e["tag"], "type": e.get("type"),
                                      "experts": retiring_experts})

    total_wo = sum(p["workorders"] for p in experts) or 1
    wo_at_risk = sum(p["workorders"] for p in experts if p["retiring"])
    experts.sort(key=lambda x: (x["months_left"] is None, x["months_left"] if x["months_left"] is not None else 9999))

    return {
        "summary": {
            "horizon_years": years,
            "experts_retiring": sum(1 for p in experts if p["retiring"]),
            "total_experts": len(experts),
            "equipment_at_risk": len(at_risk_equipment),
            "knowledge_at_risk_pct": round(100 * wo_at_risk / total_wo),
        },
        "experts": experts,
        "equipment_at_risk": at_risk_equipment,
    }


@router.get("/nodes")
def nodes(limit: int = 500, user: dict = Depends(require("graph"))):
    return neo4j_service.full_graph(limit=min(limit, 2000))


@router.get("/equipment/{tag_id}")
def equipment_subgraph(tag_id: str, depth: int = 2, user: dict = Depends(require("graph"))):
    result = neo4j_service.subgraph(tag_id.upper(), depth)
    if not result.get("nodes"):
        raise HTTPException(404, f"No subgraph for {tag_id}")
    return result


@router.get("/stats")
def stats(user: dict = Depends(require("graph"))):
    return neo4j_service.stats()


@router.post("/query")
def custom_query(body: GraphQueryRequest, user: dict = Depends(require("admin"))):
    forbidden = ["delete", "detach", "remove", "drop", "create user", "set password"]
    if any(f in body.cypher.lower() for f in forbidden):
        raise HTTPException(403, "Destructive Cypher not allowed via API")
    return neo4j_service.run(body.cypher, **body.params)
