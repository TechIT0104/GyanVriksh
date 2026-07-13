"""BGE-M3 embeddings: dense (1024-d) + sparse lexical weights for hybrid search.
Falls back to all-MiniLM-L6-v2 dense-only if FlagEmbedding is unavailable."""
import logging

logger = logging.getLogger(__name__)

_model = None
_fallback = None


def _get_model():
    global _model
    if _model is None:
        from FlagEmbedding import BGEM3FlagModel
        from app.config import settings
        _model = BGEM3FlagModel(settings.embedding_model, use_fp16=True)
    return _model


def _get_fallback():
    global _fallback
    if _fallback is None:
        from sentence_transformers import SentenceTransformer
        _fallback = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _fallback


def embed(texts: list[str]) -> list[dict]:
    """Returns [{dense: [floats], sparse: {token_id: weight}}] per text.

    Backend is chosen by settings.embedding_backend:
      - "bge"    -> BGE-M3 hybrid, 1024-d dense + sparse lexical weights
      - "minilm" -> all-MiniLM-L6-v2, 384-d dense only (sparse empty)
    Falls back to MiniLM automatically if FlagEmbedding can't be imported.
    """
    from app.config import settings
    if settings.embedding_backend != "bge":
        vecs = _get_fallback().encode(texts)
        return [{"dense": v.tolist(), "sparse": {}} for v in vecs]
    try:
        model = _get_model()
        out = model.encode(texts, batch_size=12, max_length=512,
                           return_dense=True, return_sparse=True)
        results = []
        for i in range(len(texts)):
            sparse = {int(k): float(v) for k, v in out["lexical_weights"][i].items()}
            results.append({"dense": out["dense_vecs"][i].tolist(), "sparse": sparse})
        return results
    except ImportError:
        logger.warning("FlagEmbedding unavailable — using MiniLM dense-only fallback")
        vecs = _get_fallback().encode(texts)
        return [{"dense": v.tolist(), "sparse": {}} for v in vecs]


def embed_query(text: str) -> dict:
    return embed([text])[0]
