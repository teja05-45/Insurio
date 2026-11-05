"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { Upload } from "lucide-react";

import { ApiError, api } from "@/lib/api";
import { Button, Spinner } from "./ui";

export function UploadButton({
  label = "Upload policy",
  variant = "primary",
  maxSizeMb = 20,
}: {
  label?: string;
  variant?: "primary" | "secondary";
  maxSizeMb?: number;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf") {
      setError("Only PDF files are accepted.");
      return;
    }
    if (file.size > maxSizeMb * 1024 * 1024) {
      setError(`The file must be smaller than ${maxSizeMb} MB.`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const document = await api.uploadDocument(file);
      router.push(`/documents/${document.id}`);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "The upload failed. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-1.5">
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="sr-only"
        onChange={onSelect}
        tabIndex={-1}
        aria-hidden="true"
      />
      <Button
        variant={variant}
        onClick={() => inputRef.current?.click()}
        disabled={busy}
        aria-busy={busy}
      >
        {busy ? <Spinner /> : <Upload size={15} aria-hidden />}
        {busy ? "Uploading…" : label}
      </Button>
      {error ? (
        <p className="text-xs text-danger" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
