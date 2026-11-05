"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { MessagesSquare, Plus, Trash2 } from "lucide-react";

import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  PageHeader,
  Skeleton,
  Spinner,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { formatRelative } from "@/lib/format";
import type { Conversation, DocumentSummary } from "@/lib/types";

export default function ChatIndexPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[] | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null);
  const [documentId, setDocumentId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [conversationData, documentData] = await Promise.all([
        api.listConversations(1, 50),
        api.listDocuments(1, 50, "ready"),
      ]);
      setConversations(conversationData.items);
      setDocuments(documentData.items);
      setDocumentId((current) => current || documentData.items[0]?.id || "");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load conversations.");
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

  async function startConversation() {
    if (!documentId) return;
    setCreating(true);
    setError(null);
    try {
      const conversation = await api.createConversation(documentId);
      router.push(`/chat/${conversation.id}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not start a conversation.");
      setCreating(false);
    }
  }

  async function remove(conversation: Conversation) {
    if (!window.confirm(`Delete the conversation “${conversation.title}”?`)) return;
    try {
      await api.deleteConversation(conversation.id);
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not delete the conversation.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI chat"
        description="Evidence-grounded conversations about your policies. Each answer cites the pages it used."
      />

      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}

      <Card className="p-5">
        <h2 className="text-sm font-semibold">Start a new conversation</h2>
        {documents === null ? (
          <Skeleton className="mt-3 h-10" />
        ) : documents.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">
            No processed policies yet. Upload a PDF and wait for it to reach{" "}
            <span className="font-medium text-foreground">Ready</span>.{" "}
            <Link href="/documents" className="font-medium text-primary hover:underline">
              Go to documents
            </Link>
          </p>
        ) : (
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <label htmlFor="document" className="sr-only">
              Policy document
            </label>
            <select
              id="document"
              value={documentId}
              onChange={(event) => setDocumentId(event.target.value)}
              className="h-10 flex-1 rounded-lg border border-border bg-white px-3 text-sm"
            >
              {documents.map((document) => (
                <option key={document.id} value={document.id}>
                  {document.filename} · {document.page_count} pages
                </option>
              ))}
            </select>
            <Button onClick={() => void startConversation()} disabled={creating || !documentId}>
              {creating ? <Spinner /> : <Plus size={15} aria-hidden />}
              {creating ? "Starting…" : "New conversation"}
            </Button>
          </div>
        )}
      </Card>

      <div>
        <h2 className="mb-2 text-sm font-semibold">Conversation history</h2>
        {conversations === null ? (
          <div className="space-y-2">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        ) : conversations.length === 0 ? (
          <EmptyState
            icon={<MessagesSquare size={19} aria-hidden />}
            title="No conversations yet"
            description="Choose a processed policy above and ask your first question."
          />
        ) : (
          <Card className="divide-y divide-border">
            {conversations.map((conversation) => (
              <div key={conversation.id} className="flex items-center gap-3 p-4">
                <Link href={`/chat/${conversation.id}`} className="min-w-0 flex-1 group">
                  <p className="truncate text-sm font-medium group-hover:text-primary">
                    {conversation.title}
                  </p>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">
                    {conversation.document_filename ?? "Policy"} ·{" "}
                    {conversation.message_count ?? 0} messages ·{" "}
                    {formatRelative(conversation.last_activity_at ?? conversation.created_at)}
                  </p>
                  {conversation.preview ? (
                    <p className="mt-1 truncate text-xs text-muted-foreground/80">
                      {conversation.preview}
                    </p>
                  ) : null}
                </Link>
                <button
                  type="button"
                  onClick={() => void remove(conversation)}
                  className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-danger/10 hover:text-danger"
                  aria-label={`Delete conversation ${conversation.title}`}
                  title="Delete conversation"
                >
                  <Trash2 size={15} aria-hidden />
                </button>
              </div>
            ))}
          </Card>
        )}
      </div>
    </div>
  );
}
