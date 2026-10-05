from dataclasses import dataclass
from typing import Optional

import httpx

from config import logger
from schemas import NormalizedPaper
from services.concurrency import gather_tolerant
from services.dedup import merge_candidates
from services import openalex, crossref, semantic_scholar, arxiv

NORMALIZE_FUNCS = {
    "openalex": openalex.normalize_openalex,
    "crossref": crossref.normalize,
    "semantic_scholar": semantic_scholar.normalize,
    "arxiv": arxiv.normalize,
}


@dataclass(frozen=True)
class SourceFailure:
    source: str
    status_code: Optional[int]
    message: str
    retry_after: Optional[str] = None


@dataclass
class FederationResult:
    papers: list[NormalizedPaper]
    openalex_total: Optional[int]
    successful_sources: list[str]
    failures: list[SourceFailure]


def _describe_failure(source: str, error: Exception) -> SourceFailure:
    """Turn an upstream exception into safe metadata.

    Never include the raw exception string: HTTPX includes request URLs in
    HTTPStatusError messages, and callers may place credentials in a URL.
    """
    if isinstance(error, httpx.HTTPStatusError):
        response = error.response
        status_code = response.status_code
        message = "rate limited" if status_code == 429 else f"HTTP {status_code}"
        return SourceFailure(
            source=source,
            status_code=status_code,
            message=message,
            retry_after=response.headers.get("Retry-After"),
        )

    if isinstance(error, httpx.TimeoutException):
        message = "request timed out"
    elif isinstance(error, httpx.RequestError):
        message = "request failed"
    else:
        message = "upstream request failed"

    return SourceFailure(source=source, status_code=None, message=message)


async def search_all(
    client: httpx.AsyncClient,
    sources: list,
    query: str,
    limit: int,
    openalex_params: dict,
):
    """Fan out to requested sources and retain success/failure metadata."""

    openalex_total = {"count": None}

    async def _fetch_openalex():
        data = await openalex.search_works(client, openalex_params)
        openalex_total["count"] = data.get("meta", {}).get("count", 0)
        return data.get("results", [])

    fetchers = {
        "openalex": _fetch_openalex,
        "crossref": lambda: crossref.search(client, query, limit),
        "semantic_scholar": lambda: semantic_scholar.search(client, query, limit),
        "arxiv": lambda: arxiv.search(client, query, limit),
    }

    active_sources = [s for s in sources if s in fetchers]
    coros = [fetchers[s]() for s in active_sources]
    results = await gather_tolerant(coros)

    normalized: list[NormalizedPaper] = []
    successful_sources: list[str] = []
    failures: list[SourceFailure] = []
    for source, result in zip(active_sources, results):
        if isinstance(result, Exception):
            failure = _describe_failure(source, result)
            failures.append(failure)
            status = f"HTTP {failure.status_code}" if failure.status_code else failure.message
            logger.warning("Federation source '%s' failed: %s", source, status)
            continue
        successful_sources.append(source)
        normalize_fn = NORMALIZE_FUNCS[source]
        for rank, raw_item in enumerate(result, start=1):
            try:
                normalized.append(normalize_fn(raw_item, rank))
            except Exception as e:
                logger.warning(f"Failed to normalize a '{source}' result: {e}")

    merged = merge_candidates(normalized)
    return FederationResult(
        papers=merged,
        openalex_total=openalex_total["count"],
        successful_sources=successful_sources,
        failures=failures,
    )
