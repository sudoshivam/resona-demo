"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  Award,
  BookOpen,
  Building2,
  Calendar,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PaperActions } from "@/components/paper-actions";
import { PaperFullText } from "@/components/paper-fulltext";
import { SiteHeader } from "@/components/site-header";
import { checkHealth, exportPaper, getPaper } from "@/lib/api";
import { normalizePaperRouteId } from "@/lib/paper-routing";
import { parseSearchResults, searchResultsHref } from "@/lib/search-routing";
import { Paper } from "@/lib/types";

function decodePaperId(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export default function PaperDetailPage() {
  const params = useParams<{ id: string | string[] }>();
  const searchParams = useSearchParams();
  const rawId = Array.isArray(params.id) ? params.id.join("/") : (params.id || "");
  const id = normalizePaperRouteId(decodePaperId(rawId));
  const from = searchParams.get("from") || "";
  const previousSearch = from.startsWith("/?") ? parseSearchResults(from.slice(2)) : null;
  const backHref = previousSearch ? searchResultsHref(previousSearch.params, previousSearch.page) : "/";
  const [paper, setPaper] = useState<Paper | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [aiEnabled, setAiEnabled] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");

    Promise.allSettled([getPaper(id), checkHealth()]).then(([paperResult, healthResult]) => {
      if (paperResult.status === "fulfilled") {
        setPaper(paperResult.value);
      } else {
        setError(paperResult.reason instanceof Error ? paperResult.reason.message : "Paper lookup failed");
      }
      if (healthResult.status === "fulfilled") {
        setAiEnabled(healthResult.value.ai_enabled);
      }
      setLoading(false);
    });
  }, [id]);

  const handleExport = async () => {
    if (!paper) return;
    setExporting(true);
    setExportError("");
    try {
      await exportPaper(paper);
    } catch (err: unknown) {
      setExportError(err instanceof Error ? err.message : "Paper export failed");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="min-h-screen">
      <SiteHeader />

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-7 sm:py-8">
        <div className="mb-6 flex items-center justify-between gap-3 border-b border-border pb-4">
          <Link href={backHref} className="inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-primary">
            <ArrowLeft className="h-4 w-4" /> Back to search
          </Link>
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Paper card</span>
        </div>
        {loading && (
          <Card>
            <CardContent className="space-y-4 p-5 sm:p-8">
              <Skeleton className="h-7 w-4/5" />
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </CardContent>
          </Card>
        )}

        {!loading && error && (
          <Card>
            <CardContent className="p-6 text-center sm:p-10">
              <BookOpen className="mx-auto h-10 w-10 text-muted-foreground/40" />
              <h1 className="mt-4 font-serif text-xl font-semibold">Paper unavailable</h1>
              <p className="mx-auto mt-2 max-w-xl text-sm text-muted-foreground">{error}</p>
              <Button asChild className="mt-5">
                <Link href={backHref}>Return to search</Link>
              </Button>
            </CardContent>
          </Card>
        )}

        {!loading && paper && (
          <Card>
            <CardContent className="p-6 sm:p-10">
              <div className="flex flex-wrap gap-2">
                {paper.open_access && <Badge variant="secondary" className="border-[#BDD0B8] bg-[#DCE7D8] font-mono text-[#2D5A27] dark:border-[#536B4E] dark:bg-[#29392B] dark:text-[#B9D4AE] uppercase tracking-wide">Open Access</Badge>}
                {paper.type && <Badge variant="outline" className="font-mono uppercase tracking-wide">{paper.type}</Badge>}
              </div>

              <h1 className="mt-5 max-w-4xl font-serif text-3xl font-medium leading-tight sm:text-5xl">
                {paper.title}
              </h1>

              <div className="mt-5 flex items-start gap-2 text-sm text-muted-foreground">
                <Users className="mt-0.5 h-4 w-4 shrink-0" />
                <div className="flex flex-wrap gap-x-1.5 gap-y-1">
                  {paper.authors.length > 0 ? paper.authors.map((author, index) => (
                    <span key={`${author.id || author.name}-${index}`}>
                      {author.orcid ? (
                        <a href={author.orcid} target="_blank" rel="noopener noreferrer" className="hover:text-primary hover:underline">
                          {author.name}
                        </a>
                      ) : author.name}
                      {index < paper.authors.length - 1 ? "," : ""}
                    </span>
                  )) : "Unknown authors"}
                </div>
              </div>

              <div className="mt-7 grid gap-3 border-y border-border py-5 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <div className="flex items-center gap-2">
                  <BookOpen className="h-4 w-4 text-primary" />
                  <span>{paper.journal}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Building2 className="h-4 w-4 text-primary" />
                  <span>{paper.publisher}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-primary" />
                  <span>{paper.year || "Unknown year"}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Award className="h-4 w-4 text-primary" />
                  <span>{paper.citations.toLocaleString()} citations</span>
                </div>
              </div>

              {paper.doi && <p className="mt-3 break-all font-mono text-xs text-muted-foreground">DOI: {paper.doi.replace(/^https?:\/\/(?:dx\.)?doi\.org\//, "")}</p>}

              {paper.concepts.length > 0 && (
                <div className="mt-5 flex flex-wrap gap-1.5">
                  {paper.concepts.map((concept) => (
                    <Badge key={concept.name} variant="outline" className="font-normal">
                      {concept.name}
                    </Badge>
                  ))}
                </div>
              )}

              <PaperActions
                paper={paper}
                aiEnabled={aiEnabled}
                showAiUnavailable
                onExport={handleExport}
                exporting={exporting}
              />
              {exportError && <p className="mt-2 text-xs text-destructive">{exportError}</p>}

              <section className="mt-9 border-t border-border pt-7" aria-labelledby="abstract-heading">
                <h2 id="abstract-heading" className="font-serif text-2xl font-medium">Abstract</h2>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-muted-foreground sm:text-base">
                  {paper.abstract || "No abstract available."}
                </p>
              </section>

              <PaperFullText paper={paper} />
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
