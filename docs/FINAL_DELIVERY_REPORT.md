# Final Delivery Report

## 1. Executive summary

Insurio has been rebuilt from a single-file Streamlit prototype into a multi-user, evidence-grounded
insurance policy intelligence application:

- **Backend:** FastAPI service with layered routes, services, repositories and schemas; PostgreSQL
  schema managed by Alembic; Argon2id and rotating refresh tokens; page-accurate ingestion; hybrid
  retrieval; a grounded answer pipeline with server-validated citations and an explicit
  insufficient-evidence path.
- **Frontend:** Next.js 15 / React 19 / TypeScript application covering landing, authentication,
  dashboard, document library and workspace, policy intelligence, streaming chat with citations and
  feedback, comparison, and settings.
- **Operations:** Docker images and Compose stack (PostgreSQL + API + web) with health checks and
  persistent volumes; GitHub Actions CI; 55 backend tests, 7 component tests, and clean lint and
  typecheck.

The initial prototype's useful parts (PyMuPDF extraction, lexical fallback intent, grounding
instruction, insight-card information architecture) were preserved. Its architecture — session-only
state, no accounts, unvalidated uploads, unverified citations — was replaced.

## 2. Original vs final architecture

| Concern | Original | Final |
|---|---|---|
| Runtime | Streamlit script, one process | FastAPI + Next.js + PostgreSQL |
| State | `st.session_state`, lost on refresh | Durable relational data |
| Users | None | Accounts, sessions, per-user isolation |
| Documents | In-memory text and embeddings | Stored PDFs, pages, chunks, jobs, insights |
| Retrieval | Cosine or silent TF-IDF fallback | BM25 + cosine + RRF + rerank, mode reported |
| Answers | Free text, unverified "sections" | Strict JSON, validated citations, evidence split |
| Insights | Regex over one truncated LLM call | 20 fields with quote, page, confidence, status |
| Comparison | Absent | Deterministic 2–5 policy matrix with evidence |
| UI | Streamlit controls and CSS | Purpose-built responsive product UI |
| Security | None | Ownership checks, upload validation, rate limits, prompt boundaries |
| Tests / CI / Docker | None | pytest, Vitest, GitHub Actions, Compose |

## 3. Technology decisions

Next.js + TypeScript for routing, streaming and a real design system; FastAPI for typed contracts and
SSE; PostgreSQL because ownership and constraints are relational; SQLAlchemy 2 + Alembic for explicit
schema control; PyMuPDF for fast page-accurate extraction; in-house BM25 + RRF instead of a search
service; fastembed-first embeddings to avoid a 2 GB torch install; Groq with model IDs in
configuration; Docker Compose with three services and no Redis/Celery at this scale.

Trade-offs and alternatives: [`TECH_STACK.md`](TECH_STACK.md) and [`DECISIONS.md`](DECISIONS.md).

## 4. Features implemented

- Registration, sign-in, sign-out, password reset, profile update, password change, session list,
  account deletion.
- PDF upload with magic-byte, size, encryption and page validation; background ingestion with job
  progress; document library and workspace; owner-only PDF retrieval.
- Page-accurate extraction, heading-aware chunking with page ranges, optional OCR.
- Hybrid retrieval with reciprocal rank fusion and heuristic reranking.
- Streaming answers with validated citations, confidence, evidence split, regenerate, copy, feedback,
  follow-up prompts and voice dictation.
- Structured insights across 20 fields with quotes, pages, confidence and missing status.
- Policy comparison for two to five documents with per-side evidence and missing detection.
- Settings with profile, security, sessions, usage, deployment capabilities and deletion.
- Docker Compose, migrations, seed-free startup, health/readiness, CI, and an offline test suite.

## 5. UI/UX improvements

- A real product surface with routing and persistent state instead of one Streamlit page.
- Consistent design tokens (AI blue accent, neutral surfaces, subtle shadows) and typography.
- Every screen has loading, empty, error and success states; no placeholder controls.
- Evidence is part of the interface: citation accordions, page references, “Not stated” labels, stated
  vs inferred vs absent panels.
- Responsive layouts from 360 px to desktop; mobile navigation drawer; horizontal table scroll.
- Accessibility: labelled icon buttons, visible focus, `aria-live` for streaming, reduced-motion
  support, status never conveyed by colour alone.
- The landing page labels its product mock as illustrative — no fabricated screenshots.

## 6. Database design

Twelve tables with UUID keys, foreign keys and cascades, status checks, timestamps and ownership
indexes: users, sessions, password reset tokens, documents, document pages, document chunks, policy
insights, processing jobs, conversations, messages, citations, feedback, policy comparisons. ER
diagram and column detail in [`DATABASE.md`](DATABASE.md).

## 7. RAG implementation

Extraction → normalisation → heading/sentence segmentation with page tags → overlapping chunks with
dedupe → optional embeddings → hybrid retrieval (BM25 + cosine + RRF) → heuristic reranking →
numbered, escaped sources within a character budget → strict JSON generation → incremental decoding
of the answer field → server-side citation validation → persisted answer with evidence split.

