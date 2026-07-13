"""Download local models: BGE-M3 embeddings, Whisper large-v3.

Usage: python scripts/download_models.py --models bge-m3,whisper-large-v3
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def download_bge():
    from FlagEmbedding import BGEM3FlagModel
    print("Downloading BAAI/bge-m3 (~2.2GB)...")
    BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
    print("BGE-M3 ready.")


def download_whisper():
    import whisper
    from app.config import settings
    print(f"Downloading Whisper {settings.whisper_model} (~3GB)...")
    whisper.load_model(settings.whisper_model)
    print("Whisper ready.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default="bge-m3,whisper-large-v3")
    args = parser.parse_args()
    wanted = args.models.split(",")
    if "bge-m3" in wanted:
        download_bge()
    if "whisper-large-v3" in wanted:
        download_whisper()
