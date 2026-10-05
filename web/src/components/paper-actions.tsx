"use client";

import { useState } from "react";
import { Paper } from "@/lib/types";
import { summarizePaper, getCitation } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatPanel } from "@/components/chat-panel";
import {
  ExternalLink,
  Quote,
  Sparkles,
  Copy,
  Check,
  Download,
} from "lucide-react";

interface PaperActionsProps {
  paper: Paper;
  aiEnabled: boolean;
  scopusUrl?: string | null;
  showAiUnavailable?: boolean;
  onExport?: () => void;
  exporting?: boolean;
}

export function PaperActions({
  paper,
  aiEnabled,
  scopusUrl,
  showAiUnavailable = false,
  onExport,
  exporting = false,
}: PaperActionsProps) {
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [citation, setCitation] = useState<string | null>(null);
  const [citationFormat, setCitationFormat] = useState<"bibtex" | "apa">("bibtex");
  const [showCitation, setShowCitation] = useState(false);
  const [loadingCitation, setLoadingCitation] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleSummarize = async () => {
    if (aiSummary) {
      setAiSummary(null);
      return;
    }
    setLoadingSummary(true);
    try {
      const res = await summarizePaper(paper.title, paper.abstract);
      setAiSummary(res.summary);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to generate summary";
      setAiSummary(message);
    } finally {
      setLoadingSummary(false);
    }
  };

  const handleCite = async (format: "bibtex" | "apa") => {
    setCitationFormat(format);
    setShowCitation(true);
    setLoadingCitation(true);
    try {
      const res = await getCitation(paper, format);
      setCitation(res.citation);
    } catch {
      setCitation("Failed to generate citation.");
    } finally {
      setLoadingCitation(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const hasAbstract = !!paper.abstract && paper.abstract !== "No abstract available.";

  return (
    <>
      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border pt-4">
        {aiEnabled && (!showAiUnavailable || hasAbstract) && (
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs gap-1.5"
            onClick={handleSummarize}
            disabled={loadingSummary}
          >
            <Sparkles className="h-3.5 w-3.5" />
            {loadingSummary ? "Summarizing..." : aiSummary ? "Hide AI Summary" : "AI Summary"}
          </Button>
        )}

        {aiEnabled && hasAbstract && <ChatPanel paper={paper} />}

        {showAiUnavailable && (!aiEnabled || !hasAbstract) && (
          <>
            <Button variant="outline" size="sm" className="h-7 text-xs gap-1.5" disabled>
              <Sparkles className="h-3.5 w-3.5" />
              AI Summary
            </Button>
            <Button variant="outline" size="sm" className="h-7 text-xs gap-1.5" disabled>
              Discuss With AI
            </Button>
          </>
        )}

        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs gap-1.5"
          onClick={() => handleCite("bibtex")}
        >
          <Quote className="h-3.5 w-3.5" />
          BibTeX
        </Button>

        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs gap-1.5"
          onClick={() => handleCite("apa")}
        >
          <Quote className="h-3.5 w-3.5" />
          APA
        </Button>

        {onExport && (
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs gap-1.5"
            onClick={onExport}
            disabled={exporting}
          >
            <Download className="h-3.5 w-3.5" />
            {exporting ? "Exporting..." : "Export"}
          </Button>
        )}

        {paper.doi && (
          <Button asChild variant="outline" size="sm" className="h-7 text-xs gap-1.5">
            <a href={paper.doi} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-3.5 w-3.5" />
              DOI
            </a>
          </Button>
        )}

        {paper.oa_url && (
          <Button asChild variant="outline" size="sm" className="h-7 text-xs gap-1.5">
            <a href={paper.oa_url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-3.5 w-3.5" />
              Read PDF
            </a>
          </Button>
        )}

        {(scopusUrl || paper.scopus_search_url) && (
          <Button asChild variant="outline" size="sm" className="h-7 text-xs gap-1.5">
            <a
              href={scopusUrl || paper.scopus_search_url || "#"}
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              View on Scopus
            </a>
          </Button>
        )}
      </div>

      {showAiUnavailable && (!aiEnabled || !hasAbstract) && (
        <p className="mt-2 text-xs text-muted-foreground">
          {!aiEnabled
            ? "AI actions are unavailable because no local or configured AI provider is running."
            : "AI actions are unavailable because this paper has no abstract."}
        </p>
      )}

      {loadingSummary && (
        <div className="mt-3 space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="h-4 w-3/5" />
        </div>
      )}
      {aiSummary && !loadingSummary && (
        <div className="mt-3 border border-primary/25 bg-accent/55 p-4">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              <span className="text-xs font-medium text-primary">AI Summary</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-xs gap-1 text-muted-foreground hover:text-foreground"
              onClick={() => copyToClipboard(aiSummary)}
            >
              {copied ? (
                <><Check className="h-3 w-3" /> Copied</>
              ) : (
                <><Copy className="h-3 w-3" /> Copy</>
              )}
            </Button>
          </div>
          <p className="text-sm leading-relaxed">{aiSummary}</p>
        </div>
      )}

      {showCitation && (
        <div className="mt-3 border bg-muted/50 p-4">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium">
              {citationFormat.toUpperCase()} Citation
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-xs gap-1"
              onClick={() => citation && copyToClipboard(citation)}
            >
              {copied ? (
                <><Check className="h-3 w-3" /> Copied</>
              ) : (
                <><Copy className="h-3 w-3" /> Copy</>
              )}
            </Button>
          </div>
          {loadingCitation ? (
            <Skeleton className="h-16 w-full rounded-sm" />
          ) : (
            <pre className="border bg-background p-3 font-mono text-xs whitespace-pre-wrap break-all">
              {citation}
            </pre>
          )}
        </div>
      )}
    </>
  );
}