If retrieval returns nothing, no model call is made. Invalid quotes are dropped. Missing information
produces an explicit refusal. Detail: [`RAG_PIPELINE.md`](RAG_PIPELINE.md).

## 8. Security improvements over the prototype

- Accounts with Argon2id hashes; JWTs plus rotating, revocable, hashed refresh tokens.
- Document, conversation, insight and comparison access scoped to the owner; 404 for foreign ids.
- Upload validation and containment-checked storage; no public file URLs.
- Retrieved text escaped and delimited; instruction-like content flagged; model output never rendered
  as HTML.
- Rate limits, security headers, strict CORS, uniform error envelopes, structured logs without
  secrets.
- Production refuses to start with the development secret.

Threat model and accepted risks: [`SECURITY.md`](SECURITY.md).

## 9. Test execution and verification

| Check | Result |
|---|---|
| `ruff check app tests` | Passed |
| `pytest -q` | Passed (55 tests) |
| `npm run typecheck` | Passed |
| `npm run test` | Passed (7 tests) |
| `npm run build` | Passed (13 routes) |
| `docker compose up --build -d` | Passed; all services healthy |
| API health | `{"status":"ok","database":"connected"}` |
| Live smoke: register, upload, ready, insights, compare, ownership | Passed |
| Live chat with Groq | Blocked — no API key; 503 path verified |

Full commands and limitations: [`TEST_EXECUTION_REPORT.md`](TEST_EXECUTION_REPORT.md) and
[`FINAL_AUDIT_REPORT.md`](FINAL_AUDIT_REPORT.md).

## 10. Running locally

```bash
# API
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example .env      # set DATABASE_URL, SECRET_KEY, optionally GROQ_API_KEY
alembic upgrade head
uvicorn app.main:app --reload

# Web
cd frontend && npm ci && cp .env.local.example .env.local && npm run dev
```

Open http://localhost:3000. Full guide: [`LOCAL_SETUP.md`](LOCAL_SETUP.md).

## 11. Running with Docker

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health/ready
```

If host port 3000 is occupied, set `WEB_PORT=3100`. Guide: [`DOCKER_SETUP.md`](DOCKER_SETUP.md). For
production settings: [`DEPLOYMENT.md`](DEPLOYMENT.md).

## 12. Environment configuration

All variables are documented in [`.env.example`](../.env.example): application, security, database,
uploads, Groq, retrieval/embeddings, rate limits, and Compose-only ports/credentials. Mandatory in
production: `SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`; `NEXT_PUBLIC_API_BASE_URL` is baked into the
web bundle at build time. `GROQ_API_KEY` is required only for chat.

## 13. Git summary

- 88 commits at the time of this report: the 12-commit audited baseline plus 76 new commits.
- Conventional subjects, one logical change per commit, no attribution trailers.
- Working tree clean after the report commits; no generated output or secrets tracked.

## 14. Screenshots

None. The UI is implemented and builds, but no screenshots were captured in this environment and no
mockups were substituted. See [`FINAL_AUDIT_REPORT.md`](FINAL_AUDIT_REPORT.md).

## 15. Known limitations

No email delivery; account-deletion file sweep missing; per-process rate limiting; local-disk uploads;
no Playwright browser suite; no labelled AI benchmark; JSONB embeddings with an exact scan; OCR
unverified; live Groq generation not exercised here; appending host port conflict on 3000.

## 16. Final project structure

```
Insurio/
├── backend/
│   ├── app/
│   │   ├── ai/               chunking, embeddings, retrieval, rerank, prompts,
│   │   │                     citations, pipeline, extraction, llm
│   │   ├── api/              deps + routes (auth, documents, chat, comparisons, meta, health)
│   │   ├── core/             config, security, logging, errors, middleware, rate limit
│   │   ├── db/               engine, session, declarative base
│   │   ├── models/           users, documents, conversations, policies
│   │   ├── repositories/     users, documents, conversations, policies
│   │   ├── schemas/          auth, chat, documents, common
│   │   ├── services/         auth, documents, pdf, storage, insights, comparison,
│   │   │                     conversations, answering
│   │   └── main.py
│   ├── alembic/              env + initial schema revision
│   ├── tests/                conftest + 8 test modules
│   ├── Dockerfile, requirements*.txt, pyproject.toml, alembic.ini
├── frontend/
│   ├── app/                  landing, auth, (app) dashboard/documents/insights/chat/compare/settings
│   ├── components/           UI primitives, shell, markdown, citations, voice, upload, reveal
│   ├── lib/                  api, auth, format, types, tests
│   ├── Dockerfile, package.json, configs
├── docs/                     audit, PRD, architecture, database, API, security, RAG,
│                             testing, deployment, guides, reports
├── legacy/streamlit/         preserved prototype (deprecated)
├── .github/workflows/ci.yml
├── docker-compose.yml, .env.example, README.md, CONTRIBUTING.md, LICENSE
```

## 17. Recommended next steps

1. Add a real Groq key and run a scripted live chat verification with citation inspection.
2. Implement email delivery for reset tokens.
3. Add a Playwright suite and capture real screenshots for the README.
4. Sweep stored files on account deletion; move uploads to object storage.
5. Build a labelled evaluation set and publish retrieval/citation metrics.
