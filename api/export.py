import httpx
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from config import limiter, RATE_LIMIT_EXPORT, RATE_LIMIT_EXPORT_PAPER
from models import ErrorResponse, SinglePaperExportRequest
from services.openalex import get_openalex_params, search_works, normalize_openalex
from services.export import papers_to_excel

router = APIRouter()
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_EXCEL_CELL_CHARS = 32_767


@router.get("/export")
@limiter.limit(RATE_LIMIT_EXPORT)
async def export_to_excel(
    request: Request,
    topic: str = Query(...),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    open_access_only: bool = Query(False),
    min_citations: int = Query(0),
):
    client = request.app.state.http_client
    current_year = datetime.now().year
    if not start_year:
        start_year = current_year - 5
    if not end_year:
        end_year = current_year

    filters = [
        f"from_publication_date:{start_year}-01-01",
        f"to_publication_date:{end_year}-12-31",
    ]
    if open_access_only:
        filters.append("open_access.is_oa:true")
    if min_citations > 0:
        filters.append(f"cited_by_count:>{min_citations}")

    params = {
        **get_openalex_params(),
        "search": topic,
        "filter": ",".join(filters),
        "per_page": 50,
    }

    try:
        data = await search_works(client, params)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch data: {str(e)}")

    items = data.get("results", [])
    rows = []

    for rank, item in enumerate(items, start=1):
        paper = normalize_openalex(item, rank)
        author_str = "; ".join(a.name for a in paper.authors[:5])

        rows.append({
            "Title": paper.title,
            "Authors": author_str,
            "Year": paper.year,
            "Journal": paper.journal,
            "Publisher": paper.publisher,
            "Citations": paper.source_signals["openalex"].citations,
            "Open Access": paper.open_access,
            "DOI": paper.doi_url,
            "Type": paper.type or "",
            "Abstract": paper.abstract[:500] if paper.abstract else "",
        })

    output = papers_to_excel(rows)

    safe_topic = topic.replace(" ", "_")[:30]
    filename = f"research_{safe_topic}_{start_year}_{end_year}.xlsx"

    return StreamingResponse(
        output,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post(
    "/export/paper",
    response_class=Response,
    responses={
        200: {"content": {XLSX_MEDIA_TYPE: {}}, "description": "Single-paper Excel workbook"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(RATE_LIMIT_EXPORT_PAPER)
def export_single_paper(request: Request, body: SinglePaperExportRequest):
    paper = body.paper
    author_str = "; ".join(author.name for author in paper.authors)
    rows = [{
        "Title": paper.title,
        "Authors": author_str,
        "Year": paper.year,
        "Journal": paper.journal,
        "Publisher": paper.publisher,
        "Citations": paper.citations,
        "Open Access": paper.open_access,
        "DOI": paper.doi,
        "Type": paper.type,
        "Abstract": paper.abstract[:MAX_EXCEL_CELL_CHARS],
    }]
    output = papers_to_excel(rows)

    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", paper.title).strip("_")[:50] or "paper"
    return StreamingResponse(
        output,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.xlsx"'},
    )
