"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthShell } from "@/components/AuthShell";
import { Button, ErrorState, Field, Input, Spinner } from "@/components/ui";
import { ApiError, api, setTokens } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { user, setUser } = useAuth();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) router.replace("/dashboard");
  }, [user, router]);

  function validate(): string | null {
    if (password.length < 10) return "Password must be at least 10 characters.";
    if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      return "Password must contain at least one letter and one number.";
    }
    return null;
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await api.register({ email, password, full_name: fullName });
      setTokens(response.access_token, response.refresh_token);
      setUser(response.user);
      router.replace("/dashboard");
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Registration failed. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Create your workspace"
      description="Upload a policy and start asking evidence-backed questions."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {error ? <ErrorState title="Could not create account" message={error} /> : null}
        <Field label="Full name" htmlFor="full_name">
          <Input
            id="full_name"
            name="full_name"
            autoComplete="name"
            required
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            placeholder="Asha Rao"
          />
        </Field>
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
        <Field
          label="Password"
          htmlFor="password"
          hint="At least 10 characters, with one letter and one number."
        >
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Choose a strong password"
          />
        </Field>
        <Button type="submit" className="w-full justify-center" disabled={busy}>
          {busy ? <Spinner /> : null}
          {busy ? "Creating account…" : "Create account"}
        </Button>
        <p className="text-center text-[11px] leading-relaxed text-muted-foreground">
          Insurio provides informational policy analysis, not insurance or legal advice.
        </p>
      </form>
    </AuthShell>
  );
}
