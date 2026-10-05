import asyncio
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from config import IS_PROD, CORS_ORIGINS, EMBEDDING_MODEL, FULLTEXT_CACHE_SIZE, limiter, logger
from services import embeddings
from services.fulltext import LRUCache
from api import search as search_router
from api import paper as paper_router
from api import summarize as summarize_router
from api import chat as chat_router
from api import citations as citations_router
from api import export as export_router
from api import fulltext as fulltext_router
from api import misc as misc_router

# ---------------------------
# App Setup
# ---------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient()
    app.state.fulltext_cache = LRUCache(FULLTEXT_CACHE_SIZE)

    try:
        app.state.embedding_model = await asyncio.to_thread(embeddings.load_model, EMBEDDING_MODEL)
        logger.info(f"Embedding model loaded: {EMBEDDING_MODEL}")
    except Exception as e:
        app.state.embedding_model = None
        logger.warning(
            f"Embedding model failed to load ({type(e).__name__}: {e}). "
            f"Semantic reranking (/search?rerank=true) will be unavailable until this is "
            f"resolved — first run needs network access to download model weights."
        )

    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="Resona - Academic Research Search",
    description="AI-enhanced academic research paper discovery with hybrid ranking, "
                "powered by OpenAlex (260M+ scholarly works). "
                "Features: AI summaries, advanced filtering, citation export.",
    version="2.0.0",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter

# Rate limit exceeded handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please slow down.", "retry_after": str(exc.detail)}
    )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {type(exc).__name__}: {exc}", exc_info=not IS_PROD)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error" if IS_PROD else str(exc)}
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    max_age=3600,
)

# Security headers + request logging middleware
@app.middleware("http")
async def security_and_logging_middleware(request: Request, call_next):
    start = time.time()
    response: Response = await call_next(request)
    duration = round((time.time() - start) * 1000, 1)

    # Log request (skip health checks in production to reduce noise)
    if not (IS_PROD and request.url.path == "/health"):
        logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)")

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if IS_PROD:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response

# ---------------------------
# Routers
# ---------------------------

app.include_router(search_router.router)
app.include_router(paper_router.router)
app.include_router(summarize_router.router)
app.include_router(chat_router.router)
app.include_router(citations_router.router)
app.include_router(export_router.router)
app.include_router(fulltext_router.router)
app.include_router(misc_router.router)


# ---------------------------
# Run Directly
# ---------------------------

if __name__ == "__main__":
    import os
    import uvicorn
    host = "0.0.0.0" if IS_PROD else "127.0.0.1"
    port = int(os.getenv("PORT", "9999"))
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=not IS_PROD,
        access_log=not IS_PROD,
        workers=1,  # Ollama needs sequential access
    )
