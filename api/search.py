from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Request

from config import (
    limiter,
    logger,
    RATE_LIMIT_SEARCH,
    FEDERATION_SOURCES,
    FEDERATION_OVER_FETCH_MULTIPLIER,
    FEDERATION_OVER_FETCH_CAP,
)
from models import ErrorResponse
from services.openalex import search_authors
from services.federation import SourceFailure, search_all
from ranking import build_paper_result
from reranking import semantic_rerank

router = APIRouter()

SOURCE_DISPLAY_NAMES = {
    "openalex": "OpenAlex",
    "crossref": "Crossref",
    "semantic_scholar": "Semantic Scholar",
    "arxiv": "arXiv",
}


def _all_sources_failed_detail(failures: list[SourceFailure]) -> str:
    summaries = []
    for failure in failures:
        source_name = SOURCE_DISPLAY_NAMES.get(failure.source, failure.source)
        status = f"HTTP {failure.status_code}" if failure.status_code else failure.message
        summaries.append(f"{source_name}: {status}")

    detail = "All requested search sources failed."
    if summaries:
        detail += f" {'; '.join(summaries)}."

    if any(f.source == "openalex" and f.status_code == 429 for f in failures):
        detail += (
            " OpenAlex rate-limited the request; add a free OPENALEX_API_KEY "
            "to .env (https://openalex.org/settings/api)."
        )
    return detail


