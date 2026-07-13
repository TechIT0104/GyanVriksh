"""Workforce / knowledge-cliff analytics computed from the knowledge graph.
Shared by the /graph/cliff-risk endpoint and the Copilot (so retirement /
knowledge-at-risk questions are answered from the same computed facts)."""
from datetime import date

from app.services import neo4j_service


def _months_left(ret, today: date):
    if not ret:
        return None
    try:
        y, m, _ = (int(x) for x in str(ret)[:10].split("-"))
    except Exception:
        return None
    return (y - today.year) * 12 + (m - today.month)


def cliff_risk(years: int = 3) -> dict:
    """Experts retiring within `years`, equipment whose knowledge depends on them
    with no recorded capsule, and the share of work-order history they hold."""
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
    experts.sort(key=lambda x: (x["months_left"] is None,
                                x["months_left"] if x["months_left"] is not None else 9999))

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


def cliff_context() -> str:
    """A compact factual paragraph the Copilot can cite when answering
    retirement / knowledge-at-risk questions."""
    d = cliff_risk(3)
    s = d["summary"]
    lines = []
    for e in d["experts"]:
        if not e["retiring"]:
            continue
        exp = ", ".join(e["expertise"]) or "general"
        eq = ", ".join(e["equipment"]) or "—"
        lines.append(
            f"{e['name']} ({e['designation'] or 'staff'}, {e['department'] or '—'}) retires "
            f"{e['retirement']} (in ~{e['months_left']} months); expertise: {exp}; "
            f"knows equipment: {eq}; recorded {e['capsules']} knowledge capsule(s) "
            f"[{e['status']}].")
    risk_eq = "; ".join(f"{q['tag']} (depends on {', '.join(q['experts'])})"
                        for q in d["equipment_at_risk"]) or "none"
    return (
        f"WORKFORCE KNOWLEDGE-CLIFF ANALYSIS (retiring within 3 years): "
        f"{s['experts_retiring']} of {s['total_experts']} experts retiring soon; "
        f"{s['equipment_at_risk']} equipment items are unpreserved (no recorded capsule); "
        f"{s['knowledge_at_risk_pct']}% of hands-on work-order history is held by retiring staff.\n"
        f"Retiring experts: " + " ".join(lines) + f"\nUnpreserved equipment at risk: {risk_eq}."
    )
