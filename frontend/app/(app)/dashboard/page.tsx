"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowRight,
  FileText,
  GitCompareArrows,
  MessagesSquare,
  Search,
  Sparkles,
} from "lucide-react";

import { UploadButton } from "@/components/UploadButton";
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  PageHeader,
  Skeleton,
  StatusBadge,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatRelative } from "@/lib/format";
import type { Conversation, DocumentSummary, Meta, Usage } from "@/lib/types";

const STATS = [
  { key: "documents", label: "Policies", icon: FileText, href: "/documents" },
  { key: "conversations", label: "Conversations", icon: MessagesSquare, href: "/chat" },
  { key: "questions", label: "Questions asked", icon: Search, href: "/chat" },
  { key: "comparisons", label: "Comparisons", icon: GitCompareArrows, href: "/compare" },
] as const;

export default function DashboardPage() {
  const { user } = useAuth();
  const [usage, setUsage] = useState<Usage | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null);
  const [conversations, setConversations] = useState<Conversation[] | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [usageData, documentData, conversationData, metaData] = await Promise.all([
        api.usage(),
        api.listDocuments(1, 5),
        api.listConversations(1, 5),
        api.meta(),
      ]);
      setUsage(usageData);
      setDocuments(documentData.items);
      setConversations(conversationData.items);
      setMeta(metaData);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load your workspace.");
    }
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      await Promise.resolve();
      if (active) await load();
    })();
    return () => {
      active = false;
    };
  }, [load]);

  const firstName = user?.full_name?.split(" ")[0] || "there";

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome back, ${firstName}`}
        description="Your policies, conversations and extracted coverage at a glance."
        actions={<UploadButton />}
      />

      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}

      {meta && !meta.llm_configured ? (
        <div className="rounded-xl border border-warning/30 bg-warning/5 px-4 py-3 text-sm">
          <p className="font-medium text-foreground">AI answers are not configured</p>
          <p className="mt-0.5 text-muted-foreground">
            Uploading, extraction, insights and comparison work. Set <code>GROQ_API_KEY</code> on
            the API to enable chat.
          </p>
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {STATS.map((stat) => (
          <Link key={stat.key} href={stat.href} className="group">
            <Card className="h-full p-4 transition-shadow group-hover:shadow-lift">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground">{stat.label}</span>
                <stat.icon size={15} className="text-muted-foreground/70" aria-hidden />
              </div>
              {usage ? (
                <p className="mt-2 text-2xl font-semibold tracking-tight">{usage[stat.key]}</p>
              ) : (
                <Skeleton className="mt-3 h-7 w-12" />
              )}
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Recent documents</h2>
            <Link
              href="/documents"
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              View all
              <ArrowRight size={12} aria-hidden />
            </Link>
          </div>
          <div className="mt-3">
            {documents === null ? (
              <div className="space-y-2">
                <Skeleton className="h-12" />
                <Skeleton className="h-12" />
                <Skeleton className="h-12" />
              </div>
            ) : documents.length === 0 ? (
              <EmptyState
                icon={<FileText size={19} aria-hidden />}
                title="No policies yet"
                description="Upload a PDF policy to extract coverage, exclusions and waiting periods."
                action={<UploadButton label="Upload your first policy" />}
              />
            ) : (
              <ul className="divide-y divide-border">
                {documents.map((document) => (
                  <li key={document.id}>
                    <Link
                      href={`/documents/${document.id}`}
                      className="flex items-center gap-3 py-3 transition-colors hover:text-primary"
                    >
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                        <FileText size={15} aria-hidden />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">
                          {document.filename}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {document.page_count} pages · {formatRelative(document.created_at)}
                        </span>
                      </span>
                      <StatusBadge status={document.status} />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Recent conversations</h2>
            <Link
              href="/chat"
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              View all
              <ArrowRight size={12} aria-hidden />
            </Link>
          </div>
          <div className="mt-3">
            {conversations === null ? (
              <div className="space-y-2">
                <Skeleton className="h-12" />
                <Skeleton className="h-12" />
              </div>
            ) : conversations.length === 0 ? (
              <EmptyState
                icon={<MessagesSquare size={19} aria-hidden />}
                title="No conversations yet"
                description="Ask a question about a processed policy to start one."
                action={
                  <Link
                    href="/chat"
                    className="inline-flex h-9 items-center rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground"
                  >
                    Start a chat
                  </Link>
                }
              />
            ) : (
              <ul className="divide-y divide-border">
                {conversations.map((conversation) => (
                  <li key={conversation.id}>
                    <Link
                      href={`/chat/${conversation.id}`}
                      className="block py-3 transition-colors hover:text-primary"
                    >
                      <span className="flex items-center justify-between gap-2">
                        <span className="truncate text-sm font-medium">{conversation.title}</span>
                        <span className="shrink-0 text-[11px] text-muted-foreground">
                          {formatRelative(conversation.last_activity_at ?? conversation.created_at)}
                        </span>
                      </span>
                      <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                        {conversation.document_filename ?? "Policy"} ·{" "}
                        {conversation.message_count ?? 0} messages
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Card>
      </div>

      <Card className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Sparkles size={17} aria-hidden />
          </span>
          <div>
            <h2 className="text-sm font-semibold">Compare coverage before you buy</h2>
            <p className="mt-0.5 text-sm text-muted-foreground">
              Put two policies side by side on sum insured, exclusions and waiting periods.
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge tone="primary">2–5 policies</Badge>
          <Link
            href="/compare"
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-white px-3 text-sm font-medium hover:bg-muted"
          >
            Open compare
            <ArrowRight size={14} aria-hidden />
          </Link>
        </div>
      </Card>
    </div>
  );
}
