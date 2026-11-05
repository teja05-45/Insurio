"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  Check,
  Copy,
  FileText,
  MessageSquarePlus,
  RefreshCw,
  Square,
  ThumbsDown,
  ThumbsUp,
  Trash2,
} from "lucide-react";

import { CitationList } from "@/components/CitationList";
import { Markdown } from "@/components/Markdown";
import { VoiceButton } from "@/components/VoiceButton";
import {
  Badge,
  Button,
  Card,
  ErrorState,
  Skeleton,
  Spinner,
  cn,
} from "@/components/ui";
import { ApiError, api, streamAnswer } from "@/lib/api";
import type { Conversation, ConversationDetail, Message } from "@/lib/types";

const STARTERS = [
  "What are the waiting periods for this policy?",
  "Which conditions and treatments are excluded?",
  "How do I file a claim, and what documents do I need?",
];

function placeholder(id: string, role: "user" | "assistant", content: string): Message {
  return {
    id,
    role,
    content,
    status: role === "assistant" ? "streaming" : "complete",
    citations: [],
    confidence: null,
    insufficient_evidence: false,
    citation_status: null,
    model: null,
    latency_ms: null,
    // Server timestamps replace this when the conversation is reloaded.
    created_at: "",
  };
}

export default function ChatWorkspacePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [history, setHistory] = useState<Conversation[] | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const [mode, setMode] = useState<string | null>(null);
  const [ratings, setRatings] = useState<Record<string, "up" | "down">>({});
  const [copied, setCopied] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const localIds = useRef(0);

  const busy = streamingId !== null;

  const loadConversation = useCallback(async () => {
    const detail = await api.getConversation(id);
    setConversation(detail);
    setMessages(detail.messages);
  }, [id]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [detail, list] = await Promise.all([
          api.getConversation(id),
          api.listConversations(1, 20),
        ]);
        if (!active) return;
        setConversation(detail);
        setMessages(detail.messages);
        setHistory(list.items);
      } catch (caught) {
        if (active) {
          setError(
            caught instanceof ApiError ? caught.message : "Could not load this conversation.",
          );
        }
      }
    })();
    return () => {
      active = false;
      abortRef.current?.abort();
    };
  }, [id]);

  useEffect(() => {
    const node = scrollRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages]);

  async function send(question: string) {
    const trimmed = question.trim();
    if (!trimmed || busy) return;
    localIds.current += 1;
    const stamp = localIds.current;
    const userId = `local-user-${stamp}`;
    const assistantId = `local-assistant-${stamp}`;
    setMessages((prev) => [
      ...prev,
      placeholder(userId, "user", trimmed),
      placeholder(assistantId, "assistant", ""),
    ]);
    setInput("");
    setError(null);
    setStreamingId(assistantId);
    const controller = new AbortController();
    abortRef.current = controller;
    let text = "";

    try {
      for await (const event of streamAnswer(
        `/conversations/${id}/messages`,
        { question: trimmed },
        controller.signal,
      )) {
        if (event.event === "meta") {
          setMode(event.data.retrieval_mode);
        } else if (event.event === "delta") {
          text += event.data.text;
          const snapshot = text;
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantId ? { ...message, content: snapshot } : message,
            ),
          );
        } else if (event.event === "error") {
          throw new ApiError(event.data.message, 400, event.data.code);
        }
      }
      await loadConversation();
    } catch (caught) {
      if (!(caught instanceof DOMException && caught.name === "AbortError")) {
        setError(
          caught instanceof ApiError ? caught.message : "The answer could not be generated.",
        );
      }
      try {
        await loadConversation();
      } catch {
        // Keep the partial transcript visible if the reload also fails.
      }
    } finally {
      setStreamingId(null);
      abortRef.current = null;
    }
  }

  async function regenerate() {
    if (busy) return;
    const lastAssistant = [...messages].reverse().find((message) => message.role === "assistant");
    if (!lastAssistant) return;
    setStreamingId(lastAssistant.id);
    setError(null);
    setMessages((prev) =>
      prev.map((message) =>
        message.id === lastAssistant.id
          ? { ...message, content: "", status: "streaming", citations: [] }
          : message,
      ),
    );
    const controller = new AbortController();
    abortRef.current = controller;
    let text = "";

    try {
      for await (const event of streamAnswer(
        `/conversations/${id}/regenerate`,
        {},
        controller.signal,
      )) {
        if (event.event === "meta") {
          setMode(event.data.retrieval_mode);
        } else if (event.event === "delta") {
          text += event.data.text;
          const snapshot = text;
          setMessages((prev) =>
            prev.map((message) =>
              message.id === lastAssistant.id ? { ...message, content: snapshot } : message,
            ),
          );
        } else if (event.event === "error") {
          throw new ApiError(event.data.message, 400, event.data.code);
        }
      }
      await loadConversation();
    } catch (caught) {
      if (!(caught instanceof DOMException && caught.name === "AbortError")) {
        setError(
          caught instanceof ApiError ? caught.message : "The answer could not be regenerated.",
        );
      }
      try {
        await loadConversation();
      } catch {
        // Leave the partial answer on screen.
      }
    } finally {
      setStreamingId(null);
      abortRef.current = null;
    }
  }

  async function deleteConversation() {
    if (!conversation) return;
    if (!window.confirm("Delete this conversation and its answers?")) return;
    try {
      await api.deleteConversation(conversation.id);
      router.push("/chat");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not delete the conversation.");
    }
  }

  async function copy(message: Message) {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(message.id);
      window.setTimeout(() => setCopied(null), 1500);
    } catch {
      setError("Copying is not available in this browser.");
    }
  }

  async function rate(message: Message, rating: "up" | "down") {
    try {
      await api.feedback(message.id, rating);
      setRatings((prev) => ({ ...prev, [message.id]: rating }));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Feedback could not be saved.");
    }
  }

  if (!conversation && !error) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-[50vh]" />
      </div>
    );
  }

  if (!conversation) {
    return <ErrorState title="Conversation unavailable" message={error ?? "Not found."} />;
  }

  const hasAnswer = messages.some((message) => message.role === "assistant");

  return (
    <div className="lg:grid lg:grid-cols-[220px_1fr] lg:gap-5">
      <aside className="hidden lg:block">
        <div className="sticky top-6">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              History
            </h2>
            <Link
              href="/chat"
              className="text-[11px] font-medium text-primary hover:underline"
              title="New conversation"
            >
              New
            </Link>
          </div>
          {history === null ? (
            <div className="space-y-1.5">
              <Skeleton className="h-9" />
              <Skeleton className="h-9" />
            </div>
          ) : (
            <ul className="space-y-0.5">
              {history.map((item) => (
                <li key={item.id}>
                  <Link
                    href={`/chat/${item.id}`}
                    className={cn(
                      "block truncate rounded-md px-2 py-1.5 text-xs transition-colors",
                      item.id === conversation.id
                        ? "bg-primary/10 font-medium text-primary"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    {item.title}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>

      <div className="flex min-w-0 flex-col gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <Link href="/chat" className="text-xs text-muted-foreground hover:text-foreground lg:hidden">
              ← All conversations
            </Link>
            <h1 className="truncate text-lg font-semibold tracking-tight">{conversation.title}</h1>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Link
                href={`/documents/${conversation.document_id}`}
                className="inline-flex items-center gap-1 hover:text-foreground"
              >
                <FileText size={12} aria-hidden />
                {conversation.document_filename ?? "Policy"}
              </Link>
              {mode ? <Badge tone="primary">{mode} retrieval</Badge> : null}
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <Link
              href="/chat"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-white px-3 text-xs font-medium hover:bg-muted"
            >
              <MessageSquarePlus size={14} aria-hidden />
              New chat
            </Link>
            <button
              type="button"
              onClick={() => void deleteConversation()}
              className="rounded-md p-2 text-muted-foreground hover:bg-danger/10 hover:text-danger"
              aria-label="Delete conversation"
              title="Delete conversation"
            >
              <Trash2 size={15} aria-hidden />
            </button>
          </div>
        </div>

        {error ? <ErrorState message={error} /> : null}

        <Card className="flex h-[calc(100dvh-13rem)] min-h-[480px] flex-col overflow-hidden">
          <div
            ref={scrollRef}
            className="flex-1 space-y-4 overflow-y-auto px-3 py-4 sm:px-5"
            aria-live="polite"
          >
            {messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center px-4 text-center">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <MessageSquarePlus size={20} aria-hidden />
                </span>
                <h2 className="mt-3 text-sm font-semibold">Ask your policy a question</h2>
                <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                  Answers come only from this document. If the policy is silent, Insurio says so.
                </p>
                <div className="mt-4 flex w-full max-w-md flex-col gap-2">
                  {STARTERS.map((starter) => (
                    <button
                      key={starter}
                      type="button"
                      onClick={() => void send(starter)}
                      className="rounded-lg border border-border bg-white px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                    >
                      {starter}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  streaming={streamingId === message.id}
                  rating={ratings[message.id]}
                  copied={copied === message.id}
                  onCopy={() => void copy(message)}
                  onRate={(rating) => void rate(message, rating)}
                  isLastAssistant={
                    message.role === "assistant" &&
                    message.id === [...messages].reverse().find((item) => item.role === "assistant")?.id
                  }
                  onRegenerate={() => void regenerate()}
                  busy={busy}
                />
              ))
            )}
          </div>

          <div className="border-t border-border bg-white p-3 sm:p-4">
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void send(input);
              }}
              className="flex items-end gap-2"
            >
              <label htmlFor="question" className="sr-only">
                Your question
              </label>
              <textarea
                id="question"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void send(input);
                  }
                }}
                rows={1}
                placeholder="Ask about coverage, exclusions, waiting periods…"
                className="max-h-32 min-h-[42px] flex-1 resize-none rounded-lg border border-border bg-white px-3 py-2.5 text-sm placeholder:text-muted-foreground/70 focus:border-primary"
                disabled={busy}
              />
              <VoiceButton
                onTranscript={(text) => setInput((current) => `${current} ${text}`.trim())}
                disabled={busy}
              />
              {busy ? (
                <Button
                  variant="secondary"
                  size="icon"
                  onClick={() => abortRef.current?.abort()}
                  aria-label="Stop generating"
                  title="Stop generating"
                  className="h-[42px] w-[42px]"
                >
                  <Square size={14} aria-hidden />
                </Button>
              ) : (
                <Button
                  type="submit"
                  size="icon"
                  disabled={!input.trim()}
                  aria-label="Send question"
                  title="Send question"
                  className="h-[42px] w-[42px]"
                >
                  <ArrowUp size={16} aria-hidden />
                </Button>
              )}
            </form>
            <p className="mt-2 text-center text-[10px] text-muted-foreground">
              Informational analysis of your document, not insurance advice. Verify with your insurer.
            </p>
          </div>
        </Card>

        {hasAnswer && !busy ? (
          <div className="flex flex-wrap gap-2">
            {[
              "What is the sum insured?",
              "Are there sub-limits for specific treatments?",
              "What is the claim procedure?",
            ].map((followUp) => (
              <button
                key={followUp}
                type="button"
                onClick={() => void send(followUp)}
                className="rounded-full border border-border bg-white px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
              >
                {followUp}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  streaming,
  rating,
  copied,
  onCopy,
  onRate,
  isLastAssistant,
  onRegenerate,
  busy,
}: {
  message: Message;
  streaming: boolean;
  rating?: "up" | "down";
  copied: boolean;
  onCopy: () => void;
  onRate: (rating: "up" | "down") => void;
  isLastAssistant: boolean;
  onRegenerate: () => void;
  busy: boolean;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-xl rounded-br-sm bg-primary px-3.5 py-2.5 text-sm text-primary-foreground shadow-sm">
          {message.content}
        </div>
      </div>
    );
  }

  const failed = message.status === "failed";
  const evidence = [
    { key: "stated", label: "Stated in the policy", items: message.stated ?? [] },
    { key: "inferred", label: "Interpretation", items: message.inferred ?? [] },
    { key: "not_in_document", label: "Not in the document", items: message.not_in_document ?? [] },
  ].filter((group) => group.items.length > 0);

  return (
    <div className="flex justify-start">
      <div className="w-full max-w-[92%] rounded-xl rounded-bl-sm border border-border bg-white px-3.5 py-3 shadow-sm">
        {message.content ? (
          <Markdown>{message.content}</Markdown>
        ) : streaming ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner />
            Searching your policy…
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No answer was produced.</p>
        )}

        {failed ? (
          <p className="mt-2 rounded-md bg-danger/5 px-2 py-1.5 text-xs text-danger">
            {message.error_message ?? "This answer was interrupted."}
          </p>
        ) : null}

        {message.insufficient_evidence ? (
          <div className="mt-2">
            <Badge tone="warning">Not enough evidence in this policy</Badge>
          </div>
        ) : null}

        <CitationList citations={message.citations} />

        {evidence.length > 0 ? (
          <div className="mt-3 space-y-1.5 border-t border-border pt-3">
            {evidence.map((group) => (
              <details key={group.key} className="text-xs">
                <summary className="cursor-pointer font-medium text-muted-foreground">
                  {group.label} ({group.items.length})
                </summary>
                <ul className="mt-1 list-disc space-y-0.5 pl-4 text-muted-foreground">
                  {group.items.map((item, index) => (
                    <li key={`${group.key}-${index}`}>{item}</li>
                  ))}
                </ul>
              </details>
            ))}
          </div>
        ) : null}

        {!streaming && message.status === "complete" ? (
          <div className="mt-2.5 flex flex-wrap items-center gap-2 border-t border-border pt-2 text-[11px] text-muted-foreground">
            {message.confidence !== null ? (
              <span>{Math.round(message.confidence * 100)}% confidence</span>
            ) : null}
            {message.citation_status ? <span>citations: {message.citation_status}</span> : null}
            {message.latency_ms ? <span>{(message.latency_ms / 1000).toFixed(1)}s</span> : null}
            <div className="ml-auto flex items-center gap-1">
              <button
                type="button"
                onClick={onCopy}
                className="rounded p-1 hover:bg-muted hover:text-foreground"
                aria-label="Copy answer"
                title="Copy answer"
              >
                {copied ? <Check size={13} aria-hidden /> : <Copy size={13} aria-hidden />}
              </button>
              {isLastAssistant ? (
                <button
                  type="button"
                  onClick={onRegenerate}
                  disabled={busy}
                  className="rounded p-1 hover:bg-muted hover:text-foreground disabled:opacity-50"
                  aria-label="Regenerate answer"
                  title="Regenerate answer"
                >
                  <RefreshCw size={13} aria-hidden />
                </button>
              ) : null}
              <button
                type="button"
                onClick={() => onRate("up")}
                className={cn(
                  "rounded p-1 hover:bg-muted hover:text-foreground",
                  rating === "up" && "text-success",
                )}
                aria-label="Helpful"
                aria-pressed={rating === "up"}
                title="Helpful"
              >
                <ThumbsUp size={13} aria-hidden />
              </button>
              <button
                type="button"
                onClick={() => onRate("down")}
                className={cn(
                  "rounded p-1 hover:bg-muted hover:text-foreground",
                  rating === "down" && "text-danger",
                )}
                aria-label="Not helpful"
                aria-pressed={rating === "down"}
                title="Not helpful"
              >
                <ThumbsDown size={13} aria-hidden />
              </button>
            </div>
          </div>
        ) : null}

      </div>
    </div>
  );
}
