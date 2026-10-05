from typing import Dict, List, Optional

from ranking import source_relevance
from services.embeddings import embed_texts, cosine_similarity


def _rrf_fuse_ranks(keyword_rank: int, semantic_rank: Optional[int]) -> float:
    if semantic_rank is not None:
        return round((source_relevance(keyword_rank) + source_relevance(semantic_rank)) / 2, 4)
    return round(source_relevance(keyword_rank), 4)


def fuse_semantic_scores(ranked_results: List[dict], similarities: Dict[str, float]) -> List[dict]:
    """Pure fusion step. `similarities` holds {id: cosine similarity} only
    for candidates that had a non-empty abstract to embed — a candidate
    absent from it degrades gracefully, fused from its keyword rank alone
    rather than being penalized or dropped."""
    keyword_order = sorted(ranked_results, key=lambda r: r["score"], reverse=True)
    keyword_rank = {r["id"]: i + 1 for i, r in enumerate(keyword_order)}

    semantic_order = sorted(similarities.items(), key=lambda kv: kv[1], reverse=True)
    semantic_rank = {pid: i + 1 for i, (pid, _) in enumerate(semantic_order)}

    for r in ranked_results:
        r["score"] = _rrf_fuse_ranks(keyword_rank[r["id"]], semantic_rank.get(r["id"]))

    return ranked_results


async def semantic_rerank(model, query: str, ranked_results: List[dict], abstracts_by_id: Dict[str, str]) -> List[dict]:
    """Orchestration: embed the query plus every candidate abstract in one
    batched call, compute similarities, fuse. Not unit-tested directly —
    fuse_semantic_scores above carries the actual testable logic, same
    reasoning as not respx-testing the raw embedding HTTP-shaped call."""
    with_abstract = [
        (r["id"], abstracts_by_id.get(r["id"], ""))
        for r in ranked_results
        if abstracts_by_id.get(r["id"], "")
    ]
    if not with_abstract:
        return ranked_results

    texts = [query] + [text for _, text in with_abstract]
    embeddings = await embed_texts(model, texts)
    query_embedding, *abstract_embeddings = embeddings

    similarities = {
        pid: cosine_similarity(query_embedding, emb)
        for (pid, _), emb in zip(with_abstract, abstract_embeddings)
    }

    return fuse_semantic_scores(ranked_results, similarities)
