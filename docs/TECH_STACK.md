# Technology Stack and Decisions

## 1. Summary

| Layer | Choice | Version constraint |
|---|---|---|
| Web | Next.js (App Router) + React + TypeScript | Next 15, React 19, TS 5.6+ |
| Styling | Tailwind CSS + CSS variables | Tailwind 3.4 |
| Motion / icons / charts | Framer Motion, Lucide, Recharts | 11 / 0.4 / 2.x |
| API | FastAPI + Uvicorn | 0.115+, 0.30+ |
| Validation | Pydantic v2 + pydantic-settings | 2.9+, 2.5+ |
| ORM / migrations | SQLAlchemy 2 + Alembic | 2.0+, 1.13+ |
| Database | PostgreSQL | 16 |
| Auth | PyJWT + Argon2 (`pwdlib`) | 2.9+ / 0.2+ |
| PDF | PyMuPDF | 1.24+ |
| OCR (optional) | Tesseract via `pytesseract` | 0.3.13+ |
| Embeddings (optional) | fastembed (ONNX) or sentence-transformers | 0.4+ / 3.x |
| Retrieval | BM25 (in-house) + cosine + RRF + heuristic rerank | — |
| LLM | Groq OpenAI-compatible API | `groq` 0.13+ |
| HTTP client | httpx | 0.27+ |
| Tests | pytest, pytest-asyncio, httpx TestClient; Vitest + Testing Library; Playwright | — |
| Containers | Docker, Docker Compose | Compose v2+ |
| CI | GitHub Actions | — |

## 2. Why each choice

### Next.js + TypeScript (replacing Streamlit)
The brief asks for a premium SaaS surface with auth, routing, streaming, and responsive layouts.
Streamlit's execution model cannot provide per-user routing, a real document workspace, or a
design system that survives mobile. Next's App Router gives server components for the marketing
page, client components for the chat stream, file-based routing, and a production build that CI can
verify. TypeScript is chosen because the API contract (citations, extraction status, job states) is
structural and benefits from generated/hand-written types.

*Alternatives:* Vite + React SPA (simpler, but no server rendering and more bespoke routing),
SvelteKit (excellent, but smaller hiring pool and no advantage here), staying on Streamlit
(rejected: cannot meet the product requirements).

### Tailwind CSS
Utility CSS with design tokens defined as CSS variables. Fast to keep spacing and colour consistent,
no runtime cost, trivial dark-surface extension later. A component library was rejected because the
brief explicitly asks to avoid generic dashboard templates.

### FastAPI
Typed request/response models, dependency injection for auth and DB sessions, automatic OpenAPI,
native async streaming for SSE. The heavy work (PDF parsing, embeddings) stays synchronous in a
worker thread; request handlers remain async where it matters.

*Alternatives:* Django REST (batteries included but heavier and its ORM/auth do not fit the
custom JWT + document-authorisation model as directly), Flask (no first-class validation/streaming
contract), Node/Nest (would split the AI/PDF tooling from the ecosystem with the best libraries).

### PostgreSQL, not SQLite, not pgvector in v1
Postgres provides real constraints, UUID types, JSONB for extraction payloads, transactional job
updates, and row-level ownership via indexed `user_id` columns. SQLite is retained only as the test
database so the suite runs without containers.

**pgvector was evaluated and deliberately deferred.** Chunk embeddings are stored as JSONB and
cosine similarity is computed per document in a bounded Python pass. Rationale: a single policy has
hundreds to low thousands of chunks, so an exact scan is fast and avoids a native extension that
would break SQLite-based tests and complicate managed-Postgres provisioning. The retrieval
interface is isolated in `app/ai/retrieval.py`; adding pgvector is a migration plus one
`search_chunks` implementation, documented in `docs/DECISIONS.md`.

