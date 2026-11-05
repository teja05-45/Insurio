"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Check, FileText, GitCompareArrows, Trash2 } from "lucide-react";

import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  PageHeader,
  Skeleton,
  Spinner,
  cn,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Comparison, ComparisonField, DocumentSummary } from "@/lib/types";

export default function ComparePage() {
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null);
  const [comparisons, setComparisons] = useState<Comparison[] | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [active, setActive] = useState<Comparison | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [documentData, comparisonData] = await Promise.all([
        api.listDocuments(1, 50, "ready"),
        api.listComparisons(),
      ]);
      setDocuments(documentData.items);
      setComparisons(comparisonData.items);
      setActive((current) => current ?? comparisonData.items[0] ?? null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load comparison data.");
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

  function toggle(documentId: string) {
    setSelected((current) => {
      if (current.includes(documentId)) return current.filter((id) => id !== documentId);
      if (current.length >= 5) return current;
      return [...current, documentId];
    });
  }

  async function create() {
    if (selected.length < 2) {
      setError("Select at least two policies to compare.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const comparison = await api.createComparison(selected);
      setComparisons((current) => [comparison, ...(current ?? [])]);
      setActive(comparison);
      setSelected([]);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not create the comparison.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(comparison: Comparison) {
    if (!window.confirm(`Delete “${comparison.title}”?`)) return;
    try {
      await api.deleteComparison(comparison.id);
      setComparisons((current) => (current ?? []).filter((item) => item.id !== comparison.id));
      setActive((current) => (current?.id === comparison.id ? null : current));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not delete the comparison.");
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Compare policies"
        description="Field-by-field comparison built from extracted values, with the source quote behind each one."
      />

      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}

      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold">Select policies</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Choose two to five processed policies. {selected.length} selected.
            </p>
          </div>
          <Button onClick={() => void create()} disabled={busy || selected.length < 2}>
            {busy ? <Spinner /> : <GitCompareArrows size={15} aria-hidden />}
            {busy ? "Comparing…" : "Compare"}
          </Button>
        </div>

        {documents === null ? (
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <Skeleton className="h-12" />
            <Skeleton className="h-12" />
          </div>
        ) : documents.length < 2 ? (
          <p className="mt-3 text-sm text-muted-foreground">
            You need at least two processed policies.{" "}
            <Link href="/documents" className="font-medium text-primary hover:underline">
              Upload another policy
            </Link>
            .
          </p>
        ) : (
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {documents.map((document) => {
              const isSelected = selected.includes(document.id);
              return (
                <button
                  key={document.id}
                  type="button"
                  onClick={() => toggle(document.id)}
                  aria-pressed={isSelected}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors",
                    isSelected
                      ? "border-primary bg-primary/5"
                      : "border-border bg-white hover:border-primary/40",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-5 w-5 shrink-0 items-center justify-center rounded border",
                      isSelected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border",
                    )}
                  >
                    {isSelected ? <Check size={13} aria-hidden /> : null}
                  </span>
                  <span className="min-w-0 flex-1 truncate">{document.filename}</span>
                  <span className="shrink-0 text-[11px] text-muted-foreground">
                    {document.page_count}p
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </Card>

      {comparisons && comparisons.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {comparisons.map((comparison) => (
            <button
              key={comparison.id}
              type="button"
              onClick={() => setActive(comparison)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs transition-colors",
                active?.id === comparison.id
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-white text-muted-foreground hover:text-foreground",
              )}
            >
              {comparison.title}
            </button>
          ))}
        </div>
      ) : null}

      {active ? (
        <Card className="overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold">{active.title}</h2>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {active.summary.fields_compared} fields compared ·{" "}
                {active.summary.differences} differences · created {formatDate(active.created_at)}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge tone={active.summary.differences > 0 ? "warning" : "success"}>
                {active.summary.differences > 0 ? "Policies differ" : "Values match"}
              </Badge>
              <button
                type="button"
                onClick={() => void remove(active)}
                className="rounded-md p-2 text-muted-foreground hover:bg-danger/10 hover:text-danger"
                aria-label="Delete comparison"
                title="Delete comparison"
              >
                <Trash2 size={15} aria-hidden />
              </button>
            </div>
          </div>

          {active.fields.length === 0 ? (
            <div className="p-4">
              <EmptyState
                icon={<GitCompareArrows size={19} aria-hidden />}
                title="No comparable fields"
                description="The selected policies share no extracted fields."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] border-collapse text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/40 text-left">
                    <th className="w-48 px-4 py-2 text-xs font-semibold text-muted-foreground">
                      Field
                    </th>
                    {active.documents.map((document) => (
                      <th key={document.id} className="px-4 py-2 text-xs font-semibold">
                        <span className="flex items-center gap-1.5">
                          <FileText size={12} className="text-muted-foreground" aria-hidden />
                          <span className="truncate">{document.filename}</span>
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {active.fields.map((field) => (
                    <ComparisonRow key={field.key} field={field} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      ) : comparisons && comparisons.length === 0 ? (
        <EmptyState
          icon={<GitCompareArrows size={19} aria-hidden />}
          title="No comparisons yet"
          description="Select two processed policies above to build your first comparison."
        />
      ) : null}
    </div>
  );
}

function ComparisonRow({ field }: { field: ComparisonField }) {
  return (
    <tr className="border-b border-border align-top last:border-b-0">
      <th scope="row" className="px-4 py-3 text-left text-xs font-medium">
        <span className="flex flex-col gap-1">
          {field.label}
          {field.differs ? (
            <span className="w-fit rounded-full bg-warning/10 px-1.5 py-0.5 text-[10px] font-medium text-warning">
              differs
            </span>
          ) : (
            <span className="w-fit rounded-full bg-success/10 px-1.5 py-0.5 text-[10px] font-medium text-success">
              same
            </span>
          )}
        </span>
      </th>
      {field.values.map((value) => (
        <td key={value.document_id} className="px-4 py-3 text-xs">
          {value.status === "missing" ? (
            <span className="text-muted-foreground">Not stated</span>
          ) : (
            <div className="space-y-1.5">
              <p className="whitespace-pre-wrap font-medium text-foreground">{value.value}</p>
              {value.page ? (
                <p className="text-[11px] text-muted-foreground">Page {value.page}</p>
              ) : null}
              {value.quote ? (
                <details>
                  <summary className="cursor-pointer text-[11px] text-primary">Evidence</summary>
                  <blockquote className="mt-1 border-l-2 border-border pl-2 text-[11px] leading-relaxed text-muted-foreground">
                    &ldquo;{value.quote}&rdquo;
                  </blockquote>
                </details>
              ) : null}
            </div>
          )}
        </td>
      ))}
    </tr>
  );
}
