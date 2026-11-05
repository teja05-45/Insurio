"use client";

import { useEffect, useState } from "react";
import { KeyRound, ShieldAlert, Trash2 } from "lucide-react";

import {
  Badge,
  Button,
  Card,
  ErrorState,
  Field,
  Input,
  PageHeader,
  Spinner,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/format";
import type { Meta, Usage } from "@/lib/types";

type Session = {
  id: string;
  created_at: string;
  expires_at: string;
  user_agent: string;
  ip_address: string;
};

export default function SettingsPage() {
  const { user, setUser, signOut } = useAuth();
  // RequireAuth guarantees a user is present before this page mounts.
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [savingPassword, setSavingPassword] = useState(false);

  const [sessions, setSessions] = useState<Session[] | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);

  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      await Promise.resolve();
      if (!active) return;
      const [sessionList, usageData, metaData] = await Promise.all([
        api.sessions().catch(() => [] as Session[]),
        api.usage().catch(() => null),
        api.meta().catch(() => null),
      ]);
      if (!active) return;
      setSessions(sessionList);
      setUsage(usageData);
      setMeta(metaData);
    })();
    return () => {
      active = false;
    };
  }, []);

  if (!user) return null;

  async function saveProfile(event: React.FormEvent) {
    event.preventDefault();
    setSavingProfile(true);
    setProfileError(null);
    setProfileMessage(null);
    try {
      const updated = await api.updateProfile(fullName);
      setUser(updated);
      setProfileMessage("Profile updated.");
    } catch (caught) {
      setProfileError(caught instanceof ApiError ? caught.message : "Could not update profile.");
    } finally {
      setSavingProfile(false);
    }
  }

  async function savePassword(event: React.FormEvent) {
    event.preventDefault();
    setSavingPassword(true);
    setPasswordError(null);
    setPasswordMessage(null);
    try {
      const response = await api.changePassword(currentPassword, newPassword);
      setPasswordMessage(response.message);
      setCurrentPassword("");
      setNewPassword("");
      // Changing the password revokes every session, including this one.
      window.setTimeout(() => void signOut(), 1500);
    } catch (caught) {
      setPasswordError(caught instanceof ApiError ? caught.message : "Could not change password.");
    } finally {
      setSavingPassword(false);
    }
  }

  async function deleteAccount(event: React.FormEvent) {
    event.preventDefault();
    if (deleteConfirmation !== "DELETE") {
      setDeleteError('Type DELETE to confirm.');
      return;
    }
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteAccount(deletePassword);
      await signOut();
    } catch (caught) {
      setDeleteError(caught instanceof ApiError ? caught.message : "Could not delete the account.");
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Settings"
        description="Profile, account security, usage, and deployment capabilities."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="text-sm font-semibold">Profile</h2>
          <form onSubmit={saveProfile} className="mt-3 space-y-4">
            {profileError ? <ErrorState message={profileError} /> : null}
            {profileMessage ? (
              <div className="rounded-lg border border-success/30 bg-success/5 px-3 py-2 text-xs text-success">
                {profileMessage}
              </div>
            ) : null}
            <Field label="Full name" htmlFor="full_name">
              <Input
                id="full_name"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                required
                maxLength={120}
              />
            </Field>
            <Field label="Email" htmlFor="email" hint="Email changes are not supported in this build.">
              <Input id="email" value={user.email} readOnly className="bg-muted" />
            </Field>
            <Button type="submit" disabled={savingProfile}>
              {savingProfile ? <Spinner /> : null}
              Save profile
            </Button>
          </form>
        </Card>

        <Card className="p-5">
          <h2 className="text-sm font-semibold">Account security</h2>
          <form onSubmit={savePassword} className="mt-3 space-y-4">
            {passwordError ? <ErrorState message={passwordError} /> : null}
            {passwordMessage ? (
              <div className="rounded-lg border border-success/30 bg-success/5 px-3 py-2 text-xs text-success">
                {passwordMessage} Signing you out…
              </div>
            ) : null}
            <Field label="Current password" htmlFor="current_password">
              <Input
                id="current_password"
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                required
              />
            </Field>
            <Field
              label="New password"
              htmlFor="new_password"
              hint="At least 10 characters, with a letter and a number."
            >
              <Input
                id="new_password"
                type="password"
                autoComplete="new-password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                required
              />
            </Field>
            <Button type="submit" disabled={savingPassword}>
              {savingPassword ? <Spinner /> : <KeyRound size={14} aria-hidden />}
              Change password
            </Button>
          </form>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Active sessions</h2>
            <Badge tone="neutral">{sessions?.length ?? 0}</Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Each row is a refresh-token grant. Changing your password revokes all of them.
          </p>
          <ul className="mt-3 divide-y divide-border">
            {sessions === null ? (
              <li className="py-2 text-xs text-muted-foreground">Loading sessions…</li>
            ) : sessions.length === 0 ? (
              <li className="py-2 text-xs text-muted-foreground">No active sessions.</li>
            ) : (
              sessions.map((session) => (
                <li key={session.id} className="py-2 text-xs">
                  <p className="truncate font-medium text-foreground">
                    {session.user_agent || "Unknown client"}
                  </p>
                  <p className="mt-0.5 text-muted-foreground">
                    Started {formatDate(session.created_at)} · expires{" "}
                    {formatDate(session.expires_at)} · {session.ip_address || "unknown IP"}
                  </p>
                </li>
              ))
            )}
          </ul>
        </Card>

        <Card className="p-5">
          <h2 className="text-sm font-semibold">Usage</h2>
          {usage ? (
            <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
              {[
                ["Policies", usage.documents],
                ["Conversations", usage.conversations],
                ["Questions", usage.questions],
                ["Comparisons", usage.comparisons],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-lg border border-border bg-background px-3 py-2">
                  <dt className="text-[11px] text-muted-foreground">{label}</dt>
                  <dd className="text-base font-semibold">{value}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="mt-3 text-xs text-muted-foreground">Usage is unavailable.</p>
          )}
          <p className="mt-3 text-xs text-muted-foreground">
            {usage?.quota
              ? `${usage.quota_used_percent}% of your ${usage.quota}-question quota is used.`
              : "This deployment has no question quota."}
          </p>
        </Card>
      </div>

      <Card className="p-5">
        <h2 className="text-sm font-semibold">Deployment capabilities</h2>
        {meta ? (
          <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Version", meta.app_version],
              ["Environment", meta.environment],
              ["AI model", meta.llm_configured ? meta.llm_model : "Not configured"],
              ["Embeddings", meta.embeddings_mode],
              ["OCR", meta.ocr_enabled ? "Enabled" : "Disabled"],
              ["Max upload", `${meta.max_upload_mb} MB`],
              ["Max pages", String(meta.max_pdf_pages)],
              ["Retrieval top-k", String(meta.retrieval_top_k)],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-border bg-background px-3 py-2">
                <dt className="text-[11px] text-muted-foreground">{label}</dt>
                <dd className="mt-0.5 font-medium text-foreground">{value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="mt-2 text-xs text-muted-foreground">Capabilities are unavailable.</p>
        )}
      </Card>

      <Card className="border-danger/30 p-5">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-danger/10 text-danger">
            <ShieldAlert size={17} aria-hidden />
          </span>
          <div className="w-full">
            <h2 className="text-sm font-semibold text-danger">Delete account and data</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              This permanently deletes your account, every uploaded policy, extracted page,
              conversation, citation, insight and comparison. It cannot be undone.
            </p>
            <form onSubmit={deleteAccount} className="mt-3 grid gap-2 sm:max-w-md">
              {deleteError ? <ErrorState message={deleteError} /> : null}
              <Field label="Confirm your password" htmlFor="delete_password">
                <Input
                  id="delete_password"
                  type="password"
                  autoComplete="current-password"
                  value={deletePassword}
                  onChange={(event) => setDeletePassword(event.target.value)}
                  required
                />
              </Field>
              <Field label='Type "DELETE" to confirm' htmlFor="delete_confirmation">
                <Input
                  id="delete_confirmation"
                  value={deleteConfirmation}
                  onChange={(event) => setDeleteConfirmation(event.target.value)}
                  required
                />
              </Field>
              <Button
                type="submit"
                variant="danger"
                disabled={deleting}
                className="w-fit"
              >
                {deleting ? <Spinner /> : <Trash2 size={14} aria-hidden />}
                Delete my account
              </Button>
            </form>
          </div>
        </div>
      </Card>
    </div>
  );
}
