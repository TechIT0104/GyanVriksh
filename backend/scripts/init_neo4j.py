"""Initialize Neo4j constraints and indexes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import neo4j_service

if __name__ == "__main__":
    neo4j_service.init_schema()
    print("Neo4j schema initialized.")
