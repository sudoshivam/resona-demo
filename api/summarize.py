import httpx

from fastapi import APIRouter, HTTPException, Request

from config import limiter, logger, RATE_LIMIT_SUMMARIZE, OLLAMA_MODEL, OPENAI_MODEL
from services.llm import get_active_llm_provider, summarize_with_ollama, summarize_with_openai
from models import SummarizeRequest, SummarizeResponse

router = APIRouter()


@router.post("/summarize", response_model=SummarizeResponse)
@limiter.limit(RATE_LIMIT_SUMMARIZE)
async def summarize_paper(request: Request, body: SummarizeRequest):
    client = request.app.state.http_client
    provider = await get_active_llm_provider(client)
    if not provider:
        raise HTTPException(
            status_code=503,
            detail="No AI provider available. Install Ollama (free) or set OPENAI_API_KEY in .env"
        )

    title = body.title
    abstract = body.abstract

    if not abstract or abstract == "No abstract available.":
        raise HTTPException(
            status_code=400,
            detail="This paper doesn't have an abstract available, so we can't generate a summary. Try another paper!"
        )

    prompt = (
        "You are a research assistant. Summarize this academic paper in 3-4 clear sentences. "
        "Focus on: (1) the research objective, (2) the methodology, (3) key findings. "
        "Use simple language accessible to graduate students.\n\n"
        f"Title: {title}\n\nAbstract: {abstract}"
    )

    try:
        if provider == "ollama":
            logger.info(f"Summarizing with Ollama ({OLLAMA_MODEL})")
            summary = await summarize_with_ollama(client, prompt)
        else:
            logger.info(f"Summarizing with OpenAI ({OPENAI_MODEL})")
            summary = await summarize_with_openai(client, prompt)
        return {"summary": summary, "provider": provider}
    except httpx.TimeoutException:
        logger.error(f"LLM timeout ({provider})")
        raise HTTPException(
            status_code=504,
            detail="AI is taking too long to respond. The model might be busy - please try again in a moment."
        )
    except httpx.HTTPError as e:
        logger.error(f"LLM API error ({provider}): {e}")
        error_msg = "AI summary service is temporarily unavailable. "
        if provider == "ollama":
            error_msg += "Make sure Ollama is running on your system."
        else:
            error_msg += "Please check your API key and try again."
        raise HTTPException(status_code=502, detail=error_msg)
