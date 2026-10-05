from typing import Dict, List, Optional
from pydantic import BaseModel


class Author(BaseModel):
    name: str
    id: str = ""
    orcid: str = ""


class Concept(BaseModel):
    name: str
    score: float


class SourceSignal(BaseModel):
    rank: int  # 1-indexed position within that source's own results
    citations: Optional[int] = None
    concepts: List[Concept] = []


class NormalizedPaper(BaseModel):
    # Identity
    doi: Optional[str] = None  # normalized: lowercase, no doi.org prefix
    source_ids: Dict[str, str] = {}  # {"openalex": "W123...", "arxiv": "2301.x", ...}
    fallback_key: Optional[str] = None  # normalized title+year, set only when doi is None

    # Content — source-agnostic, already fully reconstructed
    title: str
    year: Optional[int] = None
    authors: List[Author] = []
    journal: Optional[str] = None
    publisher: Optional[str] = None
    abstract: str = ""
    doi_url: Optional[str] = None
    open_access: bool = False
    oa_url: Optional[str] = None
    type: Optional[str] = None

    # Per-source signals — kept separate, never blended into one raw number before fusion
    source_signals: Dict[str, SourceSignal] = {}
