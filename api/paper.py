from datetime import datetime

import httpx

from fastapi import APIRouter, HTTPException, Request

from config import limiter, logger, RATE_LIMIT_PAPER
from services.openalex import get_work, normalize_openalex
from services.paper_lookup import classify_paper_id
from ranking import build_paper_result
from models import Paper

router = APIRouter()

UNRESOLVABLE_DETAIL = (
    "This paper isn't indexed under an OpenAlex ID or DOI, so it can't be looked "
    "up individually. It may only be available through Crossref/Semantic "
    "Scholar/arXiv federation, which this endpoint doesn't support yet."
)


@router.get("/paper/{paper_id:path}", response_model=Paper)
@limiter.limit(RATE_LIMIT_PAPER)
async def get_paper(request: Request, paper_id: str):
    client = request.app.state.http_client

    kind, value = classify_paper_id(paper_id)
    if kind == "unresolvable":
        raise HTTPException(status_code=404, detail=UNRESOLVABLE_DETAIL)

    path_segment = value if kind == "openalex" else f"doi:{value}"

    try:
        item = await get_work(client, path_segment)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Paper not found in OpenAlex.")
        logger.error(f"OpenAlex API error: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch from OpenAlex: {str(e)}")
    except httpx.HTTPError as e:
        logger.error(f"OpenAlex API error: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch from OpenAlex: {str(e)}")

    normalized = normalize_openalex(item, rank=1)
    current_year = datetime.now().year
    return build_paper_result(normalized, current_year - 5, current_year, max_authors=None)
