"""Load OISD / Factories Act / PESO regulation clauses into Neo4j + Qdrant."""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import embedding_service, neo4j_service, qdrant_service

REG_FILE = Path(__file__).resolve().parent.parent / "data/regulations/regulations.json"


def main():
    regs = json.loads(REG_FILE.read_text())
    texts = [f"{r['standard']} Section {r['section']} — {r['title']}: {r['text']}" for r in regs]
    vectors = embedding_service.embed(texts)

    points = []
    for r, text, vec in zip(regs, texts, vectors):
        neo4j_service.upsert_node("Regulation", r["reg_id"], r)
        points.append({
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, r["reg_id"])),
            "dense": vec["dense"], "sparse": vec["sparse"],
            "payload": {"chunk_id": r["reg_id"], "file_id": r["reg_id"], "page": 1,
                        "text": text, "doc_type": "REGULATION", "equipment_tags": []},
        })
    qdrant_service.upsert_chunks("regulations", points)
    qdrant_service.upsert_chunks("chunks", points)
    print(f"Loaded {len(regs)} regulation clauses into Neo4j + Qdrant.")


if __name__ == "__main__":
    main()
