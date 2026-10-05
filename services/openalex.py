import httpx

from config import (
    OPENALEX_API_KEY,
    OPENALEX_BASE,
    OPENALEX_EMAIL,
    REQUEST_TIMEOUT,
    WORKS_URL,
)
from schemas import NormalizedPaper, Author, Concept, SourceSignal
from services.dedup import normalize_doi, normalize_title_year_key


def get_openalex_params():
    params = {}
    if OPENALEX_EMAIL:
        params["mailto"] = OPENALEX_EMAIL
    return params


def get_openalex_headers():
    if not OPENALEX_API_KEY:
        return {}
    return {"Authorization": f"Bearer {OPENALEX_API_KEY}"}


async def search_works(client: httpx.AsyncClient, params: dict) -> dict:
    response = await client.get(
        WORKS_URL,
        params={**params, **get_openalex_params()},
        headers=get_openalex_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


async def get_work(client: httpx.AsyncClient, path_segment: str) -> dict:
    """Fetch a single work. `path_segment` is either a bare OpenAlex id
    ("W123...") or "doi:10.xxxx/yyyy" — OpenAlex's single-work endpoint
    supports both forms natively."""
    response = await client.get(
        f"{WORKS_URL}/{path_segment}",
        params=get_openalex_params(),
        headers=get_openalex_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


async def search_authors(client: httpx.AsyncClient, author: str) -> list:
    resp = await client.get(
        f"{OPENALEX_BASE}/autocomplete/authors",
        params={**get_openalex_params(), "q": author},
        headers=get_openalex_headers(),
        timeout=REQUEST_TIMEOUT
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def reconstruct_abstract(inv_index):
    if not inv_index:
        return ""
    word_positions = []
    for word, positions in inv_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join([w[1] for w in word_positions])


def safe_journal_info(item):
    primary_location = item.get("primary_location") or {}
    source = primary_location.get("source") or {}
    journal_name = source.get("display_name") or "Unknown Journal"
    publisher_name = source.get("host_organization_name") or "Unknown Publisher"
    return journal_name, publisher_name


def extract_authors(item, max_authors=5):
    authorships = item.get("authorships") or []
    authors = []
    for a in authorships[:max_authors]:
        author = a.get("author") or {}
        name = author.get("display_name")
        if name:
            authors.append({
                "name": name,
                "id": author.get("id", ""),
                "orcid": author.get("orcid", "")
            })
    if len(authorships) > max_authors:
        authors.append({"name": f"+{len(authorships) - max_authors} more", "id": "", "orcid": ""})
    return authors


def extract_all_authors(item):
    """Like extract_authors but without the max_authors truncation/'+N more'
    placeholder — used when building a NormalizedPaper, since truncation now
    happens exactly once, uniformly across all sources, after merging.

    Uses `or ""` (not `.get(key, "")`) for id/orcid: real OpenAlex records
    sometimes have these keys present but explicitly null, which `.get`'s
    default doesn't catch and which the strict `Author` model rejects."""
    authorships = item.get("authorships") or []
    authors = []
    for a in authorships:
        author = a.get("author") or {}
        name = author.get("display_name")
        if name:
            authors.append({
                "name": name,
                "id": author.get("id") or "",
                "orcid": author.get("orcid") or "",
            })
    return authors


def extract_concepts(item, max_concepts=5):
    concepts = item.get("concepts") or []
    return [
        {"name": c.get("display_name", ""), "score": round(c.get("score", 0), 2)}
        for c in concepts[:max_concepts]
        if c.get("score", 0) > 0.3
    ]


def normalize_openalex(item: dict, rank: int) -> NormalizedPaper:
    openalex_id = item.get("id", "")
    doi_url = item.get("doi") or None
    doi = normalize_doi(doi_url)
    title = item.get("title") or ""
    year = item.get("publication_year") or None
    journal_name, publisher_name = safe_journal_info(item)
    authors = [Author(**a) for a in extract_all_authors(item)]
    abstract = reconstruct_abstract(item.get("abstract_inverted_index"))
    concepts = [Concept(**c) for c in extract_concepts(item)]
    citations = item.get("cited_by_count", 0)
    open_access = item.get("open_access") or {}

    return NormalizedPaper(
        doi=doi,
        source_ids={"openalex": openalex_id} if openalex_id else {},
        fallback_key=None if doi else normalize_title_year_key(title, year),
        title=title,
        year=year,
        authors=authors,
        journal=journal_name,
        publisher=publisher_name,
        abstract=abstract,
        doi_url=doi_url,
        open_access=open_access.get("is_oa", False),
        oa_url=open_access.get("oa_url") or None,
        type=item.get("type") or None,
        source_signals={"openalex": SourceSignal(rank=rank, citations=citations, concepts=concepts)},
    )
