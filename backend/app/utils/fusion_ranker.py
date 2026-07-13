"""Reciprocal Rank Fusion for merging vector hits and graph-derived facts."""


def rrf_merge(result_lists: list[list[dict]], k: int = 60, limit: int = 12) -> list[dict]:
    """Each result list is ranked best-first; items need a stable 'key' field."""
    scores: dict = {}
    for results in result_lists:
        for rank, item in enumerate(results):
            entry = scores.setdefault(item["key"], {"item": item, "score": 0.0})
            entry["score"] += 1.0 / (k + rank + 1)
    ranked = sorted(scores.values(), key=lambda x: -x["score"])
    return [dict(r["item"], fusion_score=r["score"]) for r in ranked[:limit]]
