import { Quote } from "lucide-react";

import { formatPages } from "@/lib/format";
import type { Citation } from "@/lib/types";

export function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-3 border-t border-border pt-3">
      <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        Sources from your policy
      </p>
      <ul className="space-y-1">
        {citations.map((citation, index) => (
          <li key={`${citation.source_id}-${index}`}>
            <details className="group rounded-lg border border-border bg-white">
              <summary className="flex cursor-pointer list-none items-center gap-2 px-2.5 py-2 text-xs">
                <span className="rounded bg-primary/10 px-1.5 py-0.5 font-semibold text-primary">
                  {citation.source_id}
                </span>
                <span className="text-muted-foreground">
                  {formatPages(citation.page_start, citation.page_end)}
                </span>
                <Quote size={12} className="ml-auto text-muted-foreground" aria-hidden />
              </summary>
              <blockquote className="border-t border-border px-3 py-2 text-xs leading-relaxed text-muted-foreground">
                &ldquo;{citation.quote}&rdquo;
              </blockquote>
            </details>
          </li>
        ))}
      </ul>
    </div>
  );
}
