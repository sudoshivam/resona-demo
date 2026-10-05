import httpx

from config import SEMANTIC_SCHOLAR_API_KEY
from schemas import NormalizedPaper, Author, SourceSignal
from services.dedup import normalize_doi, normalize_title_year_key

SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_TIMEOUT = 15
SEMANTIC_SCHOLAR_FIELDS = "title,abstract,year,authors,externalIds,citationCount,openAccessPdf,venue,publicationTypes"


async def search(client: httpx.AsyncClient, query: str, limit: int) -> list:
    headers = {"x-api-key": SEMANTIC_SCHOLAR_API_KEY} if SEMANTIC_SCHOLAR_API_KEY else {}
    response = await client.get(
        SEMANTIC_SCHOLAR_BASE,
        params={"query": query, "limit": limit, "fields": SEMANTIC_SCHOLAR_FIELDS},
        headers=headers,
        timeout=SEMANTIC_SCHOLAR_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("data", [])


def normalize(item: dict, rank: int) -> NormalizedPaper:
    external_ids = item.get("externalIds") or {}
    doi_raw = external_ids.get("DOI")
    doi = normalize_doi(doi_raw)
    doi_url = f"https://doi.org/{doi_raw}" if doi_raw else None
    title = item.get("title") or ""
    year = item.get("year")
    authors = [
        Author(name=a.get("name", ""), id=str(a.get("authorId") or ""))
        for a in (item.get("authors") or [])
        if a.get("name")
    ]
    paper_id = item.get("paperId", "")
    oa_pdf = item.get("openAccessPdf") or {}
    pub_types = item.get("publicationTypes") or []

    return NormalizedPaper(
        doi=doi,
        source_ids={"semantic_scholar": paper_id} if paper_id else {},
        fallback_key=None if doi else normalize_title_year_key(title, year),
        title=title,
        year=year,
        authors=authors,
        journal=item.get("venue") or None,
        publisher=None,
        abstract=item.get("abstract") or "",
        doi_url=doi_url,
        open_access=bool(oa_pdf.get("url")),
        oa_url=oa_pdf.get("url"),
        type=pub_types[0] if pub_types else None,
        source_signals={
            "semantic_scholar": SourceSignal(rank=rank, citations=item.get("citationCount"), concepts=[])
        },
    )
