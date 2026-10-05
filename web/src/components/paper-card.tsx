"use client";

import { useState, useEffect, type MouseEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Paper } from "@/lib/types";
import { paperDetailHref } from "@/lib/paper-routing";
import { checkScopus } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PaperActions } from "@/components/paper-actions";
import {
  BookOpen,
  Users,
  Calendar,
  Award,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

interface PaperCardProps {
  paper: Paper;
  index: number;
  aiEnabled: boolean;
  scopusEnabled?: boolean;
  returnHref: string;
}

export function PaperCard({ paper, index, aiEnabled, scopusEnabled, returnHref }: PaperCardProps) {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const [scopusIndexed, setScopusIndexed] = useState<boolean | null>(null);
  const [scopusUrl, setScopusUrl] = useState<string | null>(null);

  useEffect(() => {
    if (scopusEnabled && paper.doi) {
      checkScopus(paper.doi)
        .then((res) => {
          setScopusIndexed(res.indexed);
          if (res.scopus_url) setScopusUrl(res.scopus_url);
        })
        .catch(() => {});
    }
  }, [scopusEnabled, paper.doi]);

  const authorNames = paper.authors
    .map((a) => a.name)
    .join(", ");
  const detailHref = `${paperDetailHref(paper.id)}?from=${encodeURIComponent(returnHref)}`;

  const handleCardClick = (event: MouseEvent<HTMLDivElement>) => {
    const target = event.target as Element;
    if (target.closest("a, button, input, select, textarea") || window.getSelection()?.toString()) {
      return;
    }
    router.push(detailHref);
  };

  return (
    <Card
      className="cursor-pointer hover:border-primary/60"
      onClick={handleCardClick}
    >
      <CardContent className="p-5 sm:p-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono font-medium text-foreground shrink-0">
                #{String(index + 1).padStart(2, "0")}
              </span>
              <div className="flex flex-wrap gap-1.5">
                {paper.open_access && (
                  <Badge variant="secondary" className="border-[#BDD0B8] bg-[#DCE7D8] font-mono text-[#2D5A27] dark:border-[#536B4E] dark:bg-[#29392B] dark:text-[#B9D4AE] text-[10px] uppercase tracking-wide">
                    Open Access
                  </Badge>
                )}
                {scopusIndexed && (
                  <Badge variant="secondary" className="border-[#D8C7B0] bg-[#EFE3D3] font-mono text-[#7A4B1A] dark:border-[#6D5539] dark:bg-[#3D3021] dark:text-[#D8B785] text-[10px] uppercase tracking-wide">
                    Scopus Indexed
                  </Badge>
                )}
                {paper.type && (
                  <Badge variant="outline" className="font-mono text-[10px] uppercase tracking-wide">
                    {paper.type}
                  </Badge>
                )}
              </div>
            </div>

            <h3 className="mb-3 font-serif text-xl font-medium leading-snug sm:text-2xl">
              <Link href={detailHref} className="hover:text-primary transition-colors">
                {paper.title}
              </Link>
            </h3>

            {/* Authors */}
            <div className="mb-2 flex items-center gap-1.5 text-xs text-muted-foreground">
              <Users className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{authorNames || "Unknown authors"}</span>
            </div>

            {/* Meta row */}
            <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] text-muted-foreground sm:gap-3">
              <span className="flex items-center gap-1">
                <BookOpen className="h-3.5 w-3.5" />
                {paper.journal}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" />
                {paper.year}
              </span>
              <span className="flex items-center gap-1">
                <Award className="h-3.5 w-3.5" />
                {paper.citations.toLocaleString()} citations
              </span>
              <span className="hidden bg-muted px-1.5 py-0.5 font-mono text-[10px] sm:inline">
                Score: {paper.score}
              </span>
            </div>
          </div>
        </div>

        {/* Abstract snippet */}
        <div className="mt-4 border-t border-border pt-3">
          <p className="text-sm text-muted-foreground leading-relaxed">
            {expanded ? paper.abstract || paper.summary : paper.summary}
          </p>
          {paper.abstract && paper.abstract.length > paper.summary.length && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-primary hover:underline mt-1 flex items-center gap-0.5"
            >
              {expanded ? (
                <>Show less <ChevronUp className="h-3 w-3" /></>
              ) : (
                <>Read full abstract <ChevronDown className="h-3 w-3" /></>
              )}
            </button>
          )}
        </div>

        {/* Concepts */}
        {paper.concepts.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {paper.concepts.map((c, i) => (
              <Badge key={i} variant="outline" className="text-[10px] font-normal">
                {c.name}
              </Badge>
            ))}
          </div>
        )}

        <PaperActions paper={paper} aiEnabled={aiEnabled} scopusUrl={scopusUrl} />
      </CardContent>
    </Card>
  );
}
