import json

import httpx

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from config import limiter, logger, RATE_LIMIT_CHAT, OLLAMA_MODEL, OPENAI_MODEL
from services.llm import (
    get_active_llm_provider,
    stream_chat_with_ollama,
    stream_chat_with_openai,
)
from services.chat import build_grounded_messages
from services.fulltext import get_fulltext_excerpts
from models import ChatRequest

router = APIRouter()


@router.post("/chat", response_class=StreamingResponse)
@limiter.limit(RATE_LIMIT_CHAT)
async def chat(request: Request, body: ChatRequest):
    client = request.app.state.http_client
    provider = await get_active_llm_provider(client)
    if not provider:
        raise HTTPException(
            status_code=503,
            detail="No AI provider available. Install Ollama (free) or set OPENAI_API_KEY in .env"
        )

    history = [m.model_dump() for m in body.messages]

    # Full-text RAG when the paper is OA with a usable PDF and embeddings are
    # available; otherwise (the common case) fall back to the abstract. Any
    # failure inside get_fulltext_excerpts returns None -> abstract path.
    excerpts = None
    embedding_model = request.app.state.embedding_model
    if body.open_access and body.oa_url and embedding_model is not None and history:
        question = history[-1].get("content", "")
        cache_key = body.paper_id or body.oa_url
        excerpts = await get_fulltext_excerpts(
            client, embedding_model, request.app.state.fulltext_cache,
            cache_key, body.oa_url, question,
        )

    grounding = "fulltext" if excerpts else "abstract"
    logger.info(f"Chat grounding: {grounding}")
    messages = build_grounded_messages(body.title, body.abstract, history, excerpts=excerpts)

    if provider == "ollama":
        logger.info(f"Chatting with Ollama ({OLLAMA_MODEL})")
        stream = stream_chat_with_ollama(client, messages)
    else:
        logger.info(f"Chatting with OpenAI ({OPENAI_MODEL})")
        stream = stream_chat_with_openai(client, messages)

    def sse_event(event: dict) -> str:
        return f"data: {json.dumps(event)}\n\n"

    async def event_stream():
        yield sse_event({"type": "meta", "provider": provider, "grounding": grounding})
        try:
            async for delta in stream:
                yield sse_event({"type": "token", "delta": delta})
            yield sse_event({"type": "done"})
        except httpx.TimeoutException:
            logger.error(f"LLM stream timeout ({provider})")
            yield sse_event({
                "type": "error",
                "error": "AI is taking too long to respond. The model might be busy - please try again in a moment.",
            })
        except httpx.HTTPError as error:
            logger.error(f"LLM stream API error ({provider}): {error}")
            message = "AI chat service is temporarily unavailable. "
            if provider == "ollama":
                message += "Make sure Ollama is running on your system."
            else:
                message += "Please check your API key and try again."
            yield sse_event({"type": "error", "error": message})
        except Exception as error:
            logger.error(f"LLM stream failed ({provider}): {type(error).__name__}: {error}")
            yield sse_event({"type": "error", "error": "Chat stream failed. Please try again."})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
