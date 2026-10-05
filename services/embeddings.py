import asyncio
from typing import List

import numpy as np
from fastembed import TextEmbedding


def load_model(model_name: str) -> TextEmbedding:
    """Construct and load weights for the embedding model. Call once, at
    startup (main.py's lifespan) — this is what pays the (possibly
    first-run-download) cost eagerly, matching the httpx.AsyncClient
    precedent, rather than paying it on the first request."""
    return TextEmbedding(model_name=model_name)


def _embed_sync(model: TextEmbedding, texts: List[str]) -> List[List[float]]:
    return [vec.tolist() for vec in model.embed(texts)]


async def embed_texts(model: TextEmbedding, texts: List[str]) -> List[List[float]]:
    """Batch-embed a list of texts in one call. fastembed's .embed() is
    synchronous, CPU-bound ONNX inference, not I/O — calling it directly
    inside an async route would block the event loop for every other
    in-flight request, so it's offloaded to a thread here."""
    return await asyncio.to_thread(_embed_sync, model, texts)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    a_arr = np.array(a, dtype=float)
    b_arr = np.array(b, dtype=float)
    denom = float(np.linalg.norm(a_arr) * np.linalg.norm(b_arr))
    if denom == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)
