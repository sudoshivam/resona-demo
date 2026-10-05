def format_bibtex(paper):
    author_str = " and ".join([a["name"] for a in paper.get("authors", []) if a.get("name") and "more" not in a["name"]])
    doi = paper.get("doi", "") or ""
    key = doi.split("/")[-1] if doi else paper.get("title", "unknown")[:20].replace(" ", "_")
    year = paper.get("year", "")
    return (
        f"@article{{{key},\n"
        f"  title = {{{paper.get('title', '')}}},\n"
        f"  author = {{{author_str}}},\n"
        f"  journal = {{{paper.get('journal', '')}}},\n"
        f"  year = {{{year}}},\n"
        f"  doi = {{{doi}}},\n"
        f"  publisher = {{{paper.get('publisher', '')}}}\n"
        f"}}\n"
    )


def format_apa(paper):
    authors = paper.get("authors", [])
    author_names = [a["name"] for a in authors if a.get("name") and "more" not in a["name"]]
    if len(author_names) == 0:
        author_str = "Unknown"
    elif len(author_names) == 1:
        author_str = author_names[0]
    elif len(author_names) == 2:
        author_str = f"{author_names[0]} & {author_names[1]}"
    else:
        author_str = ", ".join(author_names[:-1]) + f", & {author_names[-1]}"
    year = paper.get("year", "n.d.")
    title = paper.get("title", "")
    journal = paper.get("journal", "")
    doi = paper.get("doi", "")
    citation = f"{author_str} ({year}). {title}. *{journal}*."
    if doi:
        citation += f" {doi}"
    return citation