### SQLAlchemy 2 + Alembic
Mature, explicit, testable. Alembic migrations are the single source of schema truth and are run at
container startup. Async SQLAlchemy was rejected: PDF parsing and embedding calls are CPU-bound and
already occupy threads, so an async ORM would add complexity without throughput here.

### Groq with OpenAI-compatible models
Groq remains the inference provider as requested. The original hard-coded models are retired or
enterprise-only; the rebuild defaults to `openai/gpt-oss-120b` (production, 131k context) with
`openai/gpt-oss-20b` as an explicit, optional fallback. Model IDs are configuration, not code, so a
deprecation is an env change. The provider boundary (`app/ai/llm.py`) is injectable, which lets tests
run without network or paid calls.

### PyMuPDF
Fast, pure-pip, page-accurate extraction, already proven in the original app. `pdfplumber` is slower;
`pypdf` has weaker layout handling. OCR fallback uses Tesseract only when a page yields almost no
text, and is off unless installed.

### Embeddings: fastembed first, sentence-transformers second, lexical always
`fastembed` (ONNX `bge-small-en-v1.5`, 384 dims) avoids the ~2 GB torch dependency and is fast on
CPU. `sentence-transformers` is supported for users who already have it. If neither is installed,
the application runs a **visible** BM25-only mode instead of silently pretending to be semantic.
Tests inject a deterministic hashing embedder, so vector paths are covered offline.

### In-house BM25 + RRF instead of a search service
No extra infrastructure for a per-document corpus, fully unit-testable, no network hop. Elasticsearch
or a hosted vector DB would be justified only at multi-tenant scale.

### JWT access + refresh with server-side refresh records
Access tokens are short-lived and stateless; refresh tokens are hashed in the `sessions` table so
they can be revoked and rotated. Cookie storage was considered, but the frontend is a separate
origin in development and the product is token-based; refresh tokens are stored in `localStorage`
with the trade-off documented in `docs/SECURITY.md`.

### Background processing via FastAPI BackgroundTasks + a job table
Extraction and embedding take seconds, not hours. A durable `processing_jobs` row makes state
observable and recoverable; a Celery/Redis deployment is unnecessary and is documented as the scale
path. This keeps the compose stack to three services.

## 3. Compatibility and constraints

- Python 3.11–3.12 in Docker (`python:3.12-slim`); 3.11 verified locally.
- Node 20.9+ (Next 15); Node 24 verified locally.
- PostgreSQL 16 is the only required external service.
- Optional features degrade explicitly: OCR needs the `tesseract-ocr` binary; semantic embeddings
  need `requirements-ml.txt`; chat needs `GROQ_API_KEY`.
- `GROQ_MODEL` must be a currently supported Groq model. Check
  `https://console.groq.com/docs/models` before changing defaults.

## 4. Trade-offs accepted

| Decision | Cost |
|---|---|
| JSONB embeddings instead of pgvector | Exact scan per document; revisit above ~20k chunks/document |
| Refresh tokens in localStorage | XSS exposure mitigated by strict CSP and short access-token lifetime; httpOnly-cookie variant documented |
| No Redis | Rate limiting is per-process; horizontal scaling needs a shared limiter |
| Synchronous SQLAlchemy | Less concurrency per worker; compensated by Uvicorn workers |
| Single LLM provider | Provider outage stops chat; provider interface allows a second adapter |
| BackgroundTasks | Jobs are not retried after a process crash; the job row exposes the failure |

## 5. Rejected alternatives

- **Streamlit** — cannot satisfy auth, routing, streaming, or responsive product UI.
- **Django** — excellent, but its admin/auth assumptions and sync-first ecosystem add weight for no
  requirement here.
- **pgvector in v1** — native extension complicates tests and managed-Postgres setup for no measured
  benefit at this corpus size.
- **Celery + Redis** — operational cost not justified by second-scale jobs.
- **LangChain / LlamaIndex** — the pipeline is small and auditable; frameworks obscure citation
  validation and prompt boundaries, which are the core of this product.
