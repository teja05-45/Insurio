const BYTE_UNITS = ["B", "KB", "MB", "GB"];

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), BYTE_UNITS.length - 1);
  const value = bytes / 1024 ** exponent;
  return `${value.toFixed(exponent === 0 ? 0 : 1)} ${BYTE_UNITS[exponent]}`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatRelative(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value).getTime();
  if (Number.isNaN(date)) return "—";
  const seconds = Math.round((date - Date.now()) / 1000);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  const ranges: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31536000],
    ["month", 2592000],
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  for (const [unit, size] of ranges) {
    if (Math.abs(seconds) >= size) return formatter.format(Math.round(seconds / size), unit);
  }
  return "just now";
}

export function formatPages(start: number, end: number): string {
  return start === end ? `page ${start}` : `pages ${start}–${end}`;
}

export function confidenceLabel(confidence: number | null | undefined): string {
  if (confidence === null || confidence === undefined) return "—";
  return `${Math.round(confidence * 100)}% confidence`;
}

export function initials(name: string, email: string): string {
  const source = name.trim() || email;
  const parts = source.split(/[\s@.]+/).filter(Boolean);
  return (parts[0]?.[0] ?? "?").concat(parts[1]?.[0] ?? "").toUpperCase();
}

export type Tone = "neutral" | "primary" | "success" | "warning" | "danger";

export function statusTone(status: string): Tone {
  switch (status) {
    case "ready":
    case "found":
      return "success";
    case "processing":
    case "streaming":
    case "ambiguous":
      return "warning";
    case "failed":
      return "danger";
    case "queued":
      return "neutral";
    default:
      return "neutral";
  }
}

export const STATUS_LABEL: Record<string, string> = {
  queued: "Queued",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
  streaming: "Writing",
  complete: "Complete",
  found: "Found",
  ambiguous: "Ambiguous",
  missing: "Not stated",
};
