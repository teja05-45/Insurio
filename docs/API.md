# API

Base URL: `/api/v1` (configurable). Interactive docs are served at `/docs` outside production.

## 1. Conventions

- Authentication: `Authorization: Bearer <access_token>` for every route except auth, `/meta` and
  `/health/*`.
- Errors always use one envelope:

```json
{
  "error": {
    "code": "document_not_found",
    "message": "Document not found.",
    "details": null,
    "request_id": "9f2c1a7b4e6d8c01"
  }
}
```

- Lists are paginated: `{ "items": [], "total": 0, "page": 1, "page_size": 20 }`.
- Timestamps are ISO 8601 with UTC offsets. Identifiers are UUID strings.

## 2. Routes

### Health and metadata

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health/live` | no | Liveness, version |
| GET | `/health/ready` | no | 200 when PostgreSQL responds, else 503 |
| GET | `/api/v1/meta` | no | Capabilities: model configured, embedding mode, limits |
| GET | `/api/v1/usage` | yes | Per-user counts |

### Authentication

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create account, returns access + refresh tokens |
| POST | `/auth/login` | Sign in |
| POST | `/auth/refresh` | Rotate a refresh token |
| POST | `/auth/logout` | Revoke a refresh grant |
| POST | `/auth/forgot-password` | Create reset token (returned outside production) |
| POST | `/auth/reset-password` | Consume reset token |
| GET | `/auth/me` | Current profile |
| PATCH | `/auth/me` | Update full name |
| DELETE | `/auth/me` | Delete account (password required) |
| POST | `/auth/change-password` | Change password, revoke sessions |
| GET | `/auth/sessions` | Active refresh grants |

### Documents

| Method | Path | Purpose |
|---|---|---|
| POST | `/documents` | Upload PDF (multipart `file`), 202 + job |
| GET | `/documents` | List (`page`, `page_size`, `status`) |
| GET | `/documents/{id}` | Detail + latest job |
| GET | `/documents/{id}/status` | Poll processing state |
| GET | `/documents/{id}/pages` | Extracted page text |
| GET | `/documents/{id}/pages/{n}` | One page |
| GET | `/documents/{id}/file` | Owner-only PDF bytes |
| GET | `/documents/{id}/insights` | Structured fields (extracts if absent) |
| POST | `/documents/{id}/insights/refresh` | Re-run extraction |
| DELETE | `/documents/{id}` | Delete document, data, and file |

### Conversations

| Method | Path | Purpose |
|---|---|---|
| POST | `/conversations` | Create for a ready document |
| GET | `/conversations` | List with message counts and previews |
| GET | `/conversations/{id}` | Thread with messages and citations |
| PATCH | `/conversations/{id}` | Rename |
| DELETE | `/conversations/{id}` | Delete thread |
| POST | `/conversations/{id}/messages` | Ask a question (SSE) |
| POST | `/conversations/{id}/regenerate` | Regenerate the last answer (SSE) |
| POST | `/messages/{id}/feedback` | `{"rating": "up"\|"down", "comment": null}` |

### Comparisons

| Method | Path | Purpose |
|---|---|---|
| POST | `/comparisons` | `{"document_ids": [..2–5..], "title": null}` |
| GET | `/comparisons` | Saved comparisons |
| GET | `/comparisons/{id}` | One comparison |
| DELETE | `/comparisons/{id}` | Delete |

## 3. Streaming protocol

`POST /conversations/{id}/messages` returns `text/event-stream`:

```
event: meta
data: {"conversation_id":"...","assistant_id":"...","retrieval_mode":"hybrid",
       "sources":[{"source_id":"S1","page_start":4,"page_end":4,"heading":"Exclusions"}],
       "model":"openai/gpt-oss-120b"}

event: delta
data: {"text":"Cosmetic surgery is "}

event: final
data: {"message":{"id":"...","role":"assistant","content":"...","citation_status":"valid",
       "citations":[{"source_id":"S1","page_start":4,"quote":"..."}],"confidence":0.87,
       "insufficient_evidence":false,"stated":[],"inferred":[],"not_in_document":[]}}
```

A failure mid-stream emits `event: error` with `{code, message}` and marks the stored message
`failed`. Clients should treat `final` as authoritative and may reload the conversation afterward.

Because `EventSource` cannot set headers, the web client uses `fetch` with a bearer token and parses
the stream manually. `AbortController` cancels generation.

## 4. Examples

Register and upload:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"asha@example.com","password":"StrongPass123","full_name":"Asha Rao"}' \
  | python -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

DOC=$(curl -s -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@policy.pdf;type=application/pdf" | python -c "import json,sys; print(json.load(sys.stdin)['id'])")

curl -s "http://localhost:8000/api/v1/documents/$DOC/status" -H "Authorization: Bearer $TOKEN"
```

Ask a question:

```bash
CONV=$(curl -s -X POST http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"document_id\":\"$DOC\"}" | python -c "import json,sys; print(json.load(sys.stdin)['id'])")

curl -N -X POST "http://localhost:8000/api/v1/conversations/$CONV/messages" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"question":"Is knee replacement covered?"}'
```

## 5. Status codes

| Code | Meaning in this API |
|---|---|
| 200 | Success |
| 201 | Account, conversation, or comparison created |
| 202 | Upload accepted, processing queued |
| 400 | Invalid operation (empty file, reset token reused, comparison of one policy) |
| 401 | Missing/expired token, invalid credentials, revoked refresh grant |
| 404 | Not found **or not owned** (ownership is not disclosed) |
| 409 | Duplicate upload, email already registered |
| 413 | File or page-count limit exceeded |
| 415 | Not a PDF |
| 422 | Schema validation failure |
| 429 | Rate limit exceeded |
| 502 | AI provider unavailable or stream interrupted |
| 503 | AI not configured, or database not ready |