@router.get(
    "/search",
    responses={502: {"model": ErrorResponse, "description": "All requested sources failed"}},
)
@limiter.limit(RATE_LIMIT_SEARCH)
async def search_papers(
    request: Request,
    topic: str = Query(..., description="Research topic or keywords"),
    limit: int = Query(10, ge=1, le=50, description="Results per page"),
    page: int = Query(1, ge=1, description="Page number"),
    start_year: Optional[int] = Query(None, description="Start year filter"),
    end_year: Optional[int] = Query(None, description="End year filter"),
    open_access_only: bool = Query(False, description="Only open access papers"),
    min_citations: int = Query(0, ge=0, description="Minimum citation count"),
    sort_by: str = Query("relevance", description="Sort: relevance, citations, year_desc, year_asc"),
    type_filter: Optional[str] = Query(None, description="Work type: article, review, book-chapter, etc."),
    author: Optional[str] = Query(None, description="Author name filter"),
    sources: Optional[str] = Query(
        None,
        description="Comma-separated: openalex,crossref,semantic_scholar,arxiv. Default: openalex only.",
    ),
    rerank: bool = Query(
        False,
        description="Rerank by semantic similarity to the query (local embedding model), "
                    "fused with the existing keyword/citation/recency ordering via reciprocal "
                    "rank fusion — not a replacement. No-op if the embedding model isn't loaded.",
    ),
):
    client = request.app.state.http_client
    current_year = datetime.now().year

    if not start_year:
        start_year = current_year - 5
    if not end_year:
        end_year = current_year

    if sources:
        source_list = [s.strip() for s in sources.split(",") if s.strip()]
        if not source_list:
            raise HTTPException(status_code=400, detail="At least one search source is required.")
        unknown = [s for s in source_list if s not in FEDERATION_SOURCES]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown source(s): {', '.join(unknown)}. Valid: {', '.join(FEDERATION_SOURCES)}",
            )
    else:
        source_list = ["openalex"]

    is_federated = source_list != ["openalex"]
    # Reranking needs the same over-fetched candidate pool federation does —
    # otherwise there's nothing beyond the current page to promote from.
    needs_over_fetch = is_federated or rerank

    filters = [
        f"from_publication_date:{start_year}-01-01",
        f"to_publication_date:{end_year}-12-31",
    ]

    if open_access_only:
        filters.append("open_access.is_oa:true")

    if min_citations > 0:
        filters.append(f"cited_by_count:>{min_citations}")

    if type_filter:
        filters.append(f"type:{type_filter}")

    if author:
        # Resolve author name to OpenAlex author ID (display_name.search is not a valid filter)
        # OpenAlex-only, by design — not extended to federation this phase.
        try:
            author_results = await search_authors(client, author)
            if author_results:
                author_id = author_results[0]["id"]
                filters.append(f"authorships.author.id:{author_id}")
                logger.info(f"Resolved author '{author}' → {author_id} ({author_results[0]['display_name']})")
            else:
                logger.warning(f"Author '{author}' not found in OpenAlex, skipping author filter")
        except Exception as e:
            logger.warning(f"Author lookup failed for '{author}': {e}")

    sort_mapping = {
        "relevance": "relevance_score:desc",
        "citations": "cited_by_count:desc",
        "year_desc": "publication_year:desc",
        "year_asc": "publication_year:asc",
    }

    # Single-source, non-reranked (default) requests pass page/per_page
    # straight through to OpenAlex, unchanged from before. Federated and/or
    # reranked requests over-fetch a fixed window from page 1 and paginate
    # the merged/reranked result server-side instead — OpenAlex's own
    # "page" can't correctly window a cross-source merged list, and
    # reranking needs a larger pool than one page to promote candidates from.
    if needs_over_fetch:
        fetch_limit = min(limit * FEDERATION_OVER_FETCH_MULTIPLIER, FEDERATION_OVER_FETCH_CAP)
        openalex_page = 1
        openalex_per_page = fetch_limit
    else:
        fetch_limit = limit
        openalex_page = page
        openalex_per_page = limit

    openalex_params = {
        "search": topic,
        "filter": ",".join(filters),
        "sort": sort_mapping.get(sort_by, "relevance_score:desc"),
        "per_page": openalex_per_page,
        "page": openalex_page,
    }

    federation_result = await search_all(
        client, source_list, topic, fetch_limit, openalex_params
    )

    if not federation_result.successful_sources:
        detail = _all_sources_failed_detail(federation_result.failures)
        retry_after = next(
            (failure.retry_after for failure in federation_result.failures if failure.retry_after),
            None,
        )
        headers = {"Retry-After": retry_after} if retry_after else None
        raise HTTPException(status_code=502, detail=detail, headers=headers)

    merged_papers = federation_result.papers
    openalex_total = federation_result.openalex_total

    if not merged_papers:
        return {
            "topic": topic,
            "years_filter": f"{start_year}-{end_year}",
            "total_found": 0,
            "total_journals": 0,
            "page": page,
            "results": []
        }

    ranked_results = []
    abstracts_by_id = {}
    for p in merged_papers:
        result = build_paper_result(p, start_year, end_year)
        ranked_results.append(result)
        abstracts_by_id[result["id"]] = p.abstract

    # Uniform post-filter over the merged set. Safe no-op for OpenAlex results
    # (already server-side filtered natively) — actually enforces the filter
    # for other sources, which have no native filter support wired up.
    def _passes_filters(r):
        if open_access_only and not r["open_access"]:
            return False
        if min_citations > 0 and r["citations"] < min_citations:
            return False
        if type_filter and r["type"] != type_filter:
            return False
        if r["year"] and not (start_year <= r["year"] <= end_year):
            return False
        return True

    ranked_results = [r for r in ranked_results if _passes_filters(r)]

    # Semantic reranking, if requested and the model actually loaded at
    # startup — operates on the full filtered candidate pool, before
    # pagination, since its value is surfacing candidates the keyword/
    # citation score under-ranked. Mutates each result's "score" via RRF
    # fusion with the existing ordering; only visibly changes the final
    # order when sort_by=relevance (below) — an explicit citations/year
    # sort always wins over reranking.
    embedding_model = request.app.state.embedding_model
    if rerank and embedding_model is not None:
        ranked_results = await semantic_rerank(embedding_model, topic, ranked_results, abstracts_by_id)
    elif rerank:
        logger.warning("rerank=true requested but the embedding model isn't loaded; skipping.")

    sort_key_map = {
        "relevance": lambda r: r["score"],
        "citations": lambda r: r["citations"],
        "year_desc": lambda r: r["year"],
        "year_asc": lambda r: r["year"],
    }
    key_fn = sort_key_map.get(sort_by, sort_key_map["relevance"])
    ranked_results.sort(key=key_fn, reverse=(sort_by != "year_asc"))

    if needs_over_fetch:
        start = (page - 1) * limit
        page_results = ranked_results[start:start + limit]
    else:
        page_results = ranked_results[:limit]

    journal_set = {r["journal"] for r in page_results}
    total_found = openalex_total if openalex_total is not None else len(ranked_results)

    return {
        "topic": topic,
        "years_filter": f"{start_year}-{end_year}",
        "total_found": total_found,
        "total_journals": len(journal_set),
        "page": page,
        "per_page": limit,
        "results": page_results
    }
