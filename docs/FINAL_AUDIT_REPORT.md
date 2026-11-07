# Final Audit Report

Verification performed after implementation, against the running stack and the automated checks.
Statuses: **Passed**, **Failed**, **Blocked**, **Not tested**.

## A. Application

| Check | Status | Evidence |
|---|---|---|
| Frontend starts | **Passed** | Production build exit 0; container healthy; HTTP 200 on published port 3100 |
| Backend starts | **Passed** | Container healthy; 42 routes registered; `/health/ready` connected |
| Authentication works | **Passed** | Live registration returned a token; 11 auth tests pass |
| PDF uploads work | **Passed** | Live 202 upload through the containerized API |
| PDF text extraction works | **Passed** | Live document reached `ready`; pages endpoint returns text |
| RAG retrieval works | **Passed** | Unit tests rank the matching clause; hybrid mode asserted |
| Groq integration with valid credentials | **Blocked** | No API key in this environment; endpoint correctly returns 503 |
| Answers contain valid citations | **Passed (contract)** | Citation validation tests; live model output not exercised |
| Conversation history works | **Passed** | Streaming test persists user + assistant messages and reloads them |
| Policy comparison works | **Passed** | Live comparison detected differing sum insured with evidence |
| Voice input works | **Not tested** | Browser speech recognition; implementation present, unsupported state handled |
| All UI controls functional | **Passed (reviewed)** | No placeholder buttons; each action calls a real endpoint |

## B. Database

| Check | Status | Evidence |
|---|---|---|
| Database starts | **Passed** | `postgres:16-alpine` healthy |
| Migrations work | **Passed** | `alembic upgrade head` ran at API container start |
| Models match migration | **Passed (reviewed)** | Single initial revision created from the models; schema compared by inspection |
| CRUD operations work | **Passed** | Register, upload, insights, comparison, conversation in the smoke test |
| Relationships work | **Passed** | Cascading deletes asserted for documents; conversations load messages/citations |
| Persistent storage | **Passed** | Named volumes for `pgdata` and `uploads`; stack restarts with data |

## C. Docker

| Check | Status | Evidence |
|---|---|---|
| All containers start | **Passed** | db, api, web all healthy |
| Health checks pass | **Passed** | `pg_isready`, `/health/ready`, web fetch |
| Database persistence | **Passed (configuration)** | Named volume mounted; not tested across a full host restart |
| Application connectivity | **Passed** | API reaches db; web serves; browser API base URL documented |
| Environment variables load | **Passed** | Compose values applied; `/meta` reflects configuration |

## D. Quality

| Check | Status | Evidence |
|---|---|---|
| No broken imports | **Passed** | `from app.main import app` succeeds; 42 routes |
| No critical runtime errors | **Passed** | Smoke test completed without 5xx except the intentional 503 |
| No exposed credentials | **Passed** | `.env` untracked; only `.env.example` with empty key; no secret in git |
| No placeholder UI | **Passed (reviewed)** | Every button has a handler and endpoint |
| No broken routes | **Passed** | All 13 frontend routes build; navigation targets exist |
| No dead buttons | **Passed (reviewed)** | Copy, regenerate, feedback, delete, upload, compare all wired |
| Documentation matches implementation | **Passed (reviewed)** | Routes, env vars, limits and known gaps documented from code |
| Mandatory tests pass | **Passed** | ruff 0, pytest 0, typecheck 0, Vitest 0, build 0 |

## E. Git

| Check | Status | Evidence |
|---|---|---|
| At least 40 meaningful commits | **Passed** | 88 commits at report time (76 added after the audited baseline of 12) |
| Clean working tree | **Passed after final commit** | Reports committed; `git status --porcelain` empty |
| No generated junk committed | **Passed** | `node_modules`, `.next`, `.venv`, uploads, logs and test DBs ignored |
| No secrets committed | **Passed** | Checked tracked files for `.env` and key patterns |
| Conventional commit subjects | **Passed** | `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `style:`, `ci:` |
| No AI attribution or Codebuff mention | **Passed** | Subjects only, no trailers |

One process note: an early commit titled `style: format backend with ruff` also carried a staged
`git mv` of the legacy requirements file. The move is correct; the subject is narrower than the
change. It was not amended because the repository rules forbid rewriting history.

## F. Resolved critical issues from the initial audit

| Original issue | Resolution |
|---|---|
| Retired hardcoded fallback model | Models are configuration; verified identifiers documented |
| README model mismatch | README rewritten from the implementation |
| Insights from a 6,000-character prefix | Whole-document, page-aware rule extraction with optional verified enrichment |
| Page provenance lost in chunking | Chunks carry page range and heading; citations use them |
| Keyword fallback returned irrelevant chunks | Non-matching chunks are dropped; no-evidence path is explicit |
| Streamlit-only, no persistence or accounts | FastAPI + PostgreSQL + Next.js with per-user isolation |
| No citation verification | Server-side verbatim validation; invalid citations dropped |
| Silent embedding fallback | Retrieval mode is reported; no false semantic claim |
| No upload validation | Magic bytes, size, encryption and page limits |
| No tests, CI, Docker | 55 backend tests, 7 frontend tests, CI workflow, Compose stack |

## G. Unresolved issues and known gaps

1. **Account deletion leaves PDF files on disk.** Database rows cascade; storage files are not swept.
2. **No email delivery.** Password reset returns the token only outside production.
3. **Rate limiting is per process.** Two Uvicorn workers maintain independent counters.
4. **No browser end-to-end tests.** Playwright is not implemented; UI verification is build-level.
5. **No AI quality benchmark.** Retrieval and faithfulness are not measured on a labelled corpus.
6. **No live provider run.** Chat was verified with a fake LLM and the 503 path; a real key is needed
   to exercise Groq end to end.
7. **OCR path unverified.** Requires Tesseract and a scanned PDF.
8. **Web host port 3000 blocked by an unrelated process** in this environment; verified on 3100.
9. **No screenshots committed.** The UI is implemented but was not captured; nothing was fabricated.
10. **Test database schema bypasses Alembic.** Tests create tables from models, so migration/model
    drift is not automatically detected.

## H. CI/CD remediation (2026-11-07)

### Original failure

The `Backend (lint + tests)` job of GitHub Actions run `42010011699` failed while loading the test
fixtures:

```
ImportError while loading conftest '.../backend/tests/conftest.py'.
backend/tests/conftest.py:32: in <module>
    from app.db.session import engine
