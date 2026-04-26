from __future__ import annotations

# Optional adapter — only imported when [embeddings] enabled = true.
# Install: pip install cartograph[embeddings]

try:
    from fastembed import TextEmbedding
    import numpy as np
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_model = None


def available() -> bool:
    return _AVAILABLE


def embed(texts: list[str]) -> "np.ndarray":
    if not _AVAILABLE:
        raise RuntimeError("fastembed not installed — run: pip install cartograph[embeddings]")
    global _model
    if _model is None:
        _model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return np.array(list(_model.embed(texts)))


def cosine_sim(a: "np.ndarray", b: "np.ndarray") -> float:
    if not _AVAILABLE:
        raise RuntimeError("fastembed not installed — run: pip install cartograph[embeddings]")
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
