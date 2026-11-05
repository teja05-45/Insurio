"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Sparkles } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  PageHeader,
  Skeleton,
  StatusBadge,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { Insight, InsightField } from "@/lib/types";

const CATEGORY_TITLES: Record<string, string> = {
  policy: "Policy details",
  coverage: "Coverage and limits",
  conditions: "Conditions and waiting periods",
  exclusions: "Exclusions",
  claims: "Claims",
};

const CATEGORY_ORDER = ["policy", "coverage", "conditions", "exclusions", "claims"];

export default function InsightsPage() {
  const { id } = useParams<{ id: string }>();
  const [insight, setInsight] = useState<Insight | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setInsight(await api.insights(id));
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Insights are not available for this document.",
      );
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

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      setInsight(await api.refreshInsights(id));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not refresh the insights.");
    } finally {
      setBusy(false);
    }
  }

  if (error && !insight) {
    return <ErrorState title="Insights unavailable" message={error} onRetry={() => void load()} />;
  }

  if (!insight) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-72" />
        <Skeleton className="h-32" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  const counts = {
    found: insight.fields.filter((field) => field.status === "found").length,
    ambiguous: insight.fields.filter((field) => field.status === "ambiguous").length,
    missing: insight.fields.filter((field) => field.status === "missing").length,
  };
  const chartData = [
    { name: "Found", count: counts.found },
    { name: "Ambiguous", count: counts.ambiguous },
    { name: "Not stated", count: counts.missing },
  ];

  return (
    <div className="space-y-5">
      <PageHeader
        title="Policy intelligence"
        description={`Structured facts extracted from ${insight.filename}. Every value carries its page and source quote.`}
        actions={
          <>
            <Button variant="secondary" onClick={() => void refresh()} disabled={busy}>
              <RefreshCw size={14} className={busy ? "animate-spin" : undefined} aria-hidden />
              {busy ? "Re-extracting…" : "Re-extract"}
            </Button>
            <Link
              href={`/documents/${id}`}
              className="inline-flex h-10 items-center rounded-lg border border-border bg-white px-4 text-sm font-medium hover:bg-muted"
            >
              Open workspace
            </Link>
          </>
        }
      />

      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}

      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Extraction coverage</h2>
            <Badge tone="primary">
              {insight.extraction_method === "rules+llm" ? "Rules + AI" : "Rules-based"}
            </Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {counts.found} of {insight.fields.length} fields found in the document.
          </p>
          <div className="mt-2 h-[170px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid horizontal={false} stroke="hsl(214 32% 91%)" />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} stroke="#94a3b8" />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={78}
                  tick={{ fontSize: 11 }}
                  stroke="#94a3b8"
                />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "hsl(214 32% 91%)" }}
                />
                <Bar dataKey="count" fill="hsl(221 83% 53%)" radius={[0, 4, 4, 0]} barSize={16} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="flex flex-col justify-center p-5">
          <div className="flex items-start gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Sparkles size={17} aria-hidden />
            </span>
            <div>
              <h2 className="text-sm font-semibold">Missing information is information</h2>
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                Fields marked <span className="font-medium text-foreground">Not stated</span> are
                absent from this document. Insurio never fills them from general knowledge — ask
                the insurer before relying on them.
              </p>
            </div>
          </div>
          <dl className="mt-5 grid grid-cols-3 gap-2 text-center">
            {(
              [
                ["Found", counts.found, "text-success"],
                ["Ambiguous", counts.ambiguous, "text-warning"],
                ["Not stated", counts.missing, "text-muted-foreground"],
              ] as const
            ).map(([label, value, tone]) => (
              <div key={label} className="rounded-lg border border-border bg-background px-2 py-3">
                <dt className="text-[11px] text-muted-foreground">{label}</dt>
                <dd className={`mt-0.5 text-lg font-semibold ${tone}`}>{value}</dd>
              </div>
            ))}
          </dl>
        </Card>
      </div>

      {insight.fields.every((field) => field.status === "missing") ? (
        <EmptyState
          icon={<Sparkles size={19} aria-hidden />}
          title="No structured fields were found"
          description="The document may be scanned, use unusual formatting, or not be a policy document."
        />
      ) : null}

      <div className="space-y-6">
        {CATEGORY_ORDER.map((category) => {
          const fields = insight.fields.filter((field) => field.category === category);
          if (fields.length === 0) return null;
          return (
            <section key={category}>
              <h2 className="mb-2 text-sm font-semibold">
                {CATEGORY_TITLES[category] ?? category}
              </h2>
              <div className="grid gap-3 sm:grid-cols-2">
                {fields.map((field) => (
                  <FieldCard key={field.key} field={field} />
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}

function FieldCard({ field }: { field: InsightField }) {
  return (
    <Card className="flex h-full flex-col p-4">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {field.label}
        </h3>
        <StatusBadge status={field.status} />
      </div>
      {field.status === "missing" ? (
        <p className="mt-2 text-sm text-muted-foreground">
          Not stated in this document. Confirm with your insurer.
        </p>
      ) : (
        <>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-foreground">
            {field.value}
          </p>
          {field.quote ? (
            <blockquote className="mt-3 border-l-2 border-border pl-3 text-xs leading-relaxed text-muted-foreground">
              &ldquo;{field.quote}&rdquo;
            </blockquote>
          ) : null}
          <div className="mt-auto flex items-center gap-3 pt-3 text-[11px] text-muted-foreground">
            {field.page ? <span>Page {field.page}</span> : null}
            <span className="flex items-center gap-1.5">
              Confidence
              <span className="inline-block h-1.5 w-16 overflow-hidden rounded-full bg-muted">
                <span
                  className="block h-full rounded-full bg-primary"
                  style={{ width: `${Math.round(field.confidence * 100)}%` }}
                />
              </span>
              {Math.round(field.confidence * 100)}%
            </span>
          </div>
        </>
      )}
    </Card>
  );
}
