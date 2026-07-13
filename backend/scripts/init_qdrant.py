"""Create Qdrant collections (chunks, procedures, regulations, incidents, audio_clips)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import qdrant_service

if __name__ == "__main__":
    qdrant_service.init_collections()
    print("Qdrant collections ready:", qdrant_service.COLLECTIONS)
