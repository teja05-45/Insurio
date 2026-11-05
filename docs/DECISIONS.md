# Architecture Decisions

Each record states the context, the decision, and the consequence. Dates are omitted because these
decisions were made within a single rebuild.

## ADR-001 — Replace Streamlit with a FastAPI + Next.js product

**Context.** The original app kept documents, embeddings and chat in `st.session_state`; no accounts,
persistence, API or mobile surface were possible.

**Decision.** Rebuild as a separate API and web client; preserve the old app under
`legacy/streamlit/`.

**Consequence.** Real authentication, ownership, persistence and a responsive UI become possible. The
cost is two deployables and an explicit API contract.

## ADR-002 — PostgreSQL, with SQLite only for tests

**Context.** Relational data with ownership, constraints and JSON payloads.

**Decision.** PostgreSQL 16 in production; SQLite in the test suite so tests need no container.

**Consequence.** Tests are fast and offline, but migrations are not exercised by tests; they must be
reviewed and run against PostgreSQL.

## ADR-003 — Defer pgvector

**Context.** Chunk counts per document are hundreds to low thousands.

**Decision.** Store embeddings as JSONB and compute cosine similarity in-process over the document's
chunks. Keep retrieval isolated behind `ai/retrieval.py`.

**Consequence.** No native extension, tests work on SQLite, exact search is accurate. Above roughly
20k chunks per document, migrate to pgvector.

## ADR-004 — BM25 + cosine with reciprocal rank fusion, not a search service

**Context.** One corpus per document; no cross-tenant search.

**Decision.** Implement BM25 and RRF in-house (`ai/retrieval.py`), with a heuristic reranker.

**Consequence.** No infrastructure, fully testable, transparent scoring. A learned reranker is future
work; paraphrases without lexical overlap depend on embeddings.

## ADR-005 — Explicit degradation instead of silent fallbacks

**Context.** The original fell back to keyword search while still claiming embeddings.

**Decision.** Report the retrieval mode actually used (`hybrid`, `bm25`, `none`) and state when
embeddings are disabled.

**Consequence.** Users and operators can reason about answer quality. The UI must show the mode,
which it does in the chat header.

## ADR-006 — Validate citations server-side

**Context.** Free-text citations can be fabricated.

**Decision.** Accept a citation only if its quote appears in the retrieved source after normalisation,
and persist only accepted citations. Drop invalid ones and flag the answer.

**Consequence.** Fabricated clauses cannot reach the UI as sources. Quotes are limited to the
retrieved context, so a valid clause outside the top-k is not citable for that turn.

## ADR-007 — Strict JSON answer contract with evidence separation

**Context.** Users need to distinguish policy text from interpretation.

**Decision.** The model returns `answer_markdown`, `citations`, `stated`, `inferred`,
`not_in_document`, `confidence`, `insufficient_evidence`. Streaming decodes only the answer field.

**Consequence.** The UI can present evidence honestly. Models occasionally fail to produce valid JSON;
those answers are shown but marked `unparsed` rather than trusted.

## ADR-008 — JWT access + rotating hashed refresh tokens

**Context.** The SPA needs revocable sessions without cookie/CSRF complexity.

**Decision.** Short-lived JWT access tokens; opaque refresh tokens stored as SHA-256 digests with
rotation and revocation.

**Consequence.** Tokens live in `localStorage`, an accepted XSS trade-off mitigated by a short access
lifetime and no raw-HTML rendering. An httpOnly-cookie variant remains possible.

## ADR-009 — FastAPI BackgroundTasks for ingestion

**Context.** Ingestion takes seconds; a queue adds operational cost.

**Decision.** In-process background tasks with a durable `processing_jobs` row.

**Consequence.** Simple single-node deployment. Jobs do not survive a process crash and do not retry
automatically; the job row exposes the failure. Move to a queue when needed.

## ADR-010 — Local disk storage behind a service module

**Context.** One node, no object storage in scope.

**Decision.** Store PDFs under `UPLOAD_DIR/<user id>/<uuid>.pdf`, addressed only by server-generated
keys, with path containment checks.

**Consequence.** Path traversal is structurally prevented. Horizontal scaling requires object storage;
account deletion does not yet sweep files (known gap).

## ADR-011 — Deterministic extraction before LLM enrichment

**Context.** LLM-only extraction is unstable and unverifiable.

**Decision.** Rules always run; LLM values are merged only when their quote is found verbatim on the
stated page.

**Consequence.** Missing fields stay missing and values are traceable. Recall for unusual formats is
lower than a pure-LLM approach, which is the intended trade.

## ADR-012 — Heuristic prompt-injection defence, not a classifier

**Context.** Uploaded documents are untrusted input to the model.

**Decision.** Delimit and escape document text, treat it as data in the system prompt, and flag
instruction-like phrases. Do not add a separate classifier.

**Consequence.** No external service or latency, and the structural boundary is the main control. An
adversarial corpus and regression tests are still needed.
