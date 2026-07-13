"""Verify every infrastructure service is reachable."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


@check("PostgreSQL")
def _pg():
    from sqlalchemy import text
    from app.models.db_models import engine
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


@check("Neo4j")
def _neo():
    from app.services import neo4j_service
    neo4j_service.run("RETURN 1")


@check("Qdrant")
def _qdrant():
    from app.services import qdrant_service
    qdrant_service.get_client().get_collections()


@check("Redis")
def _redis():
    import redis
    redis.from_url(settings.redis_url).ping()


@check("Kafka")
def _kafka():
    from confluent_kafka.admin import AdminClient
    AdminClient({"bootstrap.servers": settings.kafka_bootstrap_servers}).list_topics(timeout=10)


@check("MinIO")
def _minio():
    from app.services import minio_service
    minio_service.get_client().list_buckets()


@check("OpenAI API")
def _openai():
    from app.services.llm_service import chat
    chat([{"role": "user", "content": "Reply with exactly: OK"}])


if __name__ == "__main__":
    failures = 0
    for name, fn in CHECKS:
        try:
            fn()
            print(f"  [OK]   {name}")
        except Exception as e:
            failures += 1
            print(f"  [FAIL] {name}: {e}")
    print(f"\n{len(CHECKS) - failures}/{len(CHECKS)} services healthy")
    sys.exit(1 if failures else 0)
