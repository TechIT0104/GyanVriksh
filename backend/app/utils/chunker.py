"""Semantic chunking via LangChain RecursiveCharacterTextSplitter.
chunk_size/overlap are in tokens approximated as chars*4 per README config."""
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings

# README: 512 tokens, 80 token overlap. Approximate 1 token ≈ 4 chars.
splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.chunk_size * 4,
    chunk_overlap=settings.chunk_overlap * 4,
    separators=["\n\n", "\n", ". ", " "],
)


def chunk_pages(pages: list[dict]) -> list[dict]:
    """pages: [{page, text}] -> [{page, chunk_index, text}]"""
    chunks = []
    idx = 0
    for p in pages:
        for piece in splitter.split_text(p["text"] or ""):
            if piece.strip():
                chunks.append({"page": p["page"], "chunk_index": idx, "text": piece.strip()})
                idx += 1
    return chunks
