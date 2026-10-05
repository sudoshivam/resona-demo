"use client";

import { useMemo, useState } from "react";
import { Download, Search, SlidersHorizontal, Sparkles } from "lucide-react";
import type { SearchParams } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const SOURCES = [
  { value: "openalex", label: "OpenAlex" },
  { value: "crossref", label: "Crossref" },
  { value: "semantic_scholar", label: "Semantic Scholar" },
  { value: "arxiv", label: "arXiv" },
] as const;
const SUGGESTIONS = ["transformers", "UAV remote sensing", "object detection", "climate change"];

interface SearchFiltersProps {
  onSearch: (params: SearchParams) => void;
  initialParams?: SearchParams | null;
  onExport: () => void;
  loading: boolean;
  exporting?: boolean;
  showSidebar?: boolean;
}

export function SearchFilters({ onSearch, initialParams, onExport, loading, exporting, showSidebar = false }: SearchFiltersProps) {
  const [topic, setTopic] = useState(initialParams?.topic || "");
  const [startYear, setStartYear] = useState(initialParams?.start_year ? String(initialParams.start_year) : "");
  const [endYear, setEndYear] = useState(initialParams?.end_year ? String(initialParams.end_year) : "");
  const [openAccessOnly, setOpenAccessOnly] = useState(Boolean(initialParams?.open_access_only));
  const [minCitations, setMinCitations] = useState(initialParams?.min_citations ? String(initialParams.min_citations) : "");
  const [sortBy, setSortBy] = useState(initialParams?.sort_by || "relevance");
  const [typeFilter, setTypeFilter] = useState(initialParams?.type_filter || "");
  const [author, setAuthor] = useState(initialParams?.author || "");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showMobileFilters, setShowMobileFilters] = useState(false);
  const [sources, setSources] = useState<string[]>(initialParams?.sources?.length ? initialParams.sources : ["openalex"]);
  const [rerank, setRerank] = useState(Boolean(initialParams?.rerank));
  const currentYear = new Date().getFullYear();
  const years = useMemo(() => Array.from({ length: currentYear - 1949 }, (_, i) => currentYear - i), [currentYear]);

  const toggleSource = (value: string) => setSources((current) =>
    current.includes(value)
      ? current.length === 1 ? current : current.filter((source) => source !== value)
      : [...current, value]
  );
  const handleSearch = (suggestedTopic?: string) => {
    const query = (suggestedTopic ?? topic).trim();
    if (!query) return;
    if (suggestedTopic) setTopic(suggestedTopic);
    onSearch({
      topic: query,
      start_year: startYear && startYear !== "any" ? Number(startYear) : undefined,
      end_year: endYear && endYear !== "any" ? Number(endYear) : undefined,
      open_access_only: openAccessOnly || undefined,
      min_citations: minCitations && minCitations !== "any" ? Number(minCitations) : undefined,
      sort_by: sortBy,
      type_filter: typeFilter || undefined,
      author: author.trim() || undefined,
      sources,
      rerank: rerank || undefined,
    });
  };
  const clearFilters = () => {
    setStartYear(""); setEndYear(""); setOpenAccessOnly(false); setMinCitations("");
    setSortBy("relevance"); setTypeFilter(""); setAuthor(""); setSources(["openalex"]); setRerank(false);
  };

  return (
    <div className={showSidebar ? "contents" : "space-y-5"}>
      <section className={showSidebar ? "lg:col-span-2" : ""} aria-label="Search papers">
        <form className="flex overflow-hidden rounded-sm border border-border bg-card focus-within:ring-2 focus-within:ring-ring/40" onSubmit={(event) => { event.preventDefault(); handleSearch(); }}>
          <Search className="ml-4 mt-3.5 h-4 w-4 shrink-0 text-muted-foreground" />
          <Input aria-label="Search papers, topics, authors" placeholder="Search papers, topics, authors..." value={topic} onChange={(event) => setTopic(event.target.value)} className="h-11 flex-1 border-0 bg-transparent shadow-none focus-visible:ring-0" />
          <Button type="submit" disabled={loading || !topic.trim()} className="h-11 rounded-none px-5 sm:px-7">{loading ? "Searching..." : "Search →"}</Button>
        </form>
        {!showSidebar && <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          <span className="mr-1 font-mono text-muted-foreground">TRY:</span>
          {SUGGESTIONS.map((suggestion) => <button key={suggestion} type="button" onClick={() => handleSearch(suggestion)} className="rounded-full border border-border bg-secondary/60 px-3 py-1 text-foreground transition-colors hover:border-primary hover:text-primary">{suggestion}</button>)}
        </div>}
      </section>

      <aside className={showSidebar ? "border border-border bg-card p-5 lg:row-start-2" : "border-t border-border pt-4"}>
        <div className="mb-5 flex items-center justify-between gap-2">
          <h2 className="font-serif text-lg font-semibold">Filters</h2>
          <div className="flex items-center gap-3">
            <button type="button" onClick={clearFilters} className="text-xs text-primary hover:underline">Clear all</button>
            {showSidebar && <button type="button" onClick={() => setShowMobileFilters(!showMobileFilters)} aria-expanded={showMobileFilters} className="text-xs text-primary lg:hidden">
              {showMobileFilters ? "Hide" : "Show"}
            </button>}
          </div>
        </div>
        <div className={showSidebar && !showMobileFilters ? "hidden space-y-5 lg:block" : "space-y-5"}>
          <fieldset>
            <legend className="mb-2 text-sm font-semibold">Sources</legend>
            <div className="grid grid-cols-2 gap-x-3 gap-y-2 lg:grid-cols-1">
              {SOURCES.map((source) => <label key={source.value} className="flex cursor-pointer items-center gap-2 text-xs">
                <input type="checkbox" checked={sources.includes(source.value)} onChange={() => toggleSource(source.value)} className="size-4 accent-primary" />
                {source.label}
              </label>)}
            </div>
          </fieldset>
          <button type="button" aria-pressed={rerank} onClick={() => setRerank(!rerank)} className="flex w-full items-center justify-between gap-2 border-t border-border pt-4 text-left text-xs font-medium">
            <span className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-primary" /> Semantic rerank</span>
            <span className={rerank ? "text-primary" : "text-muted-foreground"}>{rerank ? "On" : "Off"}</span>
          </button>
          {!showSidebar && <Button type="button" variant="outline" size="sm" onClick={() => setShowAdvanced(!showAdvanced)} aria-expanded={showAdvanced} className="w-full justify-between">
            <span className="flex items-center gap-2"><SlidersHorizontal className="h-4 w-4" /> Advanced filters</span><span>{showAdvanced ? "−" : "+"}</span>
          </Button>}
          {(showSidebar || showAdvanced) && <div className="grid gap-4 border-t border-border pt-4 sm:grid-cols-2 lg:grid-cols-1">
            <div className="space-y-2">
              <label className="text-xs font-semibold">Year range</label>
              <div className="flex items-center gap-2">
                <Select value={startYear} onValueChange={setStartYear}>
                  <SelectTrigger aria-label="From year" className="h-9 min-w-0 flex-1 text-xs"><SelectValue placeholder={String(currentYear - 5)} /></SelectTrigger>
                  <SelectContent className="max-h-56"><SelectItem value="any">Any</SelectItem>{years.map((year) => <SelectItem key={year} value={String(year)}>{year}</SelectItem>)}</SelectContent>
                </Select>
                <span className="text-muted-foreground">–</span>
                <Select value={endYear} onValueChange={setEndYear}>
                  <SelectTrigger aria-label="To year" className="h-9 min-w-0 flex-1 text-xs"><SelectValue placeholder={String(currentYear)} /></SelectTrigger>
                  <SelectContent className="max-h-56"><SelectItem value="any">Any</SelectItem>{years.map((year) => <SelectItem key={year} value={String(year)}>{year}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <label className="flex items-center gap-2 text-xs">
              <input type="checkbox" checked={openAccessOnly} onChange={(event) => setOpenAccessOnly(event.target.checked)} className="size-4 accent-primary" />Open Access only
            </label>
            <div className="space-y-2">
              <label className="text-xs font-semibold">Minimum citations</label>
              <Select value={minCitations} onValueChange={setMinCitations}>
                <SelectTrigger aria-label="Minimum citations" className="h-9 w-full text-xs"><SelectValue placeholder="Any" /></SelectTrigger>
                <SelectContent><SelectItem value="any">Any</SelectItem>{[5, 10, 25, 50, 100, 500, 1000].map((count) => <SelectItem key={count} value={String(count)}>{count.toLocaleString()}+</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-semibold">Sort by</label>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger aria-label="Sort by" className="h-9 w-full text-xs"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="relevance">Relevance</SelectItem><SelectItem value="citations">Most cited</SelectItem><SelectItem value="year_desc">Newest first</SelectItem><SelectItem value="year_asc">Oldest first</SelectItem></SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-semibold">Document type</label>
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger aria-label="Document type" className="h-9 w-full text-xs"><SelectValue placeholder="All types" /></SelectTrigger>
                <SelectContent><SelectItem value="all">All types</SelectItem><SelectItem value="article">Journal article</SelectItem><SelectItem value="review">Review</SelectItem><SelectItem value="book-chapter">Book chapter</SelectItem><SelectItem value="proceedings-article">Conference paper</SelectItem><SelectItem value="dissertation">Dissertation</SelectItem><SelectItem value="preprint">Preprint</SelectItem></SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label htmlFor="author-filter" className="text-xs font-semibold">Author</label>
              <Input id="author-filter" placeholder="Author name" value={author} onChange={(event) => setAuthor(event.target.value)} className="h-9 text-xs" />
            </div>
          </div>}
          <Button type="button" variant="outline" size="sm" onClick={onExport} disabled={!topic.trim() || exporting} className="w-full">
            <Download className="h-4 w-4" />{exporting ? "Exporting..." : "Export Excel"}
          </Button>
        </div>
      </aside>
    </div>
  );
}
