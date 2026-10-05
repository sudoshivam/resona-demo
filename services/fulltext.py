"""Full-text RAG for the paper-discussion chatbot (increment 2).

When a paper is open-access with a usable PDF, fetch + extract its text, split it
into fixed-size overlapping chunks, embed them (reusing services.embeddings), and
retrieve the chunks most relevant to the user's question. Everything here degrades
to None on any failure — the caller falls back to the abstract path, which is a
normal, common outcome (most papers are not OA with a clean PDF).

The extracted+embedded chunks are cached per paper in a bounded in-memory LRU so
the expensive fetch/extract/embed happens once per paper, not once per message.
"""

import asyncio
import io
from collections import OrderedDict
from typing import Dict, List, Optional

import httpx
from pypdf import PdfReader

from config import (
    logger,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    RAG_TOP_K,
    MAX_FULLTEXT_CHARS,
    MAX_FULLTEXT_BYTES,
    FULLTEXT_TIMEOUT,
)
from services.embeddings import embed_texts, cosine_similarity


class LRUCache:
    """Bounded least-recently-used cache with a hard cap.

    Never holds more than `maxsize` entries: `set` evicts the oldest until the
    size is within the cap, and `get` refreshes recency. This is ephemeral
    process state (lost on restart), not a database.
    """

    def __init__(self, maxsize: int):
        self.maxsize = max(1, maxsize)
        self._data: "OrderedDict[str, dict]" = OrderedDict()

    def get(self, key: str) -> Optional[dict]:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def set(self, key: str, value: dict) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self.maxsize:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: str) -> bool:
        return key in self._data


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into fixed-size overlapping character windows.

    Pragmatic, tokenizer-free chunking. Empty/whitespace text -> []. Text shorter
    than `size` -> a single chunk.
    """
    text = (text or "").strip()
    if not text:
        return []
    if size <= 0:
        return [text]
    step = max(1, size - max(0, overlap))
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        chunks.append(text[start : start + size])
        if start + size >= n:
            break
        start += step
    return chunks


def select_top_k_chunks(
    query_vec: List[float],
    chunk_vecs: List[List[float]],
    chunks: List[str],
    k: int = RAG_TOP_K,
) -> List[str]:
    """Return the k chunks most similar to the query, highest similarity first.

    k larger than the number of chunks returns all of them; empty inputs -> [].
    """
    if not chunks or not chunk_vecs:
        return []
    scored = [
        (cosine_similarity(query_vec, vec), chunk)
        for vec, chunk in zip(chunk_vecs, chunks)
    ]
    scored.sort(key=lambda t: t[0], reverse=True)
    return [chunk for _, chunk in scored[: max(0, k)]]


def extract_pdf_text(data: bytes, max_chars: int = MAX_FULLTEXT_CHARS) -> str:
    """Extract 'good enough' body text from PDF bytes via pypdf.

    Concatenates per-page text, capped at `max_chars`. Any parse failure -> "".
    """
    try:
        reader = PdfReader(io.BytesIO(data))
        parts: List[str] = []
        total = 0
        for page in reader.pages:
            try:
                page_text = page.extract_text() or ""
            except Exception:
                continue
            if not page_text:
                continue
            parts.append(page_text)
            total += len(page_text)
            if total >= max_chars:
                break
        return "\n".join(parts).strip()[:max_chars]
    except Exception:
        return ""


async def fetch_pdf(
    client: httpx.AsyncClient,
    url: str,
    timeout: int = FULLTEXT_TIMEOUT,
    max_bytes: int = MAX_FULLTEXT_BYTES,
) -> Optional[bytes]:
    """Download a PDF over HTTP, or return None if it can't be used.

    Follows redirects (oa_url often redirects to the actual file), enforces a size
    cap, and verifies the %PDF magic bytes so HTML landing pages fall through to
    the abstract path rather than being mis-parsed. Any error -> None.
    """
    try:
        resp = await client.get(url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        return None

    content_length = resp.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > max_bytes:
        return None

    content = resp.content
    if len(content) > max_bytes:
        return None
    if not content[:5].startswith(b"%PDF"):
        return None
    return content


async def get_or_fetch_fulltext(
    client: httpx.AsyncClient,
    cache: LRUCache,
    key: str,
    oa_url: str,
    max_chars: int = MAX_FULLTEXT_CHARS,
) -> Optional[str]:
    """Return cached extracted text, or fetch, extract, and cache it once."""
    cached = cache.get(key) if key else None
    if cached and "text" in cached:
        return cached["text"]

    data = await fetch_pdf(client, oa_url)
    if not data:
        return None
    text = await asyncio.to_thread(extract_pdf_text, data, max_chars)
    if not text:
        return None

    if key:
        cache.set(key, {**(cached or {}), "text": text})
    return text


async def get_fulltext_excerpts(
    client: httpx.AsyncClient,
    model,
    cache: LRUCache,
    key: str,
    oa_url: str,
    question: str,
    top_k: int = RAG_TOP_K,
) -> Optional[List[str]]:
    """Resolve the top-k full-text excerpts relevant to `question`, or None.

    Reuses cached chunks+embeddings for a paper when present; otherwise fetches,
    extracts, chunks, and embeds once and caches the result. Returns None on ANY
    failure or empty result so the caller cleanly falls back to the abstract.
    """
    try:
        cached: Optional[Dict[str, object]] = cache.get(key) if key else None
        if cached is None or "chunks" not in cached or "embeddings" not in cached:
            text = cached.get("text") if cached else None
            if not isinstance(text, str):
                text = await get_or_fetch_fulltext(client, cache, key, oa_url)
            if not text:
                return None
            chunks = chunk_text(text)
            if not chunks:
                return None
            embeddings = await embed_texts(model, chunks)
            cached = {"text": text, "chunks": chunks, "embeddings": embeddings}
            if key:
                cache.set(key, cached)

        chunks = cached["chunks"]
        chunk_vecs = cached["embeddings"]
        if not question or not chunks:
            return None

        query_vec = (await embed_texts(model, [question]))[0]
        excerpts = select_top_k_chunks(query_vec, chunk_vecs, chunks, top_k)
        return excerpts or None
    except Exception as e:
        logger.warning(f"Full-text RAG failed for {key or oa_url}: {type(e).__name__}: {e}")
        return None
