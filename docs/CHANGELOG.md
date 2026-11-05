# Changelog

All notable changes to Insurio. Format follows Keep a Changelog; versions follow SemVer.

## [2.0.0] — Production rebuild

### Added

- FastAPI backend with layered routes, services, repositories, schemas and models.
- PostgreSQL schema with migrations for users, sessions, password resets, documents, pages, chunks,
  jobs, insights, conversations, messages, citations, feedback and comparisons.
- Argon2id password hashing, JWT access tokens, rotating hashed refresh tokens, logout and revocation.
- Per-user ownership enforcement on documents, conversations, insights, comparisons and files.
- PDF validation (magic bytes, size, encryption, page count) and page-accurate extraction.
- Heading-aware, page-tagged chunking with overlap control and deduplication.
- Optional embeddings (fastembed, sentence-transformers, deterministic hashing for tests) with honest
  BM25 fallback.
- Hybrid retrieval with reciprocal rank fusion and heuristic reranking.
- Grounded answer pipeline: numbered sources, strict JSON contract, incremental answer streaming over
  SSE, server-side citation validation, explicit insufficient-evidence responses.
- Evidence split persisted per message: stated, inferred, not in document.
- Structured policy insights with value, quote, page, confidence and missing status; optional LLM
  enrichment that cannot insert unverifiable quotes.
- Deterministic policy comparison over two to five documents with per-side evidence.
- Responsive Next.js 15 application: landing, auth (sign in, sign up, reset), dashboard, document
  library and workspace with PDF preview and page navigation, insights dashboard, streaming chat with
  citations/regenerate/feedback/voice, comparison, settings.
- Docker Compose stack (PostgreSQL, API, web) with health checks and persistent volumes.
- Offline pytest suite, Vitest component tests, GitHub Actions CI, ruff configuration.
- Documentation set: audit, PRD, architecture, system design, tech stack, design, database, API,
  auth, security, RAG pipeline, AI evaluation, testing, deployment, local and Docker setup,
  troubleshooting, user and developer guides, roadmap, decisions.

### Changed

- LLM models are configuration (`openai/gpt-oss-120b` primary, `openai/gpt-oss-20b` fallback) instead
  of hardcoded, retired identifiers.
- Prompts treat retrieved text as untrusted data with explicit delimiters.
- The Streamlit prototype is preserved under `legacy/streamlit/` and is not part of the runtime.

### Fixed

- Page provenance is retained through extraction and chunking, so citations can name a page.
- Keyword fallback no longer returns irrelevant leading chunks; chunks with no lexical or semantic
  match are dropped.
- Retrieval mode reflects the method used for the current query.
- Interrupted answer streams are healed to `failed` instead of spinning forever.
- Regeneration no longer deletes citations in a way that can leave the session stale.

### Known limitations

- No email delivery for password reset (token is returned outside production only).
- Account deletion removes database rows but not stored PDF files.
- Rate limiting is per process.
- No Playwright/browser end-to-end suite; no visual regression tests.
- No labelled AI benchmark; accuracy metrics are not claimed.
- Embeddings are JSONB with an exact scan per document.
