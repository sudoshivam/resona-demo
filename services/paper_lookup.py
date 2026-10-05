"""Pure ID-classification logic for GET /paper/{id}.

Post-federation, a Paper's `id` (built by ranking._primary_id) is not always an
OpenAlex work ID: it's the DOI when one exists, an OpenAlex work ID when there's
no DOI but the paper was found via OpenAlex, a non-OpenAlex source id (Semantic
Scholar hash, arXiv id) when there's no DOI and no OpenAlex match, or a synthetic
"normalized title|year" fallback key as a last resort. This endpoint only knows
how to resolve the first two kinds via OpenAlex; everything else is reported as
unresolvable so the route can return a clean 404 instead of guessing.
"""

import re
from typing import Tuple

from services.dedup import normalize_doi

_OPENALEX_ID_RE = re.compile(r"^(?:https?://openalex\.org/)?(W\d+)$", re.IGNORECASE)
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")


def classify_paper_id(raw_id: str) -> Tuple[str, str]:
    """Classify a Paper.id string.

    Returns (kind, value):
    - ("openalex", "W123...")  — bare OpenAlex work id, ready for /works/{id}
    - ("doi", "10.xxxx/yyyy")  — normalized bare DOI, ready for /works/doi:{doi}
    - ("unresolvable", raw_id) — a fallback key, a non-OpenAlex source id, or empty
    """
    if not raw_id:
        return ("unresolvable", raw_id or "")

    candidate = raw_id.strip()

    m = _OPENALEX_ID_RE.match(candidate)
    if m:
        return ("openalex", m.group(1).upper())

    doi_candidate = normalize_doi(candidate)
    if doi_candidate and _DOI_RE.match(doi_candidate):
        return ("doi", doi_candidate)

    return ("unresolvable", candidate)
