"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { SearchFilters } from "@/components/search-filters";
import { PaperCard } from "@/components/paper-card";
import { searchPapers, checkHealth, exportToExcel } from "@/lib/api";
import { Paper, SearchParams, SearchResponse } from "@/lib/types";
import { parseSearchResults, searchResultsHref } from "@/lib/search-routing";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SiteHeader } from "@/components/site-header";
import { HeroWordmark } from "@/components/hero-wordmark";
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

export default function Home() {
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentParams, setCurrentParams] = useState<SearchParams | null>(null);
  const [restoredParams, setRestoredParams] = useState<SearchParams | null>(null);
  const restoredFromUrl = useRef(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [scopusEnabled, setScopusEnabled] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    const fetchHealth = () => {
      checkHealth()
        .then((h) => {
          setAiEnabled(h.ai_enabled);
          setScopusEnabled(h.scopus_enabled || false);
        })
        .catch((err) => {
          console.error("Health check failed:", err);
          // Retry once after 3 seconds
          setTimeout(() => {
            checkHealth()
              .then((h) => {
                setAiEnabled(h.ai_enabled);
                setScopusEnabled(h.scopus_enabled || false);
              })
              .catch((err2) => console.error("Health check retry failed:", err2));
          }, 3000);
        });
    };
    fetchHealth();
  }, []);

  const handleSearch = useCallback(async (params: SearchParams, page = 1) => {
    setLoading(true);
    setError(null);
    setHasSearched(true);
    setCurrentParams(params);
    setCurrentPage(page);
    window.history.replaceState(window.history.state, "", searchResultsHref(params, page));

    try {
      const data = await searchPapers({
        ...params,
        limit: 10,
        page,
        type_filter: params.type_filter === "all" ? undefined : params.type_filter,
      });
      setResults(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Search failed. Is the backend running?";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (restoredFromUrl.current) return;
    restoredFromUrl.current = true;
    const restored = parseSearchResults(window.location.search);
    if (restored) {
      setRestoredParams(restored.params);
      void handleSearch(restored.params, restored.page);
    }
  }, [handleSearch]);

  const handleExport = async () => {
    if (!currentParams) return;
    setExporting(true);
    try {
      await exportToExcel({
        topic: currentParams.topic,
        start_year: currentParams.start_year,
        end_year: currentParams.end_year,
        open_access_only: currentParams.open_access_only,
        min_citations: currentParams.min_citations,
      });
    } catch {
      setError("Excel export failed. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (!currentParams) return;
    handleSearch(currentParams, newPage);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const totalPages = results
    ? Math.ceil(results.total_found / (results.per_page || 10))
    : 0;

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-4 py-7 sm:px-7 sm:py-9">
        {!hasSearched && (
          <section className="mx-auto max-w-4xl px-2 pb-10 pt-8 text-center sm:pb-12 sm:pt-12">
            <HeroWordmark />
            <h1 className="mt-3 font-serif text-4xl font-medium leading-tight tracking-tight sm:mt-4 sm:text-6xl">
              Discover Research That<br /><em className="font-normal text-primary">Matters</em>
            </h1>
            <p className="mx-auto mt-6 max-w-xl text-sm leading-7 text-muted-foreground sm:text-base">
              Search 260M+ scholarly works with AI-powered summaries, hybrid ranking, and instant citation export.
            </p>
          </section>
        )}

        <div className={hasSearched ? "grid gap-5 lg:grid-cols-[260px_minmax(0,1fr)]" : "mx-auto max-w-3xl"}>
        <SearchFilters
          key={restoredParams ? "restored" : "fresh"}
          onSearch={handleSearch}
          initialParams={restoredParams}
          onExport={handleExport}
          loading={loading}
          exporting={exporting}
          showSidebar={hasSearched}
        />
        {hasSearched && <div className="min-w-0 lg:col-start-2 lg:row-start-2">

        {/* Error */}
        {error && (
          <div className="mt-6 p-4 rounded-lg border border-destructive/50 bg-destructive/5 text-destructive text-sm">
            {error}
          </div>
        )}

        {/* Results meta */}
        {results && !loading && (
          <div className="mt-4 sm:mt-6 flex flex-col sm:flex-row sm:items-center justify-between gap-1">
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-3 text-xs sm:text-sm text-muted-foreground font-mono">
              <span className="font-medium text-foreground">
                {results.total_found.toLocaleString()} papers
              </span>
              <span className="hidden sm:inline">|</span>
              <span>{results.years_filter}</span>
              <span className="hidden sm:inline">|</span>
              <span>{results.total_journals} journals</span>
            </div>
            <span className="text-xs text-muted-foreground font-mono">
              Page {currentPage} of {Math.max(totalPages, 1)}
            </span>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="mt-6 space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="space-y-3 border bg-card p-5">
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            ))}
          </div>
        )}

        {/* Paper results */}
        {results && !loading && (
          <div className="mt-4 space-y-3">
            {results.results.map((paper: Paper, i: number) => (
              <PaperCard
                key={paper.id || i}
                paper={paper}
                index={(currentPage - 1) * (results.per_page || 10) + i}
                aiEnabled={aiEnabled}
                scopusEnabled={scopusEnabled}
                returnHref={currentParams ? searchResultsHref(currentParams, currentPage) : "/"}
              />
            ))}
          </div>
        )}

        {/* No results */}
        {results && !loading && results.results.length === 0 && (
          <div className="mt-12 text-center text-muted-foreground">
            <BookOpen className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p className="text-lg font-medium">No papers found</p>
            <p className="text-sm">Try different keywords or adjust your filters.</p>
          </div>
        )}

        {/* Pagination */}
        {results && !loading && results.results.length > 0 && (
          <div className="mt-6 sm:mt-8 flex items-center justify-center gap-1 sm:gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage <= 1}
              className="gap-1 h-8 px-2 sm:px-3"
            >
              <ChevronLeft className="h-4 w-4" />
              <span className="hidden sm:inline">Previous</span>
            </Button>
            <div className="flex items-center gap-0.5 sm:gap-1 px-1 sm:px-3">
              {Array.from(
                { length: Math.min(5, totalPages) },
                (_, i) => {
                  let page: number;
                  if (totalPages <= 5) {
                    page = i + 1;
                  } else if (currentPage <= 3) {
                    page = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    page = totalPages - 4 + i;
                  } else {
                    page = currentPage - 2 + i;
                  }
                  return (
                    <Button
                      key={page}
                      variant={page === currentPage ? "default" : "ghost"}
                      size="sm"
                      className="h-8 w-8 p-0 text-xs"
                      onClick={() => handlePageChange(page)}
                    >
                      {page}
                    </Button>
                  );
                }
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage >= totalPages}
              className="gap-1 h-8 px-2 sm:px-3"
            >
              <span className="hidden sm:inline">Next</span>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}
        </div>}
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-10 border-t">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground sm:px-7">
          <span>Resona — research in focus</span>
          <span>Search · Summarize · Explore</span>
        </div>
      </footer>
    </div>
  );
}
