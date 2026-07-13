"""Qdrant vector DB operations — collections per README storage layer."""
import logging

from qdrant_client import QdrantClient
from qdrant_client.models import (Distance, FieldCondition, Filter, MatchAny,
                                  NamedSparseVector, NamedVector, PointStruct,
                                  SparseIndexParams, SparseVector,
                                  SparseVectorParams, VectorParams)

from app.config import settings

logger = logging.getLogger(__name__)

COLLECTIONS = ["chunks", "procedures", "regulations", "incidents", "audio_clips"]
# Must match the active embedding backend (bge=1024, minilm=384). Driven by .env.
DENSE_DIM = settings.embedding_dim

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _client


def init_collections():
    client = get_client()
    existing = {c.name for c in client.get_collections().collections}
    for name in COLLECTIONS:
        if name in existing:
            continue
        client.create_collection(
            collection_name=name,
            vectors_config={"dense": VectorParams(size=DENSE_DIM, distance=Distance.COSINE)},
            sparse_vectors_config={"sparse": SparseVectorParams(index=SparseIndexParams())},
        )
        logger.info("Created Qdrant collection: %s", name)


def upsert_chunks(collection: str, points: list[dict]):
    """points: [{id, dense, sparse, payload}]"""
    structs = []
    for p in points:
        vectors = {"dense": p["dense"]}
        if p.get("sparse"):
            vectors["sparse"] = SparseVector(
                indices=list(p["sparse"].keys()), values=list(p["sparse"].values()))
        structs.append(PointStruct(id=p["id"], vector=vectors, payload=p["payload"]))
    get_client().upsert(collection_name=collection, points=structs)


def search(collection: str, query_vec: dict, limit: int = 10,
           equipment_filter: list[str] | None = None) -> list[dict]:
    """Hybrid: dense + sparse searches, merged by reciprocal rank fusion."""
    client = get_client()
    qfilter = None
    if equipment_filter:
        qfilter = Filter(must=[FieldCondition(key="equipment_tags", match=MatchAny(any=equipment_filter))])

    dense_hits = client.search(
        collection_name=collection,
        query_vector=NamedVector(name="dense", vector=query_vec["dense"]),
        query_filter=qfilter, limit=limit, with_payload=True,
    )
    sparse_hits = []
    if query_vec.get("sparse"):
        sparse_hits = client.search(
            collection_name=collection,
            query_vector=NamedSparseVector(name="sparse", vector=SparseVector(
                indices=list(query_vec["sparse"].keys()),
                values=list(query_vec["sparse"].values()))),
            query_filter=qfilter, limit=limit, with_payload=True,
        )

    # Reciprocal rank fusion
    scores: dict = {}
    for rank, hit in enumerate(dense_hits):
        scores.setdefault(hit.id, {"hit": hit, "score": 0})["score"] += 1 / (60 + rank + 1)
    for rank, hit in enumerate(sparse_hits):
        scores.setdefault(hit.id, {"hit": hit, "score": 0})["score"] += 1 / (60 + rank + 1)
    ranked = sorted(scores.values(), key=lambda x: -x["score"])[:limit]
    return [{"id": r["hit"].id, "score": r["score"], "payload": r["hit"].payload} for r in ranked]


def collection_stats() -> dict:
    client = get_client()
    stats = {}
    for name in COLLECTIONS:
        try:
            info = client.get_collection(name)
            stats[name] = info.points_count
        except Exception:
            stats[name] = 0
    return stats
