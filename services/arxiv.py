import xml.etree.ElementTree as ET

import httpx

from schemas import NormalizedPaper, Author, SourceSignal
from services.dedup import normalize_doi, normalize_title_year_key

ARXIV_BASE = "https://export.arxiv.org/api/query"
ARXIV_TIMEOUT = 15
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


async def search(client: httpx.AsyncClient, query: str, limit: int) -> list:
    response = await client.get(
        ARXIV_BASE,
        params={"search_query": f"all:{query}", "start": 0, "max_results": limit},
        timeout=ARXIV_TIMEOUT,
    )
    response.raise_for_status()
    root = ET.fromstring(response.text)
    return [_entry_to_dict(entry) for entry in root.findall(f"{ATOM_NS}entry")]


def _entry_to_dict(entry: ET.Element) -> dict:
    def text(tag, ns=ATOM_NS):
        el = entry.find(f"{ns}{tag}")
        return el.text.strip() if el is not None and el.text else None

    authors = [
        (a.findtext(f"{ATOM_NS}name", default="") or "").strip()
        for a in entry.findall(f"{ATOM_NS}author")
    ]
    abs_url = None
    for link in entry.findall(f"{ATOM_NS}link"):
        if link.get("rel") == "alternate":
            abs_url = link.get("href")
            break

    return {
        "id": text("id"),
        "title": text("title"),
        "summary": text("summary"),
        "published": text("published"),
        "authors": [a for a in authors if a],
        "doi": text("doi", ns=ARXIV_NS),
        "abs_url": abs_url,
    }


def normalize(item: dict, rank: int) -> NormalizedPaper:
    arxiv_id_url = item.get("id") or ""
    arxiv_id = arxiv_id_url.rstrip("/").split("/")[-1] if arxiv_id_url else ""
    doi_raw = item.get("doi")
    doi = normalize_doi(doi_raw)
    doi_url = f"https://doi.org/{doi_raw}" if doi_raw else None
    title = (item.get("title") or "").replace("\n", " ").strip()
    published = item.get("published") or ""
    year = int(published[:4]) if published[:4].isdigit() else None
    authors = [Author(name=name) for name in item.get("authors", [])]
    abstract = (item.get("summary") or "").replace("\n", " ").strip()

    return NormalizedPaper(
        doi=doi,
        source_ids={"arxiv": arxiv_id} if arxiv_id else {},
        fallback_key=None if doi else normalize_title_year_key(title, year),
        title=title,
        year=year,
        authors=authors,
        journal=None,
        publisher=None,
        abstract=abstract,
        doi_url=doi_url,
        open_access=True,  # every arXiv preprint is open access by construction
        oa_url=item.get("abs_url"),
        type="preprint",
        source_signals={"arxiv": SourceSignal(rank=rank, citations=None, concepts=[])},
    )
