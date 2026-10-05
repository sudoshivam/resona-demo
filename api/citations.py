from fastapi import APIRouter, HTTPException, Request

from config import limiter, RATE_LIMIT_SEARCH, RATE_LIMIT_EXPORT
from citations import format_bibtex, format_apa
from models import CiteRequest, CiteBatchRequest, CiteResponse, CiteBatchResponse

router = APIRouter()


@router.post("/cite", response_model=CiteResponse)
@limiter.limit(RATE_LIMIT_SEARCH)
def generate_citation(request: Request, body: CiteRequest):
    format_type = body.format
    paper = body.paper

    if not paper:
        raise HTTPException(status_code=400, detail="No paper data provided")

    if format_type == "bibtex":
        return {"citation": format_bibtex(paper)}
    elif format_type == "apa":
        return {"citation": format_apa(paper)}
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format_type}")


@router.post("/cite/batch", response_model=CiteBatchResponse)
@limiter.limit(RATE_LIMIT_EXPORT)
def batch_citations(request: Request, body: CiteBatchRequest):
    papers = body.papers
    format_type = body.format

    if not papers:
        raise HTTPException(status_code=400, detail="No papers provided")

    citations = []
    for paper in papers:
        if format_type == "bibtex":
            citations.append(format_bibtex(paper))
        elif format_type == "apa":
            citations.append(format_apa(paper))

    return {"citations": "\n".join(citations)}
