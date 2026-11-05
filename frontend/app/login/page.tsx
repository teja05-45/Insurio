"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthShell } from "@/components/AuthShell";
import { Button, ErrorState, Field, Input, Spinner } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { signIn, user } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) router.replace("/dashboard");
  }, [user, router]);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(email, password);
      router.replace("/dashboard");
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Sign in failed. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      description="Sign in to your policy workspace."
      footer={
        <>
          New to Insurio?{" "}
          <Link href="/register" className="font-medium text-primary hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {error ? <ErrorState title="Could not sign in" message={error} /> : null}
        <Field label="Email" htmlFor="email">
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
          />
        </Field>
        <Field label="Password" htmlFor="password">
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Your password"
          />
        </Field>
        <div className="flex justify-end">
          <Link href="/forgot-password" className="text-xs text-muted-foreground hover:text-foreground">
            Forgot your password?
          </Link>
        </div>
        <Button type="submit" className="w-full justify-center" disabled={busy}>
          {busy ? <Spinner /> : null}
          {busy ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </AuthShell>
  );
}
