"use client";

import Link from "next/link";
import { useState } from "react";

import { AuthShell } from "@/components/AuthShell";
import { Button, ErrorState, Field, Input, Spinner } from "@/components/ui";
import { ApiError, api } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function requestReset(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = await api.forgotPassword(email);
      setMessage(response.message);
      setResetToken(response.reset_token);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Request failed. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function completeReset(event: React.FormEvent) {
    event.preventDefault();
    if (!resetToken) return;
    if (newPassword.length < 10) {
      setError("Password must be at least 10 characters.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.resetPassword(resetToken, newPassword);
      setDone(true);
      setResetToken(null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Reset failed. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Reset your password"
      description="We will create a single-use reset link for your account."
      footer={
        <Link href="/login" className="font-medium text-primary hover:underline">
          Back to sign in
        </Link>
      }
    >
      {done ? (
        <div className="rounded-xl border border-success/30 bg-success/5 p-4 text-sm">
          <p className="font-medium text-foreground">Password updated</p>
          <p className="mt-1 text-muted-foreground">
            Your other sessions were signed out. You can now sign in with the new password.
          </p>
          <Link
            href="/login"
            className="mt-3 inline-flex h-9 items-center rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground"
          >
            Sign in
          </Link>
        </div>
      ) : resetToken ? (
        <form onSubmit={completeReset} className="space-y-4" noValidate>
          <div className="rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-xs text-muted-foreground">
            Email delivery is not configured in this build, so the reset token is shown here
            directly. Production deployments must send it by email.
          </div>
          {error ? <ErrorState message={error} /> : null}
          <Field label="Reset token" htmlFor="reset_token">
            <Input id="reset_token" value={resetToken} readOnly className="font-mono text-xs" />
          </Field>
          <Field label="New password" htmlFor="new_password" hint="At least 10 characters.">
            <Input
              id="new_password"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              required
            />
          </Field>
          <Button type="submit" className="w-full justify-center" disabled={busy}>
            {busy ? <Spinner /> : null}
            Set new password
          </Button>
        </form>
      ) : (
        <form onSubmit={requestReset} className="space-y-4" noValidate>
          {error ? <ErrorState message={error} /> : null}
          {message ? (
            <div className="rounded-lg border border-border bg-muted px-3 py-2 text-sm text-muted-foreground">
              {message}
            </div>
          ) : null}
          <Field label="Email" htmlFor="email">
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
            />
          </Field>
          <Button type="submit" className="w-full justify-center" disabled={busy}>
            {busy ? <Spinner /> : null}
            Create reset link
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
