# Insurio — Initial Engineering Audit

**Audit date:** 2026-11-04
**Audited revision:** `9509d33` (`Update README.md`) on `main`
**Original repository:** https://github.com/teja05-45/Insurio
**Auditor:** Engineering review performed against the checked-out source, not the README claims.

This document is the Phase 1 deliverable. It records the state of the application *before* the
production rebuild. No source file was modified to produce it.

---

## 1. Existing architecture

The original project is a single-process Streamlit application with no server-side persistence.

```
app.py (845 lines)
  ├── inject_styles()                 modules/styles.py       (875 lines of CSS-in-Python)
  ├── process_document()              modules/rag_pipeline.py (PyMuPDF → chunks → embeddings)
  ├── retrieve_context()              modules/rag_pipeline.py (cosine similarity / TF-IDF)
  ├── generate_answer()               modules/groq_client.py  (Groq chat completion)
  ├── generate_policy_insights()      modules/groq_client.py  (one 6,000-character LLM call)
  ├── transcribe_audio()              modules/voice_input.py  (SpeechRecognition → Google STT)
  └── sanitize_llm_response()         modules/sanitize.py      (regex HTML stripping)
```

**Runtime flow**

1. The user uploads a PDF through `st.file_uploader`.
2. `process_document()` reads the bytes, extracts text page by page with PyMuPDF, joins the pages
   into one string, chunks by paragraph/sentence heuristics, and builds a `SimpleVectorStore`.
3. Embeddings are generated with `sentence-transformers` (`all-MiniLM-L6-v2`) inside the Streamlit
   request. If the import or model load fails, retrieval silently degrades to a keyword scorer.
4. The first user question triggers `retrieve_context()` (top-k = 4) and `generate_answer()`, which
   injects the retrieved text plus the last six chat messages into a Groq chat completion.
5. A second LLM call generates "policy insights" as Markdown, which `app.py` parses with regex into
   HTML cards.

Everything — document bytes, extracted text, embeddings, chat history, insights — lives in
`st.session_state`. Closing the browser tab destroys the entire workspace.

### Existing technology stack

| Layer | Technology | Version constraint |
|---|---|---|
| UI | Streamlit | `>=1.32.0` |
| LLM | Groq SDK | `>=0.4.0` |
| Primary model | `llama-3.1-8b-instant` | hard-coded |
| Fallback model | `mixtral-8x7b-32768` | hard-coded, decommissioned by Groq |
| PDF | PyMuPDF (`fitz`) | `>=1.23.0` |
| Embeddings | sentence-transformers | `>=2.2.0` (torch pulls ~2 GB) |
| Numerics | NumPy | `>=1.24.0` |
| Voice | SpeechRecognition + PyAudio | `>=3.10.0` / `>=0.2.13` |
| Config | python-dotenv | `>=1.0.0` |

There is no database, no authentication, no API layer, no job queue, no container definition, no
migration tooling, and no automated test.

---

## 2. Critical bugs (confirmed by code inspection)

| # | Severity | Location | Defect |
|---|---|---|---|
| 1 | Critical | `modules/groq_client.py:31` | `FALLBACK_MODEL = "mixtral-8x7b-32768"` has been retired by Groq. The fallback path therefore fails whenever the primary model errors, so the "fallback" guarantee in the README is false. |
| 2 | Critical | `README.md` | The documented models (`llama3-70b-8192`, `mixtral-8x7b-32768`) do not match the code (`llama-3.1-8b-instant`) and at least one is retired. Documentation misleads operators. |
| 3 | High | `modules/groq_client.py:171` | Insights are generated from `policy_text[:6000]` only. For a typical 40-page policy this discards most of the document; exclusions and waiting periods later in the file are never analysed. |
| 4 | High | `modules/rag_pipeline.py:39-47` | Page markers (`[Page N]`) are embedded inside the same string that is later chunked. A chunk may span pages and the marker can be split, so page provenance cannot be recovered reliably. No chunk retains structured page numbers. |
| 5 | High | `modules/rag_pipeline.py:171-183` | Keyword fallback: when the best score is `0`, the expression `[... for _, i in scores[:top_k] if scores[0][0] > 0]` yields an empty list, then returns the **first** chunks of the document. Irrelevant content is presented to the model as evidence. |
| 6 | High | `app.py:267-291` | The "idempotency guard" drops any question identical to the previous user message. Asking the same legitimate follow-up (for example after regenerating) is silently ignored with no feedback. |
| 7 | High | `app.py:267-291` | On any LLM error the user message is popped from history and rendered with a transient `st.error`. The failure disappears on the next rerun; there is no durable error state and the question is lost. |
| 8 | Medium | `modules/rag_pipeline.py:198-214` | Embedding search catches every exception and silently falls back to keyword search. The UI still reports "Embeddings" because the pill reflects the build method, not the method actually used for that query. |
| 9 | Medium | `modules/rag_pipeline.py:137-162` | `SentenceTransformer('all-MiniLM-L6-v2')` is instantiated per uploaded document (and reloads weights each time) inside a UI spinner. Model loading blocks the Streamlit script thread for seconds and multiplies memory across sessions. |
| 10 | Medium | `modules/rag_pipeline.py:82-124` | Character-count chunking applies overlap after paragraph splitting and again after sentence splitting. The same text can appear in two chunks with no deduplication, producing duplicate evidence and inflated relevance. |
| 11 | Medium | `modules/voice_input.py:18-62` | Microphone recording and Google speech recognition run synchronously in the Streamlit execution thread with a 5 s + 15 s worst-case block. Audio is sent to a third-party service with no disclosure. |
| 12 | Medium | `modules/sanitize.py` | HTML stripping is the only output defence. Encoded/obfuscated markup and Markdown image/link exfiltration payloads are not considered. It is used as a security control but is a cosmetic filter. |
| 13 | Low | `app.py:1` | `app.py` executes the sidebar, page config, and styles at import time. The module cannot be imported by tests or reused by another entry point. |
| 14 | Low | `modules/rag_pipeline.py:27` | `numpy` is imported but only used behind the embedding flag; errors in `np.linalg.norm` are swallowed by the same broad `except`. |

