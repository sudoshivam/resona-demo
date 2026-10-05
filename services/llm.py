import json
from collections.abc import AsyncGenerator

import httpx

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OPENAI_API_KEY, OPENAI_MODEL, LLM_PROVIDER


async def check_ollama_available(client: httpx.AsyncClient):
    """Check if Ollama is running and the model is available."""
    try:
        resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if resp.status_code == 200:
            models = [m.get("name", "").split(":")[0] for m in resp.json().get("models", [])]
            return OLLAMA_MODEL.split(":")[0] in models
    except Exception:
        pass
    return False


async def get_active_llm_provider(client: httpx.AsyncClient):
    """Determine which LLM provider to use."""
    if LLM_PROVIDER == "openai" and OPENAI_API_KEY:
        return "openai"
    if LLM_PROVIDER == "ollama":
        return "ollama"
    # auto mode: try Ollama first (free), then OpenAI
    if await check_ollama_available(client):
        return "ollama"
    if OPENAI_API_KEY:
        return "openai"
    return None


async def summarize_with_ollama(client: httpx.AsyncClient, prompt: str) -> str:
    """Generate summary using local Ollama model."""
    resp = await client.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 300
            }
        },
        timeout=60  # local models can be slower
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


async def summarize_with_openai(client: httpx.AsyncClient, prompt: str) -> str:
    """Generate summary using OpenAI API."""
    resp = await client.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "temperature": 0.3
        },
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


async def chat_with_ollama(client: httpx.AsyncClient, messages: list) -> str:
    """Multi-turn chat completion using local Ollama model.

    Takes a full message list (system + conversation) rather than a single
    prompt, and allows a larger output budget than summarization.
    """
    resp = await client.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 500
            }
        },
        timeout=60  # local models can be slower
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


async def chat_with_openai(client: httpx.AsyncClient, messages: list) -> str:
    """Multi-turn chat completion using OpenAI API."""
    resp = await client.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": OPENAI_MODEL,
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.3
        },
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


async def stream_chat_with_ollama(
    client: httpx.AsyncClient, messages: list
) -> AsyncGenerator[str, None]:
    """Yield token deltas from Ollama's NDJSON chat stream."""
    async with client.stream(
        "POST",
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": 0.3,
                "num_predict": 500,
            },
        },
        timeout=60,
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            delta = chunk.get("message", {}).get("content", "")
            if delta:
                yield delta


async def stream_chat_with_openai(
    client: httpx.AsyncClient, messages: list
) -> AsyncGenerator[str, None]:
    """Yield token deltas from OpenAI's SSE chat-completions stream."""
    async with client.stream(
        "POST",
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_MODEL,
            "messages": messages,
            "stream": True,
            "max_tokens": 500,
            "temperature": 0.3,
        },
        timeout=30,
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            data = line.removeprefix("data: ").strip()
            if data == "[DONE]":
                break
            if not data:
                continue
            chunk = json.loads(data)
            delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
            if delta:
                yield delta
