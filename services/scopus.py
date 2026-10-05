import httpx
from urllib.parse import quote

from config import SCOPUS_API_KEY, SCOPUS_SEARCH_URL, logger


async def check_scopus_doi(client: httpx.AsyncClient, doi: str) -> dict:
    """Check if a paper exists in Scopus by DOI. Returns Scopus ID and link if found."""
    if not SCOPUS_API_KEY or not doi:
        return {"indexed": False, "scopus_url": None, "scopus_id": None}

    clean_doi = doi.replace("https://doi.org/", "")
    try:
        resp = await client.get(
            SCOPUS_SEARCH_URL,
            headers={"X-ELS-APIKey": SCOPUS_API_KEY, "Accept": "application/json"},
            params={"query": f"DOI({clean_doi})", "count": 1},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            total = int(data.get("search-results", {}).get("opensearch:totalResults", 0))
            if total > 0:
                entry = data["search-results"]["entry"][0]
                scopus_id = entry.get("dc:identifier", "").replace("SCOPUS_ID:", "")
                # Build Scopus abstract link
                scopus_link = None
                for link in entry.get("link", []):
                    if link.get("@ref") == "scopus":
                        scopus_link = link.get("@href")
                        break
                return {"indexed": True, "scopus_url": scopus_link, "scopus_id": scopus_id}
    except Exception as e:
        logger.debug(f"Scopus check failed for {doi}: {e}")
    return {"indexed": False, "scopus_url": None, "scopus_id": None}


def get_scopus_search_url(title: str) -> str:
    """Generate a Scopus search URL for a paper title (no API key needed)."""
    return f"https://www.scopus.com/results/results.uri?sort=plf-f&src=s&sot=b&sdt=b&sl=50&s=TITLE%28{quote(title)}%29"
