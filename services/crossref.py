import httpx

from schemas import NormalizedPaper, Author, SourceSignal
from services.dedup import normalize_doi, normalize_title_year_key

CROSSREF_BASE = "https://api.crossref.org/works"
CROSSREF_TIMEOUT = 15


async def search(client: httpx.AsyncClient, query: str, limit: int) -> list:
    response = await client.get(
        CROSSREF_BASE, params={"query": query, "rows": limit}, timeout=CROSSREF_TIMEOUT
    )
    response.raise_for_status()
    return response.json().get("message", {}).get("items", [])


def _author_name(a: dict) -> str:
    given = a.get("given", "") or ""
    family = a.get("family", "") or ""
    name = f"{given} {family}".strip()
    return name or (a.get("name") or "")  # organizational authors use "name" directly


def normalize(item: dict, rank: int) -> NormalizedPaper:
    doi_raw = item.get("DOI")
    doi = normalize_doi(doi_raw)
    doi_url = f"https://doi.org/{doi_raw}" if doi_raw else None
    title_list = item.get("title") or []
    title = title_list[0] if title_list else ""
    date_parts = (
        item.get("published")
        or item.get("published-print")
        or item.get("published-online")
        or {}
    ).get("date-parts", [[]])
    year = date_parts[0][0] if date_parts and date_parts[0] else None
    authors = [Author(name=n) for n in (_author_name(a) for a in (item.get("author") or [])) if n]
    container = item.get("container-title") or []
    journal = container[0] if container else None
    citations = item.get("is-referenced-by-count")

    return NormalizedPaper(
        doi=doi,
        source_ids={"crossref": doi_raw} if doi_raw else {},
        fallback_key=None if doi else normalize_title_year_key(title, year),
        title=title,
        year=year,
        authors=authors,
        journal=journal,
        publisher=item.get("publisher"),
        abstract="",  # Crossref rarely provides one; graceful degrade, not scraped/guessed
        doi_url=doi_url,
        open_access=False,  # no reliable direct OA signal in Crossref's response
        oa_url=None,
        type=item.get("type"),
        source_signals={"crossref": SourceSignal(rank=rank, citations=citations, concepts=[])},
    )
