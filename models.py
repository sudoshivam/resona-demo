from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from schemas import Author, Concept


class SummarizeRequest(BaseModel):
    title: str = ""
    abstract: str = ""


class CiteRequest(BaseModel):
    format: str = "bibtex"
    paper: Dict[str, Any] = {}


class CiteBatchRequest(BaseModel):
    format: str = "bibtex"
    papers: List[Dict[str, Any]] = []


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    ai_enabled: bool
    ai_provider: str
    ollama_available: bool
    ollama_model: Optional[str] = None
    openai_configured: bool
    scopus_enabled: bool
    data_source: str


class SummarizeResponse(BaseModel):
    summary: str
    provider: str


class ChatMessage(BaseModel):
    role: str = "user"
    content: str = ""


class ChatRequest(BaseModel):
    title: str = ""
    abstract: str = ""
    messages: List[ChatMessage] = []
    # Full-text RAG (increment 2) — optional; frontend supplies these from the
    # Paper it already holds so the backend can fetch the OA PDF. All default so
    # the abstract-only path (increment 1) stays valid without them.
    open_access: bool = False
    oa_url: str = ""
    paper_id: str = ""


class ChatResponse(BaseModel):
    reply: str
    provider: str
    grounding: str = "abstract"  # "fulltext" | "abstract" — which context grounded the answer


class CiteResponse(BaseModel):
    citation: str


class CiteBatchResponse(BaseModel):
    citations: str


class ScopusCheckResponse(BaseModel):
    indexed: bool
    scopus_url: Optional[str] = None
    scopus_id: Optional[str] = None


class Paper(BaseModel):
    """Matches ranking.build_paper_result's dict shape field-for-field — the
    same shape returned per result by /search — so GET /paper/{id} returns a
    typed, identical result the frontend can render with the same component."""
    id: str
    title: str
    year: int
    authors: List[Author]
    journal: str
    publisher: str
    citations: int
    open_access: bool
    oa_url: str
    doi: str
    abstract: str
    summary: str
    concepts: List[Concept]
    type: str
    score: float
    scopus_search_url: Optional[str] = None


class SinglePaperExportRequest(BaseModel):
    paper: Paper


class FullTextRequest(BaseModel):
    open_access: bool = False
    oa_url: str = ""
    paper_id: str = ""


class FullTextResponse(BaseModel):
    text: str
    characters: int
    truncated: bool


class ErrorResponse(BaseModel):
    detail: str
    retry_after: Optional[str] = None
