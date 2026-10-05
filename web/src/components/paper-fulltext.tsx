"use client";

import { useState } from "react";
import { ExternalLink, FileText } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Paper } from "@/lib/types";
import { loadFullText } from "@/lib/api";

interface PaperFullTextProps {
  paper: Paper;
}

type LoadState = "idle" | "loading" | "loaded" | "failed";

export function PaperFullText({ paper }: PaperFullTextProps) {
  const available = paper.open_access && !!paper.oa_url;
  const [state, setState] = useState<LoadState>("idle");
  const [text, setText] = useState("");
  const [truncated, setTruncated] = useState(false);
  const [error, setError] = useState("");

  const handleLoad = async () => {
    setState("loading");
    setError("");
    try {
      const result = await loadFullText(paper);
      setText(result.text);
      setTruncated(result.truncated);
      setState("loaded");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Couldn't load full text.");
      setState("failed");
    }
  };

  return (
    <section className="mt-6 border-t border-border/60 pt-5" aria-labelledby="full-text-heading">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="full-text-heading" className="font-serif text-xl font-semibold">Full text</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Extracted PDF text may lose equations, tables, columns, and other layout.
          </p>
        </div>

        {!available ? (
          <Button variant="outline" disabled>
            <FileText className="h-4 w-4" />
            Full text not available
          </Button>
        ) : state === "loaded" ? (
          <Button asChild variant="outline">
            <a href={paper.oa_url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4" />
              Open original PDF
            </a>
          </Button>
        ) : (
          <Button variant="outline" onClick={handleLoad} disabled={state === "loading"}>
            <FileText className="h-4 w-4" />
            {state === "loading" ? "Loading full text..." : state === "failed" ? "Retry full text" : "Load full text"}
          </Button>
        )}
      </div>

      {!available && (
        <p className="mt-3 text-sm text-muted-foreground">Full text not available.</p>
      )}

      {state === "failed" && (
        <div className="mt-4 border border-destructive/30 bg-destructive/5 p-4">
          <p className="text-sm font-medium text-destructive">Couldn&apos;t load full text.</p>
          {error && error !== "Couldn't load full text." && (
            <p className="mt-1 text-xs text-muted-foreground">{error}</p>
          )}
          <a
            href={paper.oa_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
          >
            Try the original source <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      )}

      {state === "loaded" && (
        <div className="mt-5">
          {truncated && (
            <p className="mb-3 border border-primary/20 bg-accent/50 p-3 text-xs text-muted-foreground">
              This display reached the reading limit. Open the original PDF for the remainder.
            </p>
          )}
          <article className="break-words whitespace-pre-wrap border bg-background p-4 text-sm leading-7 sm:p-6">
            {text}
          </article>
        </div>
      )}
    </section>
  );
}
