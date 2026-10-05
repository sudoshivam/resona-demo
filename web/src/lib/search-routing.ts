import type { SearchParams } from "./types";

export function searchResultsHref(params: SearchParams, page = 1): string {
  const query = new URLSearchParams();
  query.set("topic", params.topic);
  if (page > 1) query.set("page", String(page));
  if (params.start_year) query.set("start_year", String(params.start_year));
  if (params.end_year) query.set("end_year", String(params.end_year));
  if (params.open_access_only) query.set("open_access_only", "true");
  if (params.min_citations) query.set("min_citations", String(params.min_citations));
  if (params.sort_by && params.sort_by !== "relevance") query.set("sort_by", params.sort_by);
  if (params.type_filter && params.type_filter !== "all") query.set("type_filter", params.type_filter);
  if (params.author) query.set("author", params.author);
  if (params.sources?.length && !(params.sources.length === 1 && params.sources[0] === "openalex")) {
    query.set("sources", params.sources.join(","));
  }
  if (params.rerank) query.set("rerank", "true");
  return `/?${query.toString()}`;
}

export function parseSearchResults(search: string): { params: SearchParams; page: number } | null {
  const query = new URLSearchParams(search);
  const topic = query.get("topic")?.trim();
  if (!topic) return null;

  const positiveNumber = (name: string) => {
    const value = Number(query.get(name));
    return Number.isSafeInteger(value) && value > 0 ? value : undefined;
  };
  const page = positiveNumber("page") ?? 1;
  const sources = query.get("sources")?.split(",").filter(Boolean);
  return {
    page,
    params: {
      topic,
      start_year: positiveNumber("start_year"),
      end_year: positiveNumber("end_year"),
      open_access_only: query.get("open_access_only") === "true" || undefined,
      min_citations: positiveNumber("min_citations"),
      sort_by: query.get("sort_by") || "relevance",
      type_filter: query.get("type_filter") || undefined,
      author: query.get("author") || undefined,
      sources: sources?.length ? sources : ["openalex"],
      rerank: query.get("rerank") === "true" || undefined,
    },
  };
}
