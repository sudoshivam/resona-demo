import math

from config import CITATION_SCORE_CEILING
from schemas import NormalizedPaper
from services.scopus import get_scopus_search_url

RRF_K = 60  # standard IR-literature default
SOURCE_ID_PRIORITY = ("openalex", "semantic_scholar", "crossref", "arxiv")


def normalize(value, max_value):
    if not value or not max_value:
        return 0
    return value / max_value


def get_snippet(text, max_chars=500):
    if not text:
        return ""
    snippet = text[:max_chars]
    last_period = snippet.rfind(".")
    if last_period != -1:
        snippet = snippet[:last_period + 1]
    return snippet.strip()


def source_relevance(rank: int) -> float:
    """Reciprocal-rank score for a single 1-indexed rank position. Shared
    across ranking.py (per-source fusion) and reranking.py (keyword/semantic
    fusion) — the same formula applied one level up."""
    return (RRF_K + 1) / (RRF_K + rank)


def relevance_component(source_signals: dict) -> float:
    """Reciprocal-rank relevance, averaged across whichever sources
    returned this paper. Average (not sum) keeps this bounded in [0, 1]
    regardless of how many sources were queried — a paper found by more
    sources isn't automatically 'more relevant', just more findable."""
    if not source_signals:
        return 0.0
    return sum(source_relevance(s.rank) for s in source_signals.values()) / len(source_signals)


def _primary_id(paper: NormalizedPaper) -> str:
    if paper.doi:
        return paper.doi
    for source in SOURCE_ID_PRIORITY:
        if source in paper.source_ids:
            return paper.source_ids[source]
    return paper.fallback_key or ""


def _merged_citations(source_signals: dict) -> int:
    counts = [s.citations for s in source_signals.values() if s.citations is not None]
    return max(counts) if counts else 0


def _merged_concepts(source_signals: dict, max_concepts=5) -> list:
    seen = set()
    merged = []
    for signal in source_signals.values():
        for c in signal.concepts:
            if c.name not in seen:
                seen.add(c.name)
                merged.append({"name": c.name, "score": c.score})
    merged.sort(key=lambda c: c["score"], reverse=True)
    return merged[:max_concepts]


def _format_authors(authors, max_authors=5):
    selected = authors if max_authors is None else authors[:max_authors]
    formatted = [a.model_dump() for a in selected]
    if max_authors is not None and len(authors) > max_authors:
        formatted.append({"name": f"+{len(authors) - max_authors} more", "id": "", "orcid": ""})
    return formatted


def build_paper_result(paper: NormalizedPaper, start_year, end_year, max_authors=5):
    relevance = relevance_component(paper.source_signals)
    citations = _merged_citations(paper.source_signals)
    year = paper.year or 0

    citation_score = min(math.log1p(citations) / math.log1p(CITATION_SCORE_CEILING), 1.0)
    year_range = max(end_year - start_year, 1)
    recency_score = normalize(year - start_year, year_range) if year else 0

    final_score = (
        relevance * 0.5 +
        citation_score * 0.3 +
        recency_score * 0.2
    )

    snippet = get_snippet(paper.abstract) or "No abstract available."
    authors = _format_authors(paper.authors, max_authors=max_authors)
    concepts = _merged_concepts(paper.source_signals)

    scopus_search_link = get_scopus_search_url(paper.title) if paper.title else None

    return {
        "id": _primary_id(paper),
        "title": paper.title,
        "year": year,
        "authors": authors,
        "journal": paper.journal or "Unknown Journal",
        "publisher": paper.publisher or "Unknown Publisher",
        "citations": citations,
        "open_access": paper.open_access,
        "oa_url": paper.oa_url or "",
        "doi": paper.doi_url or "",
        "abstract": paper.abstract,
        "summary": snippet,
        "concepts": concepts,
        "type": paper.type or "",
        "score": round(final_score, 4),
        "scopus_search_url": scopus_search_link,
    }
