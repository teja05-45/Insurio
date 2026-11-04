# Product Requirements — Insurio

**Version:** 2.0
**Status:** Implemented baseline for the production rebuild

## 1. Problem

Insurance policies are long, cross-referenced documents written for adjusters, not policyholders.
A person trying to answer "is this surgery covered?" must find the definitions section, the
coverage schedule, the exclusions, the waiting-period clause, and any sub-limit, then reconcile
them. Generic chatbots answer from general knowledge and invent plausible clauses. The cost of a
confidently wrong answer is a denied claim.

## 2. Product

Insurio is an evidence-grounded policy intelligence workspace. A user uploads a policy PDF, receives
a structured reading of it, and asks questions whose answers are tied to page-level evidence from
that document.

**Non-goals:** selling insurance, adjudicating claims, giving legal advice, or answering from
anything other than the uploaded document.

## 3. Users and jobs

| Persona | Job to be done |
|---|---|
| Policyholder | "Does my policy pay for this?" before a procedure |
| Caregiver / family member | Understand an elderly parent's cover and waiting periods |
| Buyer | Compare two policies field by field before purchase |
| Broker / support agent | Locate the exact clause to quote to a client |

## 4. Functional requirements

### 4.1 Accounts
- Email + password registration, sign-in, sign-out.
- JWT access tokens (short-lived) and refresh tokens (rotating, revocable server-side records).
- Password reset request flow with a non-enumerable response and a single-use, expiring token.
- Profile update (name), password change, account and data deletion.
- Strict per-user isolation on every document, conversation, insight, and comparison.

### 4.2 Documents
- Upload PDF up to a configurable size (default 20 MB).
- Validate extension, MIME type, magic bytes, encryption, and page count before processing.
- Extract per-page text; retain page count and per-page character counts.
- OCR fallback for pages with little or no extractable text when OCR is enabled.
- Chunk with heading awareness; every chunk retains page range, section heading, and ordinal.
- Store a processing job with status (`queued`, `processing`, `ready`, `failed`) and error detail.
- Document library with status, size, pages, chunk count, and upload time.
- Document workspace: metadata, per-page extracted text, processing state, delete, PDF download for
  the owner.
- Serve PDFs only to the owning user via an authenticated endpoint.

### 4.3 Question answering
- Ask a question within a conversation; answers stream token by token.
- Retrieval: hybrid BM25 + embedding cosine, reciprocal-rank fusion, optional reranking.
- Configurable top-k (1–10) and a visible retrieval mode.
- Every answer returns citations: document, page, chunk, quoted excerpt.
- The server validates citations against the retrieved context; invalid citations are dropped and
  the answer is flagged.
- Answer contract: separate **stated**, **inferred**, and **not in document** content, plus a
  confidence and an `insufficient_evidence` flag.
- Persist messages, citations, retrieval metadata, model, and latency.
- Conversation list, rename, delete, history, copy, regenerate, feedback (helpful / not helpful).
- Advice-seeking questions get a scope reminder, not a recommendation.

### 4.4 Policy intelligence
Extract a fixed schema: policyholder, insurer, policy number, policy type, insured members, sum
insured, coverage items, exclusions, waiting periods, deductibles, co-payment, room-rent limit,
disease sub-limits, pre-existing-disease terms, maternity, renewal conditions, claim procedure,
claim documents, and notable conditions.

Each field stores: value, source quote, page, confidence (0–1), and status
(`found` / `ambiguous` / `missing`). Missing fields are shown as missing, never guessed.

### 4.5 Comparison
- Compare 2–5 owned policies.
- Deterministic, field-by-field comparison over extracted values with per-side evidence.
- Highlight differences, equalities, and information missing from one or more documents.

### 4.6 Voice
- Dictate a question using the browser's speech-recognition capability.
- Feature is hidden with an explanation when unsupported; no audio is stored.
- No dependency on a native microphone library.

### 4.7 Settings and usage
- Profile, password, data export, account deletion.
- Usage panel: documents, conversations, questions asked, plan-independent quotas if configured.

## 5. Quality attributes

- **Grounding:** no quoted clause may be absent from the retrieved source; unsupported claims are
  detectable and reported.
- **Security:** OWASP-aware defaults; validated uploads; hashed passwords; rotated refresh tokens;
  rate limits; no secrets in the repository.
- **Performance:** upload returns immediately and processes in the background; chat streams; pages
  render an empty skeleton rather than blocking on data.
- **Accessibility:** keyboard operable, visible focus, labelled controls, WCAG AA contrast,
  reduced-motion support.
- **Responsiveness:** usable at 360 px, 768 px, and 1440 px.
- **Observability:** structured logs with request IDs, health/readiness endpoints, job states.
- **Testability:** AI boundaries injectable and mockable; no paid calls in the default test suite.

## 6. Acceptance criteria

1. A new user can register, upload a text PDF, see it reach `ready`, open the workspace, read
   extracted page text, ask a question, and receive a cited answer — with a configured Groq key.
2. Without a Groq key the product still registers, uploads, extracts, chunks, indexes, shows
   insights, and compares; chat returns an explicit configuration error, not a fabricated answer.
3. Every document route rejects a different user's document with 404/403.
4. Every cited page exists in the document and every quote exists in the retrieved context.
5. Automated tests cover auth, upload validation, chunking, hybrid retrieval, citation validation,
   grounding behaviour, insights, comparison, and error envelopes, and run without network access.
6. `docker compose up --build` starts PostgreSQL, the API, and the web app; `/health/ready` reports
   the database as connected.
7. CI runs formatting, linting, tests, and both production builds.
