import {
  SearchParams,
  SearchResponse,
  HealthResponse,
  Paper,
  ChatMessage,
  ChatStreamEvent,
  FullTextResponse,
} from "./types";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:9999";
const IS_BROWSER = typeof window !== "undefined";
const IS_DEV = process.env.NODE_ENV === "development";
// In dev, use Next.js proxy to avoid CORS; in prod, call backend directly
const API_BASE = IS_BROWSER && IS_DEV ? "/api/proxy" : BACKEND_URL;

export async function searchPapers(params: SearchParams): Promise<SearchResponse> {
  const query = new URLSearchParams();
  query.set("topic", params.topic);
  if (params.limit) query.set("limit", String(params.limit));
  if (params.page) query.set("page", String(params.page));
  if (params.start_year) query.set("start_year", String(params.start_year));
  if (params.end_year) query.set("end_year", String(params.end_year));
  if (params.open_access_only) query.set("open_access_only", "true");
  if (params.min_citations) query.set("min_citations", String(params.min_citations));
  if (params.sort_by) query.set("sort_by", params.sort_by);
  if (params.type_filter) query.set("type_filter", params.type_filter);
  if (params.author) query.set("author", params.author);
  if (params.sources && params.sources.length > 0) query.set("sources", params.sources.join(","));
  if (params.rerank) query.set("rerank", "true");

  const res = await fetch(`${API_BASE}/search?${query.toString()}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Search failed" }));
    throw new Error(error.detail || "Search failed");
  }
  return res.json();
}

export async function getPaper(id: string): Promise<Paper> {
  const res = await fetch(`${API_BASE}/paper/${encodeURIComponent(id)}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Paper lookup failed" }));
    throw new Error(error.detail || "Paper lookup failed");
  }
  return res.json();
}

export async function summarizePaper(
  title: string,
  abstract: string
): Promise<{ summary: string }> {
  const res = await fetch(`${API_BASE}/summarize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, abstract }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Summary failed" }));
    throw new Error(error.detail || "Summary failed");
  }
  return res.json();
}

function parseChatStreamEvent(frame: string): ChatStreamEvent | null {
  const data = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");

  if (!data) return null;

  const event: unknown = JSON.parse(data);
  if (!event || typeof event !== "object" || !("type" in event)) {
    throw new Error("Received an invalid chat stream event.");
  }

  const value = event as Record<string, unknown>;
  if (
    value.type === "meta" &&
    typeof value.provider === "string" &&
    (value.grounding === "fulltext" || value.grounding === "abstract")
  ) {
    return {
      type: "meta",
      provider: value.provider,
      grounding: value.grounding,
    };
  }
  if (value.type === "token" && typeof value.delta === "string") {
    return { type: "token", delta: value.delta };
  }
  if (value.type === "done") {
    return { type: "done" };
  }
  if (value.type === "error" && typeof value.error === "string") {
    return { type: "error", error: value.error };
  }

  throw new Error("Received an invalid chat stream event.");
}

export async function* streamChatWithPaper(
  paper: Paper,
  messages: ChatMessage[],
  signal?: AbortSignal
): AsyncGenerator<ChatStreamEvent, void, void> {
  // Next.js rewrites buffer streaming responses, so chat connects directly to
  // the configured backend while the non-streaming APIs keep using the dev proxy.
  const res = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal,
    body: JSON.stringify({
      title: paper.title,
      abstract: paper.abstract,
      open_access: paper.open_access,
      oa_url: paper.oa_url,
      paper_id: paper.id,
      messages,
    }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Chat failed" }));
    throw new Error(error.detail || "Chat failed");
  }

  if (!res.body) {
    throw new Error("Chat stream is unavailable.");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let terminalEventReceived = false;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        buffer += decoder.decode();
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        const event = parseChatStreamEvent(frame);
        if (!event) continue;

        yield event;
        if (event.type === "done" || event.type === "error") {
          terminalEventReceived = true;
          return;
        }
      }
    }

    if (!terminalEventReceived) {
      throw new Error("Chat stream ended before the response completed.");
    }
  } finally {
    try {
      await reader.cancel();
    } catch {
      // The fetch abort path can close the reader before cancellation runs.
    }
    reader.releaseLock();
  }
}

export async function getCitation(
  paper: Paper,
  format: "bibtex" | "apa"
): Promise<{ citation: string }> {
  const res = await fetch(`${API_BASE}/cite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paper, format }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Citation failed" }));
    throw new Error(error.detail || "Citation failed");
  }
  return res.json();
}

export async function getBatchCitations(
  papers: Paper[],
  format: "bibtex" | "apa"
): Promise<{ citations: string }> {
  const res = await fetch(`${API_BASE}/cite/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ papers, format }),
  });
  if (!res.ok) {
    throw new Error("Batch citation failed");
  }
  return res.json();
}

export async function exportToExcel(params: {
  topic: string;
  start_year?: number;
  end_year?: number;
  open_access_only?: boolean;
  min_citations?: number;
}): Promise<void> {
  const query = new URLSearchParams();
  query.set("topic", params.topic);
  if (params.start_year) query.set("start_year", String(params.start_year));
  if (params.end_year) query.set("end_year", String(params.end_year));
  if (params.open_access_only) query.set("open_access_only", "true");
  if (params.min_citations) query.set("min_citations", String(params.min_citations));

  const res = await fetch(`${API_BASE}/export?${query.toString()}`);
  if (!res.ok) throw new Error("Export failed");

  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition");
  const filename = disposition?.match(/filename=(.+)/)?.[1] || `research_${params.topic.replace(/\s+/g, "_")}.xlsx`;

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function exportPaper(paper: Paper): Promise<void> {
  const res = await fetch(`${API_BASE}/export/paper`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paper }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Paper export failed" }));
    throw new Error(error.detail || "Paper export failed");
  }

  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition");
  const filename = disposition?.match(/filename="?([^";]+)"?/)?.[1] || "paper.xlsx";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function loadFullText(paper: Paper): Promise<FullTextResponse> {
  const res = await fetch(`${API_BASE}/fulltext`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      open_access: paper.open_access,
      oa_url: paper.oa_url,
      paper_id: paper.id,
    }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Couldn't load full text." }));
    throw new Error(error.detail || "Couldn't load full text.");
  }
  return res.json();
}

export async function checkScopus(
  doi: string
): Promise<{ indexed: boolean; scopus_url: string | null; scopus_id: string | null }> {
  const res = await fetch(`${API_BASE}/scopus/check?doi=${encodeURIComponent(doi)}`);
  if (!res.ok) {
    return { indexed: false, scopus_url: null, scopus_id: null };
  }
  return res.json();
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}
