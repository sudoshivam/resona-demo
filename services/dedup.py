import re
from typing import List, Optional

from rapidfuzz import fuzz

from schemas import NormalizedPaper

FUZZY_TITLE_THRESHOLD = 92
SOURCE_PRIORITY = ["openalex", "semantic_scholar", "crossref", "arxiv"]


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    cleaned = doi.strip().lower()
    cleaned = re.sub(r"^https?://(dx\.)?doi\.org/", "", cleaned)
    return cleaned or None


def _normalize_title(title: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    return re.sub(r"\s+", " ", cleaned)


def normalize_title_year_key(title: str, year: Optional[int]) -> str:
    return f"{_normalize_title(title)}|{year or ''}"


def _years_close(a: Optional[int], b: Optional[int]) -> bool:
    if a is None or b is None:
        return True
    return abs(a - b) <= 1


def _merge_field(existing, incoming):
    """First non-empty value wins, preferring whichever was already there
    (callers merge in SOURCE_PRIORITY order, so 'existing' is always the
    higher-priority source once merging starts)."""
    if existing:
        return existing
    return incoming


def _merge_two(a: NormalizedPaper, b: NormalizedPaper) -> NormalizedPaper:
    """Merge b into a. a is assumed higher-priority (processed earlier in
    SOURCE_PRIORITY order) for field-conflict resolution."""
    merged_source_ids = {**b.source_ids, **a.source_ids}
    merged_source_signals = {**b.source_signals, **a.source_signals}
    return NormalizedPaper(
        doi=a.doi or b.doi,
        source_ids=merged_source_ids,
        fallback_key=a.fallback_key or b.fallback_key,
        title=_merge_field(a.title, b.title),
        year=a.year if a.year is not None else b.year,
        authors=a.authors or b.authors,
        journal=_merge_field(a.journal, b.journal),
        publisher=_merge_field(a.publisher, b.publisher),
        abstract=_merge_field(a.abstract, b.abstract),
        doi_url=_merge_field(a.doi_url, b.doi_url),
        open_access=a.open_access or b.open_access,
        oa_url=_merge_field(a.oa_url, b.oa_url),
        type=_merge_field(a.type, b.type),
        source_signals=merged_source_signals,
    )


def merge_candidates(papers: List[NormalizedPaper]) -> List[NormalizedPaper]:
    """Dedup + merge a flat list of NormalizedPaper (already normalized,
    not yet grouped) from potentially multiple sources. DOI match first;
    fuzzy title+year fallback for DOI-less records."""

    def source_rank(p: NormalizedPaper) -> int:
        for src in p.source_ids:
            if src in SOURCE_PRIORITY:
                return SOURCE_PRIORITY.index(src)
        return len(SOURCE_PRIORITY)

    ordered = sorted(papers, key=source_rank)

    by_doi: dict[str, NormalizedPaper] = {}
    doi_less: List[NormalizedPaper] = []

    for p in ordered:
        if p.doi:
            if p.doi in by_doi:
                by_doi[p.doi] = _merge_two(by_doi[p.doi], p)
            else:
                by_doi[p.doi] = p
        else:
            doi_less.append(p)

    merged: List[NormalizedPaper] = list(by_doi.values())

    for candidate in doi_less:
        match_idx = None
        for i, existing in enumerate(merged):
            if not _years_close(candidate.year, existing.year):
                continue
            score = fuzz.token_sort_ratio(_normalize_title(candidate.title), _normalize_title(existing.title))
            if score >= FUZZY_TITLE_THRESHOLD:
                match_idx = i
                break
        if match_idx is not None:
            merged[match_idx] = _merge_two(merged[match_idx], candidate)
        else:
            merged.append(candidate)

    return merged
