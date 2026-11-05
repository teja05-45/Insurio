# Security

## 1. Threat model

| Actor | Capability assumed | Primary controls |
|---|---|---|
| Unauthenticated visitor | Can call public auth endpoints | Rate limits, uniform errors, no document enumeration |
| Authenticated user | Owns an account and documents | Ownership predicates on every document-scoped query |
| Malicious upload | Controls PDF bytes and text | Magic-byte + size + page validation, prompt delimiters, injection heuristics |
| Hostile document content | Attempts to instruct the model | Sources are data, escaped, and never concatenated as instructions |
| Network attacker | Can observe or replay tokens | HTTPS assumed, short-lived access tokens, rotating hashed refresh tokens |
| Operator error | Leaves defaults in place | Startup refuses the default secret in production; `.env` is gitignored |

## 2. Authentication

- Passwords are hashed with Argon2id through `pwdlib`; verification failures return false rather
  than raising.
- Access tokens are JWTs (HS256) with `sub`, `typ=access`, `jti`, `iat`, `exp`. Default lifetime is
  30 minutes and is configurable between 5 minutes and 24 hours.
- Refresh tokens are 64-character URL-safe random strings. Only their SHA-256 digest is stored in
  `sessions`, along with expiry, user agent, IP and revocation time.
- Refresh is single-use: rotation revokes the presented grant and issues a new one in the same
  transaction. Reuse of a rotated token fails with 401.
- Login responses are identical for unknown email and wrong password.
- Password reset always returns the same message; the reset token is single-use, expiring, and only
  returned in the response outside production because email delivery is not part of this build.
- Password change and account deletion both require the current password. Password change and reset
  revoke every refresh grant.

## 3. Authorization

There is no global "list all documents" query. `repositories/documents.get_owned` requires both the
document id and the authenticated user id. Routes resolve `OwnedDocument` / `OwnedConversation`
dependencies before touching data.

Another user's resource returns **404**, not 403, so the API does not confirm that a document exists.
Conversation ids are resolved through the same ownership predicate; messages are loaded only after
the conversation is authorized. Feedback requires the message to belong to the caller through a join
on `conversations.user_id`.

The PDF endpoint is authenticated like every other route. There is no public or signed URL, and
`Cache-Control: private, no-store` plus `X-Content-Type-Options: nosniff` are set on the response.

## 4. Upload safety

`services/pdf.py` and `services/storage.py` enforce:

- non-empty body and a configurable size ceiling (default 20 MB), checked before parsing;
- `%PDF-` magic bytes, so a renamed executable is rejected;
- a declared content type must be PDF or octet-stream, and the filename must end in `.pdf`;
- encrypted PDFs are rejected with a clear message;
- page count ceiling (default 400);
- storage names are server-generated UUIDs under a per-user directory. The user filename is metadata
  only, so path traversal is structurally impossible;
- resolved paths are checked with `is_relative_to` before reading or deleting;
- PDFs are never executed or converted to HTML by the API.

## 5. Prompt injection

- Retrieved text is wrapped in `<source>` elements with IDs, page numbers and headings; the system
  prompt states explicitly that everything inside is untrusted data.
- Source content is HTML-escaped so it cannot close the delimiter.
- Instruction-like phrases are detected (`ignore previous instructions`, `reveal the system prompt`,
  and similar) and counted; the UI/pipeline treats them as suspicious but still as content.
- Retrieved text never becomes a system message. History is role-limited to `user` and `assistant`.
- Model output is never executed. Answers render as Markdown without raw HTML; links open with
  `rel="noopener noreferrer"`.

## 6. Application security

- **Validation:** every request body is a Pydantic model with length and type constraints; extra
  fields are ignored by default. Errors return a uniform envelope with field details.
- **SQL injection:** all queries use SQLAlchemy expressions and bound parameters. No raw SQL is built
  from user input; the only `text()` usage is `SELECT 1` for readiness.
- **XSS:** no `dangerouslySetInnerHTML` anywhere; Markdown is rendered with a sanitising React
  renderer; insight values are rendered as text.
- **CSRF:** the API is token-based and does not use cookies, so CSRF is not applicable. CORS is an
  explicit allowlist with credentials enabled only for those origins.
- **Headers:** the API sends `X-Content-Type-Options`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, a restrictive `Permissions-Policy`, CORP and a
  `default-src 'none'` CSP. The web app sends no-sniff, DENY, referrer and permissions headers.
- **Rate limiting:** sliding windows for auth (20/min), chat (30/min) and upload (20/hour), keyed by
  client IP. Disabled in the test environment.
- **Logging:** structured JSON with request ids. Tokens, passwords and API keys are never logged;
  provider exception text is mapped to generic client errors.
- **Secrets:** `.env` is gitignored; only `.env.example` is tracked. Production startup refuses the
  development secret. The Groq key is read from the environment and never returned by any endpoint —
  `/meta` exposes only whether a key is configured.

## 7. Data lifecycle

Deleting a document removes its database rows (cascade) and its stored file. Deleting an account
removes all owned data through foreign-key cascades, but **does not currently delete uploaded files
from the volume**; this is a known limitation recorded in `docs/FINAL_AUDIT_REPORT.md`. Files are
addressed by UUID and are unreachable through the API after deletion.

## 8. Accepted risks and gaps

| Item | Status | Mitigation / path |
|---|---|---|
| Refresh token in `localStorage` | Accepted for this token-based SPA | Short access lifetime, strict CSP, httpOnly-cookie variant documented |
| Rate limiter is per process | Accepted for single-node v1 | Move to Redis when scaling horizontally |
| No email delivery for reset links | Gap | Token returned only outside production; integrate a mail provider before launch |
| No MFA | Gap | Out of scope for v1 |
| No virus scanning of uploads | Gap | PDFs are parsed, never executed; add ClamAV at the ingress for untrusted public deployments |
| Files not removed on account deletion | Gap | Add a storage sweep job keyed by `user_id` prefix |
| No audit log of document access | Gap | Structured request logs include user id and path; a dedicated audit table is future work |
