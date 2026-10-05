import httpx

from fastapi import APIRouter, Query, HTTPException, Request

from config import (
    limiter,
    RATE_LIMIT_SCOPUS,
    RATE_LIMIT_SEARCH,
    SCOPUS_API_KEY,
    APP_ENV,
    OLLAMA_MODEL,
    OPENAI_API_KEY,
)
from services.openalex import get_openalex_params, search_works
from services.scopus import check_scopus_doi
from services.llm import get_active_llm_provider, check_ollama_available
from models import HealthResponse, ScopusCheckResponse

router = APIRouter()


@router.get("/scopus/check", response_model=ScopusCheckResponse)
@limiter.limit(RATE_LIMIT_SCOPUS)
async def scopus_check(request: Request, doi: str = Query(..., description="DOI to check in Scopus")):
    """Check if a paper is indexed in Scopus by its DOI."""
    if not SCOPUS_API_KEY:
        raise HTTPException(status_code=503, detail="Scopus API key not configured. Set SCOPUS_API_KEY in .env")
    result = await check_scopus_doi(request.app.state.http_client, doi)
    return result


@router.get("/trending")
@limiter.limit(RATE_LIMIT_SEARCH)
async def get_trending(
    request: Request,
    field: str = Query("computer-science", description="Field of study"),
):
    try:
        params = {
            **get_openalex_params(),
            "filter": f"concepts.display_name.search:{field}",
            "group_by": "publication_year",
            "per_page": 10,
        }
        data = await search_works(request.app.state.http_client, params)
        return {"field": field, "data": data.get("group_by", [])}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/health", response_model=HealthResponse)
@limiter.limit("60/minute")
async def health_check(request: Request):
    client = request.app.state.http_client
    provider = await get_active_llm_provider(client)
    ollama_ok = await check_ollama_available(client)
    return {
        "status": "healthy",
        "version": "2.0.0",
        "environment": APP_ENV,
        "ai_enabled": provider is not None,
        "ai_provider": provider or "none",
        "ollama_available": ollama_ok,
        "ollama_model": OLLAMA_MODEL if ollama_ok else None,
        "openai_configured": bool(OPENAI_API_KEY),
        "scopus_enabled": bool(SCOPUS_API_KEY),
        "data_source": "OpenAlex (260M+ scholarly works)"
    }