---

## 3. Major architectural weaknesses

1. **No persistence / no user model.** Refreshing the session loses every document and
   conversation. There is no notion of an owner, so document-level authorisation cannot exist.
2. **UI and AI concerns are entangled.** The RAG module imports Streamlit and calls
   `st.spinner` while building a vector index. Retrieval logic cannot be unit-tested without a
   Streamlit runtime.
3. **No API boundary.** The "backend" is the browser session. Mobile clients, integrations, or
   background workers are impossible without a rewrite.
4. **Per-session in-memory index.** Every session pays the embedding cost; memory grows with the
   number of open sessions and is never released deterministically.
5. **Single-shot insight generation.** The policy is summarised by one LLM call from a truncated
   prefix, with no structured schema, no confidence, no source offsets, and no way to compare
   policies field-by-field.
6. **No provenance.** Answers are free text. The model is told to "cite sections" but citations are
   unvalidated strings that may not exist in the source.
7. **No prompt-injection boundary.** Uploaded text is concatenated into the user message after a
   sentence of instruction. A PDF containing "ignore previous instructions" is treated as content.
8. **No operational surface.** No `/health`, no structured logs, no request IDs, no rate limiting,
   no cost control, no metrics.

---

## 4. Security issues

| Area | Finding | Risk |
|---|---|---|
| Authentication | None | Every visitor has full access to whatever is in the process; impossible to isolate documents |
| Authorisation | None | No owner checks on documents or conversations |
| Secret handling | `GROQ_API_KEY` read from `.env`, `.env` correctly gitignored | Acceptable for local use; no secret manager or startup validation |
| Upload validation | Extension filter only (`type=["pdf"]`); no size cap, no magic-byte check, no encryption check | Malformed/hostile PDFs reach PyMuPDF; unbounded memory use from large uploads |
| Prompt injection | Retrieved document text is inserted verbatim with no delimiters or instruction hierarchy | An uploaded policy can hijack the assistant, exfiltrate other context, or fabricate coverage |
| Output rendering | LLM output stripped of tags, then rendered as Markdown without `unsafe_allow_html`; insight cards use `unsafe_allow_html` with escaped fields | Mostly sound, but sanitisation is a regex denylist rather than a parser/allowlist |
| Rate limiting / abuse | None | A leaked URL can burn API credits without limit |
| Error leakage | Raw provider exception text is returned to the UI | Internal/provider details exposed |
| Data retention | None; data is ephemeral | Deletion/privacy requirements cannot be met, and data cannot be exported either |
| Voice privacy | Audio is uploaded to Google's recogniser without disclosure | Undisclosed third-party processing |

No literal API key is committed in the repository; `.env` is ignored. This was checked
against the tracked files and the three-commit history.

---

## 5. Performance issues

- Model weights are reloaded per document and per session; the first upload is dominated by
  cold-start, not inference.
- Embeddings are recomputed for every upload, even the same file, and are never cached.
- Cosine similarity is computed in pure NumPy over the full matrix in the Streamlit thread; fine at
  hundreds of chunks, untenable at tens of thousands.
