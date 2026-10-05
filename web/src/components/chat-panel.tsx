"use client";

import { useState, useRef, useEffect } from "react";
import { Paper, ChatMessage, ChatGrounding } from "@/lib/types";
import { streamChatWithPaper } from "@/lib/api";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MessagesSquare, Send, Sparkles, Square } from "lucide-react";

interface ChatPanelProps {
  paper: Paper;
}

// Pure render of a single turn. Kept a pure function of {role, content} so a
// later streaming increment can grow the last assistant message's content in
// place without changing how messages render.
function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={isUser ? "flex justify-end" : "flex justify-start"}>
      <div
        className={
          isUser
            ? "max-w-[85%] border border-primary bg-primary px-3.5 py-2 text-sm text-primary-foreground whitespace-pre-wrap"
            : "max-w-[85%] border bg-card px-3.5 py-2 text-sm leading-relaxed whitespace-pre-wrap"
        }
      >
        {message.content}
      </div>
    </div>
  );
}

export function ChatPanel({ paper }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamStarted, setStreamStarted] = useState(false);
  const [streamError, setStreamError] = useState("");
  const [grounding, setGrounding] = useState<ChatGrounding | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: streamStarted ? "auto" : "smooth",
      });
    });
    return () => cancelAnimationFrame(frame);
  }, [messages, loading, streamStarted, streamError]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      abortControllerRef.current?.abort();
    };
  }, []);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    setStreamStarted(false);
    setStreamError("");

    const controller = new AbortController();
    abortControllerRef.current = controller;
    const assistantIndex = nextMessages.length;

    try {
      for await (const event of streamChatWithPaper(paper, nextMessages, controller.signal)) {
        if (!mountedRef.current) return;

        if (event.type === "meta") {
          setGrounding(event.grounding);
        } else if (event.type === "token") {
          if (!event.delta) continue;
          setStreamStarted(true);
          setMessages((current) => {
            if (current.length === assistantIndex) {
              return [...current, { role: "assistant", content: event.delta }];
            }
            return current.map((message, index) =>
              index === assistantIndex
                ? { ...message, content: message.content + event.delta }
                : message
            );
          });
        } else if (event.type === "error") {
          setStreamError(event.error);
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;
      const message = err instanceof Error ? err.message : "Failed to get a response.";
      if (mountedRef.current) setStreamError(message);
    } finally {
      if (mountedRef.current && abortControllerRef.current === controller) {
        abortControllerRef.current = null;
        setLoading(false);
        setStreamStarted(false);
      }
    }
  };

  const handleStop = () => {
    abortControllerRef.current?.abort();
  };

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className="h-7 text-xs gap-1.5">
          <MessagesSquare className="h-3.5 w-3.5" />
          Discuss With AI
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-full sm:max-w-md p-0">
        <SheetHeader className="border-b border-border/50">
          <SheetTitle className="flex items-center gap-1.5 text-sm pr-6">
            <Sparkles className="h-4 w-4 text-primary shrink-0" />
            <span className="line-clamp-2">{paper.title}</span>
          </SheetTitle>
          <SheetDescription className="text-xs">
            {grounding === "fulltext"
              ? "Answering from relevant excerpts of the full text."
              : grounding === "abstract"
                ? "Answering from the abstract (full text unavailable)."
                : "Answers are grounded only in this paper, never outside knowledge."}
          </SheetDescription>
        </SheetHeader>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 space-y-3">
          {messages.length === 0 && !loading && (
            <div className="h-full flex flex-col items-center justify-center text-center text-muted-foreground gap-2 py-10">
              <MessagesSquare className="h-8 w-8 opacity-30" />
              <p className="text-sm font-medium">Ask about this paper</p>
              <p className="text-xs max-w-[240px]">
                Questions are answered from the abstract. It will say so when the
                abstract doesn&apos;t cover something.
              </p>
            </div>
          )}
          {messages.map((m, i) => (
            <MessageBubble key={i} message={m} />
          ))}
          {streamError && (
            <div className="flex justify-start" role="alert">
              <div className="max-w-[85%] border border-destructive/30 bg-destructive/10 px-3.5 py-2 text-sm text-destructive">
                {streamError}
              </div>
            </div>
          )}
          {loading && !streamStarted && (
            <div className="flex justify-start">
              <div className="flex gap-1 border bg-card px-3.5 py-2.5">
                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:-0.3s]" />
                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:-0.15s]" />
                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce" />
              </div>
            </div>
          )}
        </div>

        <form
          className="flex items-center gap-2 border-t border-border/50 p-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (loading) {
              handleStop();
            } else {
              handleSend();
            }
          }}
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            className="h-9 text-sm"
            disabled={loading}
          />
          <Button
            type="submit"
            size="icon"
            className="h-9 w-9 shrink-0"
            disabled={!loading && !input.trim()}
            aria-label={loading ? "Stop generating" : "Send message"}
          >
            {loading ? <Square className="h-3.5 w-3.5 fill-current" /> : <Send className="h-4 w-4" />}
          </Button>
        </form>
      </SheetContent>
    </Sheet>
  );
}
