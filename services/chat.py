"""Chat grounding logic for the paper-discussion chatbot.

Pure, dependency-free prompt construction: given a paper's title, its grounding
context (abstract, or full-text excerpts retrieved via RAG), and the conversation
so far, assemble the message list sent to the LLM with a grounding system prompt
prepended. The route and LLM layer are unaffected by which context is used.
"""

from typing import Dict, List, Optional

SYSTEM_PROMPT = (
    "You are a research assistant helping a user understand a single academic paper.\n"
    "You have ONLY the paper's title and abstract below — not its full text.\n\n"
    "Title: {title}\n\n"
    "Abstract: {abstract}\n\n"
    "Rules:\n"
    "- Answer strictly and only using information in the title and abstract above.\n"
    "- If the abstract does not contain enough information to answer, say so plainly "
    '(e.g. "The abstract doesn\'t cover that.") and do NOT answer from outside '
    "knowledge or guess.\n"
    "- Do not invent findings, numbers, methods, authors, or citations that are not "
    "in the abstract.\n"
    "- You may summarize, rephrase, or explain what the abstract says in simpler terms.\n"
    "- Keep answers concise and grounded. It is better to admit a limit than to speculate."
)

FULLTEXT_SYSTEM_PROMPT = (
    "You are a research assistant helping a user understand a single academic paper.\n"
    "Below are the paper's title and the most relevant excerpts retrieved from its "
    "full text. You do NOT have the complete paper — only these excerpts.\n\n"
    "Title: {title}\n\n"
    "Relevant excerpts:\n{excerpts}\n\n"
    "Rules:\n"
    "- Answer strictly and only using information in the excerpts above.\n"
    "- If the excerpts do not contain enough information to answer, say so plainly "
    '(e.g. "The available excerpts don\'t cover that.") and do NOT answer from '
    "outside knowledge or guess.\n"
    "- Do not invent findings, numbers, methods, authors, or citations that are not "
    "in the excerpts.\n"
    "- You may summarize, rephrase, or explain what the excerpts say in simpler terms.\n"
    "- Keep answers concise and grounded. It is better to admit a limit than to speculate."
)


def _format_excerpts(excerpts: List[str]) -> str:
    return "\n\n".join(f"[Excerpt {i}]\n{text}" for i, text in enumerate(excerpts, 1))


def build_grounded_messages(
    title: str,
    abstract: str,
    history: List[Dict[str, str]],
    excerpts: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    """Return the LLM message list: a grounding system message followed by the
    conversation history unchanged (newest user turn last).

    When `excerpts` are provided (full-text RAG succeeded), the system message
    grounds answers on those excerpts; otherwise it grounds on the abstract. Both
    carry the same strict no-hallucination rules so the model declines rather than
    answering from outside knowledge.
    """
    if excerpts:
        content = FULLTEXT_SYSTEM_PROMPT.format(
            title=title or "(untitled)",
            excerpts=_format_excerpts(excerpts),
        )
    else:
        content = SYSTEM_PROMPT.format(
            title=title or "(untitled)",
            abstract=abstract or "(no abstract provided)",
        )
    return [{"role": "system", "content": content}, *history]
