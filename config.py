import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address

load_dotenv(Path(__file__).parent / ".env", override=True)

# ---------------------------
# Environment
# ---------------------------

APP_ENV = os.getenv("APP_ENV", "development")  # "development" or "production"
IS_PROD = APP_ENV == "production"
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")  # Optional: protect write endpoints
RATE_LIMIT_SEARCH = os.getenv("RATE_LIMIT_SEARCH", "30/minute")
RATE_LIMIT_PAPER = os.getenv("RATE_LIMIT_PAPER", "30/minute")
RATE_LIMIT_SUMMARIZE = os.getenv("RATE_LIMIT_SUMMARIZE", "10/minute")
RATE_LIMIT_CHAT = os.getenv("RATE_LIMIT_CHAT", "10/minute")
RATE_LIMIT_EXPORT = os.getenv("RATE_LIMIT_EXPORT", "5/minute")
RATE_LIMIT_EXPORT_PAPER = os.getenv("RATE_LIMIT_EXPORT_PAPER", "10/minute")
RATE_LIMIT_FULLTEXT = os.getenv("RATE_LIMIT_FULLTEXT", "10/minute")
RATE_LIMIT_SCOPUS = os.getenv("RATE_LIMIT_SCOPUS", "20/minute")

log_level = logging.WARNING if IS_PROD else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("main")
logger.setLevel(logging.INFO)  # Always log INFO for our app

logger.info(f"Starting Resona API — env={APP_ENV}")

# ---------------------------
# Rate Limiter
# ---------------------------

limiter = Limiter(key_func=get_remote_address)

# ---------------------------
# CORS
# ---------------------------

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# ---------------------------
# Config
# ---------------------------

OPENALEX_BASE = "https://api.openalex.org"
WORKS_URL = f"{OPENALEX_BASE}/works"
AUTOCOMPLETE_URL = f"{OPENALEX_BASE}/autocomplete/works"
REQUEST_TIMEOUT = 15
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "")
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY", "")
CITATION_SCORE_CEILING = 10_000

# LLM Config — Ollama (free, local) is preferred; OpenAI is optional fallback
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")  # "ollama", "openai", or "auto"

# Scopus API (optional, free key from dev.elsevier.com)
SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY", "")
SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"

# Semantic Scholar API (optional, free key raises the unauthenticated rate limit)
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

# Federation
FEDERATION_SOURCES = ["openalex", "crossref", "semantic_scholar", "arxiv"]
FEDERATION_OVER_FETCH_MULTIPLIER = 3
FEDERATION_OVER_FETCH_CAP = 100

# Semantic reranking — pinned for reproducibility, independent of Ollama
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# Chat full-text RAG (increment 2) — fetch/extract/chunk/embed an OA paper's PDF,
# retrieve the most relevant chunks per question. Falls back to the abstract when
# any of this is unavailable.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))          # chars per chunk
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))     # chars overlapped between chunks
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))               # chunks retrieved per question
FULLTEXT_CACHE_SIZE = int(os.getenv("FULLTEXT_CACHE_SIZE", "16"))  # papers kept in the LRU
MAX_FULLTEXT_CHARS = int(os.getenv("MAX_FULLTEXT_CHARS", "200000"))  # cap extracted text
MAX_FULLTEXT_BYTES = int(os.getenv("MAX_FULLTEXT_BYTES", str(15 * 1024 * 1024)))  # cap PDF download
FULLTEXT_TIMEOUT = int(os.getenv("FULLTEXT_TIMEOUT", "20"))  # seconds for the PDF fetch
