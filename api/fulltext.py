from fastapi import APIRouter, HTTPException, Request

from config import limiter, MAX_FULLTEXT_CHARS, RATE_LIMIT_FULLTEXT
from models import ErrorResponse, FullTextRequest, FullTextResponse
from services.fulltext import get_or_fetch_fulltext

router = APIRouter()


@router.post(
    "/fulltext",
    response_model=FullTextResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Full text is not available"},
        502: {"model": ErrorResponse, "description": "The PDF could not be downloaded or extracted"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(RATE_LIMIT_FULLTEXT)
async def load_fulltext(request: Request, body: FullTextRequest):
    if not body.open_access or not body.oa_url:
        raise HTTPException(status_code=404, detail="Full text not available.")

    key = body.paper_id or body.oa_url
    text = await get_or_fetch_fulltext(
        request.app.state.http_client,
        request.app.state.fulltext_cache,
        key,
        body.oa_url,
    )
    if not text:
        raise HTTPException(status_code=502, detail="Couldn't load full text.")

    return {
        "text": text,
        "characters": len(text),
        "truncated": len(text) >= MAX_FULLTEXT_CHARS,
    }