E   ModuleNotFoundError: No module named 'app'
```

### Root cause

Not the working directory: the workflow already set `defaults.run.working-directory: backend`, and
`backend/app/__init__.py` exists. The difference was the interpreter invocation.

* pytest's prepend import mode inserts the test file's first non-package parent on `sys.path`. Because
  `backend/tests/` has no `__init__.py`, that path is `backend/tests`, never `backend`.
* The bare `pytest` console script does **not** add the current directory to `sys.path`.
* `python -m pytest` **does** add the cwd (`backend/`) to `sys.path[0]`.

Local verification used `python -m pytest`, CI used `pytest`, so the same code imported `app` locally
and failed on the runner. Reproduced locally with `backend/.venv/Scripts/pytest.exe -q` before the
fix: identical traceback at `tests/conftest.py:32`.

### Fix

1. `backend/pyproject.toml`: `pythonpath = ["."]` under `[tool.pytest.ini_options]` puts the package
   root on `sys.path` for every invocation mode, without any `sys.path` hack in `conftest.py`.
2. CI runs `python -m pytest -q` from `backend/`, matching the documented local command.
3. Added the missing `backend/app/ai/__init__.py` so `app.ai` is a regular package like its siblings.
4. Registered `unit` / `integration` markers with `--strict-markers` and split the suite into two CI
   jobs.

### Re-verification

| Check | Status | Evidence |
|---|---|---|
| Bare `pytest -q` from `backend/` | **Passed** | 55 passed after the fix (previously ImportError) |
| `python -m pytest -q` | **Passed** | 55 passed, exit 0 |
| Unit marker | **Passed** | 22 passed, 33 deselected |
| Integration marker | **Passed** | 33 passed, 22 deselected |
| `ruff check app tests` | **Passed** | exit 0 |
| Migration chain | **Passed** | `upgrade head` → `downgrade base` → `upgrade head` on SQLite, exit 0 |
| Model/migration drift | **Passed** | `alembic check`: no new upgrade operations detected |
| Frontend | **Passed** | typecheck exit 0; 7 tests; production build exit 0 |
| Docker images | **Passed** | `insurio-api` and `insurio-web` built; image import and `alembic upgrade head` verified |
| Compose stack | **Passed** | `docker compose config --quiet` valid; db/api/web all healthy |
| Containerized smoke test | **Passed** | register, upload, ready ingestion (3 chunks), pages, 20 insight fields, comparison (5 differences), ownership 404, PDF download 200, delete 200 |
| Chat against live Groq | **Blocked** | No API key here; the endpoint correctly returns `503 llm_not_configured` |
| New GitHub Actions run | **Passed** | [Run 42390594919](https://github.com/teja05-45/Insurio/actions/runs/42390594919) on `2935a5f`: all 7 jobs succeeded (lint, 22 unit, 33 integration, frontend typecheck/7 tests/build, Docker API build, Docker web build, compose config) |

### Known limitations after remediation

- Docker jobs are gated on all backend and frontend jobs, so they run only when those succeed; that is
  intentional, not a skip.
- CI does not exercise a real PostgreSQL instance; migrations are verified against SQLite in CI and
  PostgreSQL via container startup locally.
- The test suite still creates its schema from models rather than Alembic; `alembic check` covers drift
  when run manually.

## I. Verdict

The application is structurally complete, builds, passes its automated checks, and works end to end
for accounts, uploads, extraction, insights, comparison and ownership isolation. Chat is
contractually verified but not exercised against a live provider here. The gaps above are explicit
and mostly deployment-related; none are hidden behind a passing test.