- The answer call is synchronous and blocking; no streaming, so perceived latency is the full
  generation time.
- The entire document text is retained in session state alongside the chunk list and the embedding
  matrix (three copies of similar data).
- `generate_policy_insights` sends a fixed 6,000-character prefix — cheap, but wrong; and its output
  is not cached across sessions.

---

## 6. UI/UX problems

- Streamlit's defaults leak through: stock chat bubbles, stock buttons, stock file uploader. The
  custom CSS is extensive but cosmetic and cannot override layout behaviour on mobile.
- No authenticated product surface: no dashboard, no document library, no conversation history, no
  settings, no account lifecycle.
- Landing state, workspace state, and chat state are the same page with conditional branches; the
  user cannot navigate between documents.
- Insight cards are derived by regex-parsing an LLM Markdown response; a small wording change
  silently removes cards.
- No citations in the UI, no page references, no copy/regenerate/feedback controls.
- Loading, empty, error, and success states are inconsistent; failures are transient toasts.
- Emoji are used as primary iconography, which renders differently across platforms and is not
  accessible.
- No keyboard focus management, no ARIA landmarks, no reduced-motion handling.
- Mobile support is explicitly listed as a future improvement in the README.

---

## 7. Missing features relative to the product brief

- Accounts, sessions, sign-in/out, password reset.
- Persistent documents, conversations, messages, and citations.
- Document workspace with PDF viewer, page navigation, extracted text, processing status.
- Policy intelligence schema (sum insured, deductibles, co-payment, room-rent limits, PED clauses,
  maternity, renewal, claim documents) with evidence and confidence.
- Structured policy comparison.
- Streaming answers, follow-up suggestions, copy/regenerate/feedback.
- Hybrid retrieval (BM25 + vector) and reranking.
- Citation validation and explicit "insufficient evidence" answers.
- OCR fallback for scanned PDFs.
- Tests, CI, Docker, migrations, observability, rate limiting.

---

## 8. What is worth preserving

The rewrite should not discard the parts of the original that were sound:

- **PyMuPDF for text extraction** — fast, reliable, no external service.
- **The lexical fallback idea** — keyword retrieval is a real resilience mechanism; it becomes BM25
  within a hybrid retriever rather than a silent last resort.
- **The grounding instruction** ("never fabricate policy details", "say so when context is
  insufficient") — retained and strengthened into an evidence contract.
- **Output sanitisation and HTML escaping** — retained and extended to a Markdown/URL policy.
- **The insight-card information architecture** (coverage, exclusions, waiting periods, clauses,
  risk) — retained as a structured schema rather than parsed Markdown.
- **The conversational landing experience and starter questions** — retained in the new chat UI.

---

## 9. Recommended improvements (ordered)

1. Introduce a FastAPI service with an explicit API contract and a relational database; persist
   users, documents, pages, chunks, conversations, messages, citations, insights, and jobs.
2. Replace the per-session index with a persisted, page-aware chunk model and a hybrid retriever
   (BM25 + cosine), with optional embedding generation that degrades explicitly and visibly.
3. Build a grounded answer pipeline: strict context delimiters, an evidence contract, structured
   citation output, server-side citation validation, and an explicit insufficient-evidence result.
4. Replace regex insights with schema-validated extraction that stores source quote, page, and
   confidence per field, using deterministic rules plus the LLM only where needed.
5. Add JWT authentication, ownership checks on every document-scoped query, upload validation,
   rate limiting, and safe error envelopes.
6. Replace Streamlit with a Next.js/TypeScript application: marketing page, auth, dashboard,
   document workspace, streaming chat, insight dashboard, comparison, settings.
7. Add migrations, Docker Compose (PostgreSQL + API + web), CI, and automated tests at unit, API,
   pipeline, component, and end-to-end levels.
8. Make the AI provider configurable, use models that currently exist, add timeouts/retries, and
   never silently fall back.

## 10. Migration strategy

A full in-place Streamlit upgrade cannot satisfy persistence, multi-tenancy, citations, or a
premium UI. The migration is therefore a **strangler rebuild**:

- Preserve the original application under `legacy/streamlit/` for reference; it is not part of the
  new runtime and is documented as deprecated.
- Build the new backend and frontend alongside it, reusing the PDF extraction approach, the grounding
  intent, and the visual language of the insight cards.
- Ship both through Docker Compose; the Streamlit app is not exposed by the compose stack.
- Keep the original Git history intact; the rebuild is additive.

**Go/no-go:** proceed. The original is a coherent prototype with real UI craft, but its architecture
cannot be incrementally hardened into a multi-user, evidence-grounded product without the layers
above. The rebuild preserves its useful parts.
