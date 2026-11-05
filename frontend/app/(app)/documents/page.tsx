"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { FileText, MessagesSquare, Trash2 } from "lucide-react";

import { UploadButton } from "@/components/UploadButton";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  PageHeader,
  Skeleton,
  StatusBadge,
  cn,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/format";
import type { DocumentSummary } from "@/lib/types";

const FILTERS = [
  { value: "", label: "All" },
  { value: "ready", label: "Ready" },
  { value: "processing", label: "Processing" },
  { value: "failed", label: "Failed" },
];

export default function DocumentsPage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const response = await api.listDocuments(1, 50, filter || undefined);
      setDocuments(response.items);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load documents.");
    }
  }, [filter]);

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

  async function startChat(documentId: string) {
    setBusyId(documentId);
    setError(null);
    try {
      const conversation = await api.createConversation(documentId);
      router.push(`/chat/${conversation.id}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not start a conversation.");
      setBusyId(null);
    }
  }

  async function remove(document: DocumentSummary) {
    if (!window.confirm(`Delete “${document.filename}” and all of its conversations?`)) return;
    setBusyId(document.id);
    setError(null);
    try {
      await api.deleteDocument(document.id);
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not delete the document.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Documents"
        description="Uploaded policies, extraction status, and the evidence behind every insight."
        actions={<UploadButton />}
      />

      <div className="flex flex-wrap items-center gap-1.5">
        {FILTERS.map((item) => (
          <button
            key={item.value}
            type="button"
            onClick={() => {
              setFilter(item.value);
              setDocuments(null);
            }}
            aria-pressed={filter === item.value}
            className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
              filter === item.value
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {item.label}
          </button>
        ))}
      </div>

      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}

      {documents === null ? (
        <div className="space-y-2">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : documents.length === 0 ? (
        <EmptyState
          icon={<FileText size={19} aria-hidden />}
          title={filter ? "No documents in this state" : "No documents yet"}
          description={
            filter
              ? "Try a different filter, or upload another policy."
              : "Upload an insurance policy PDF to extract its coverage and start asking questions."
          }
          action={<UploadButton label="Upload a policy" />}
        />
      ) : (
        <Card className="divide-y divide-border overflow-hidden">
          {documents.map((document) => (
            <div
              key={document.id}
              className="flex flex-col gap-3 p-4 transition-colors hover:bg-muted/30 sm:flex-row sm:items-center"
            >
              <Link
                href={`/documents/${document.id}`}
                className="flex min-w-0 flex-1 items-center gap-3"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  <FileText size={16} aria-hidden />
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium">{document.filename}</span>
                  <span className="mt-0.5 block text-xs text-muted-foreground">
                    {formatBytes(document.size_bytes)} · {document.page_count} pages ·{" "}
                    {document.chunk_count} chunks · {formatDate(document.created_at)}
                  </span>
                  {document.error_message ? (
                    <span className="mt-1 block text-xs text-danger">{document.error_message}</span>
                  ) : null}
                </span>
              </Link>

              <div className="flex items-center gap-2 sm:shrink-0">
                <StatusBadge status={document.status} />
                {document.status === "ready" ? (
                  <>
                    <Link
                      href={`/insights/${document.id}`}
                      className="inline-flex h-8 items-center rounded-lg border border-border bg-white px-2.5 text-xs font-medium hover:bg-muted"
                    >
                      Insights
                    </Link>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => void startChat(document.id)}
                      disabled={busyId === document.id}
                    >
                      <MessagesSquare size={13} aria-hidden />
                      Chat
                    </Button>
                  </>
                ) : null}
                <button
                  type="button"
                  onClick={() => void remove(document)}
                  disabled={busyId === document.id}
                  className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-danger/10 hover:text-danger disabled:opacity-50"
                  aria-label={`Delete ${document.filename}`}
                  title="Delete document"
                >
                  <Trash2 size={15} aria-hidden />
                </button>
              </div>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
