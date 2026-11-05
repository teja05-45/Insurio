"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Download,
  ExternalLink,
  FileText,
  MessagesSquare,
  Sparkles,
  Trash2,
} from "lucide-react";

import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Skeleton,
  StatusBadge,
  cn,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/format";
import type { DocumentDetail, DocumentPage } from "@/lib/types";

type Tab = "text" | "pdf";

export default function DocumentWorkspacePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [pages, setPages] = useState<DocumentPage[]>([]);
  const [tab, setTab] = useState<Tab>("text");
  const [selectedPage, setSelectedPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const pdfUrlRef = useRef<string | null>(null);

  const load = useCallback(async () => {
    try {
      const detail = await api.getDocument(id);
      setDocument(detail);
      if (detail.status === "ready") {
        const loadedPages = await api.documentPages(id);
        setPages(loadedPages);
        setSelectedPage((current) =>
          loadedPages.some((page) => page.page_number === current)
            ? current
            : (loadedPages[0]?.page_number ?? 1),
        );
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load the document.");
    }
  }, [id]);

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

  useEffect(() => {
    if (!document || document.status === "ready" || document.status === "failed") return;
    const timer = window.setInterval(() => void load(), 2500);
    return () => window.clearInterval(timer);
  }, [document, load]);

  useEffect(() => {
    if (document?.status !== "ready") return;
    let active = true;
    api
      .documentFile(id)
      .then((blob) => {
        if (!active) return;
        const url = URL.createObjectURL(blob);
        pdfUrlRef.current = url;
        setPdfUrl(url);
      })
      .catch(() => {
        if (active) setPdfError("The PDF preview could not be loaded. Try downloading it.");
      });
    return () => {
      active = false;
      if (pdfUrlRef.current) URL.revokeObjectURL(pdfUrlRef.current);
      pdfUrlRef.current = null;
      setPdfUrl(null);
    };
  }, [document?.status, id]);

  async function startChat() {
    if (!document) return;
    setBusy(true);
    setError(null);
    try {
      const conversation = await api.createConversation(document.id);
      router.push(`/chat/${conversation.id}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not start a conversation.");
      setBusy(false);
    }
  }

  async function download() {
    if (!document) return;
    try {
      const blob = await api.documentFile(document.id);
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = document.filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("The download failed. Please try again.");
    }
  }

  async function remove() {
    if (!document) return;
    if (!window.confirm(`Delete “${document.filename}” and all of its conversations?`)) return;
    setBusy(true);
    try {
      await api.deleteDocument(document.id);
      router.push("/documents");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not delete the document.");
      setBusy(false);
    }
  }

  if (!document && error) {
    return <ErrorState title="Document unavailable" message={error} onRetry={() => void load()} />;
  }

  if (!document) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-24" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  const currentPage = pages.find((page) => page.page_number === selectedPage);
  const pageNumbers = pages.map((page) => page.page_number);
  const currentIndex = pageNumbers.indexOf(selectedPage);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <Link href="/documents" className="text-xs text-muted-foreground hover:text-foreground">
            ← Documents
          </Link>
          <h1 className="mt-1 flex flex-wrap items-center gap-2 text-xl font-semibold tracking-tight">
            <span className="truncate">{document.filename}</span>
            <StatusBadge status={document.status} />
          </h1>
          <p className="mt-1 text-xs text-muted-foreground">
            {formatBytes(document.size_bytes)} · {document.page_count} pages ·{" "}
            {document.chunk_count} chunks · uploaded {formatDate(document.created_at)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {document.status === "ready" ? (
            <>
              <Link
                href={`/insights/${document.id}`}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-white px-3 text-sm font-medium hover:bg-muted"
              >
                <Sparkles size={14} aria-hidden />
                Insights
              </Link>
              <Button onClick={() => void startChat()} disabled={busy}>
                <MessagesSquare size={15} aria-hidden />
                Ask questions
              </Button>
            </>
          ) : null}
          <Button variant="secondary" size="icon" onClick={() => void download()} title="Download PDF">
            <Download size={15} aria-hidden />
            <span className="sr-only">Download PDF</span>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => void remove()}
            disabled={busy}
            title="Delete document"
            className="hover:bg-danger/10 hover:text-danger"
          >
            <Trash2 size={15} aria-hidden />
            <span className="sr-only">Delete document</span>
          </Button>
        </div>
      </div>

      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}

      {document.status === "failed" ? (
        <ErrorState
          title="Processing failed"
          message={document.error_message ?? "The document could not be processed."}
        />
      ) : null}

      {document.status !== "ready" && document.status !== "failed" ? (
        <Card className="p-5">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">
              {document.latest_job?.detail || "Preparing your document"}
            </span>
            <Badge tone="warning">{document.latest_job?.progress ?? 0}%</Badge>
          </div>
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${document.latest_job?.progress ?? 5}%` }}
            />
          </div>
          <p className="mt-3 text-xs text-muted-foreground" role="status" aria-live="polite">
            Extracting text, building chunks and policy insights. This page updates automatically.
          </p>
        </Card>
      ) : null}

      {document.status === "ready" ? (
        <div className="space-y-3">
          <div className="flex items-center gap-1 border-b border-border">
            {(
              [
                ["text", "Extracted text"],
                ["pdf", "PDF"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setTab(value)}
                aria-selected={tab === value}
                role="tab"
                className={cn(
                  "-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                  tab === value
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground",
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {tab === "text" ? (
            <Card className="overflow-hidden">
              {pages.length === 0 ? (
                <div className="p-6">
                  <EmptyState
                    icon={<FileText size={19} aria-hidden />}
                    title="No extracted pages"
                    description="This document produced no readable page text."
                  />
                </div>
              ) : (
                <div className="grid lg:grid-cols-[200px_1fr]">
                  <div className="max-h-[520px] overflow-y-auto border-b border-border bg-muted/30 p-2 lg:border-b-0 lg:border-r">
                    <p className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                      Pages
                    </p>
                    <ul className="space-y-0.5">
                      {pages.map((page) => (
                        <li key={page.page_number}>
                          <button
                            type="button"
                            onClick={() => setSelectedPage(page.page_number)}
                            className={cn(
                              "flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-xs transition-colors",
                              selectedPage === page.page_number
                                ? "bg-white font-medium text-primary shadow-sm"
                                : "text-muted-foreground hover:bg-white/70 hover:text-foreground",
                            )}
                          >
                            <span>Page {page.page_number}</span>
                            <span className="text-[10px]">
                              {page.extraction_method === "ocr" ? "OCR" : `${page.char_count}c`}
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="flex min-h-[320px] flex-col">
                    <div className="flex items-center justify-between border-b border-border px-4 py-2">
                      <span className="text-xs text-muted-foreground">
                        Page {selectedPage} of {pages.length}
                      </span>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() =>
                            setSelectedPage(pageNumbers[Math.max(0, currentIndex - 1)])
                          }
                          disabled={currentIndex <= 0}
                          aria-label="Previous page"
                        >
                          <ChevronLeft size={15} aria-hidden />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() =>
                            setSelectedPage(
                              pageNumbers[Math.min(pageNumbers.length - 1, currentIndex + 1)],
                            )
                          }
                          disabled={currentIndex >= pageNumbers.length - 1}
                          aria-label="Next page"
                        >
                          <ChevronRight size={15} aria-hidden />
                        </Button>
                      </div>
                    </div>
                    <div className="max-h-[460px] flex-1 overflow-y-auto px-5 py-4">
                      <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground">
                        {currentPage?.text || "No text was extracted from this page."}
                      </pre>
                    </div>
                  </div>
                </div>
              )}
            </Card>
          ) : (
            <Card className="overflow-hidden">
              {pdfError ? (
                <div className="p-4">
                  <ErrorState title="Preview unavailable" message={pdfError} />
                </div>
              ) : pdfUrl ? (
                <div className="flex flex-col">
                  <div className="flex items-center justify-between border-b border-border px-4 py-2">
                    <span className="text-xs text-muted-foreground">
                      Rendered from your original upload
                    </span>
                    <a
                      href={pdfUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                    >
                      Open in new tab
                      <ExternalLink size={12} aria-hidden />
                    </a>
                  </div>
                  <iframe
                    src={pdfUrl}
                    title={`PDF preview of ${document.filename}`}
                    className="h-[620px] w-full bg-muted"
                  />
                </div>
              ) : (
                <div className="space-y-2 p-4">
                  <Skeleton className="h-[400px]" />
                </div>
              )}
            </Card>
          )}
        </div>
      ) : null}
    </div>
  );
}
