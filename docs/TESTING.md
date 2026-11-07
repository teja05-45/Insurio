# Testing

## 1. Strategy

The default suite runs offline and free. It uses SQLite, the deterministic hashing embedder, and a
fake LLM, so no network call or paid token is required. Real Groq calls are never part of automated
tests.

| Layer | Tool | What it covers |
|---|---|---|
| Unit | pytest | Chunking, citation validation, retrieval ranking, rule extraction, comparison matrix |
| API integration | pytest + FastAPI TestClient | Auth, upload validation, ingestion, workspace, ownership, streaming chat, feedback, comparisons |
| Component | Vitest + Testing Library | Formatting helpers, status badges, button semantics |
| Build | `next build` | Type checking, route compilation, static generation |
| Static | ruff, `tsc --noEmit` | Backend lint, frontend types |

## 2. Commands

```bash
# Backend
cd backend
python -m venv .venv
pip install -r requirements-dev.txt
ruff check app tests
python -m pytest -q                 # 55 tests
python -m pytest -q -m unit         # 22 tests
python -m pytest -q -m integration  # 33 tests

# Frontend
cd frontend
npm ci
npm run typecheck
npm run test
npm run build
```

Backend commands must run from `backend/`. `pyproject.toml` contains `pythonpath = ["."]` and
`markers = [unit, integration]`, so bare `pytest` and `python -m pytest` resolve `app` the same way.
Markers are declared at module level in each test file (`pytestmark = pytest.mark.unit` or
`.integration`).

## 3. Test fixtures

`backend/tests/conftest.py` sets environment variables before importing the app:

- `DATABASE_URL` → temporary SQLite file, schema created from `Base.metadata`
- `UPLOAD_DIR` → temporary directory
- `EMBEDDING_PROVIDER=hashing` → deterministic vectors
- `GROQ_API_KEY=test-groq-key` → chat is considered configured, but the LLM is monkeypatched
- `RATE_LIMIT_ENABLED=false`

Tables are truncated after every test. PDFs are generated with PyMuPDF at runtime, so the repository
contains no binary fixtures. `FakeLLM` streams a canned JSON answer in small chunks; `parse_sse`
asserts the event sequence.

## 4. What is asserted

- Chunks retain page ranges and headings, never merge across a section, and deduplicate.
- A citation is accepted only if its quote is verifiably in the cited source; unknown source ids,
  invented quotes, and quotes under the minimum length are rejected.
- BM25 ranks a term-matching chunk first; hybrid mode is reported when embeddings exist; empty
  queries return nothing.
- Rule extraction finds sum insured and exclusions with page and quote; absent fields stay `missing`.
- Registration, duplicate email, weak password, wrong password, token rotation and reuse, logout,
  reset flow, profile update and sessions.
- Upload rejects non-PDF and empty bytes; a processed PDF reaches `ready`, exposes pages, download,
  insights and deletion; duplicate uploads are rejected; another user receives 404.
- Chat streams `meta → delta* → final`, persists citations, drops invented citations, returns an
  explicit insufficient-evidence answer, isolates conversations by owner, regenerates, records
  feedback, and lists message counts.
- Comparison requires two policies, rejects foreign documents, detects differing values, preserves
  evidence, and supports list/get/delete.

## 5. Execution results

Recorded in `docs/TEST_EXECUTION_REPORT.md` from actual runs in this environment, including commands
and exit codes. Summary from the last run:

| Suite | Result |
|---|---|
| `ruff check app tests` | Passed |
| `python -m pytest -q` | 55 passed (22 unit, 33 integration) |
| `npm run typecheck` | Passed |
| `npm run test` | 7 passed |
| `npm run build` | Passed |

## 5a. CI execution flow

`.github/workflows/ci.yml` runs these jobs on every push to `main` and every pull request:

| Job | Command | Depends on |
|---|---|---|
| `backend-lint` | `ruff check app tests` (from `backend/`) | — |
| `backend-unit` | `python -m pytest -q -m unit` | — |
| `backend-integration` | app import smoke test, then `python -m pytest -q -m integration` | — |
| `frontend` | `npm ci`, `npm run typecheck`, `npm run test`, `npm run build` | — |
| `docker-api` | `docker build ./backend`, import check, `alembic upgrade head` on a scratch SQLite DB | lint, unit, integration |
| `docker-web` | `docker build ./frontend` with the API base URL build arg, `server.js` check | frontend |
| `docker-compose` | `docker compose config --quiet` | lint, unit, integration, frontend |

No job uses `continue-on-error`; a failing lint, test, build or image build fails the workflow. Tests
need no repository secrets: the suite is offline and the Groq key is never read by CI.

End-to-end browser tests and Playwright are **not implemented**. No browser automation was run, and
that is reported as a limitation rather than a pass.

## 6. Not covered

- Real provider behaviour, latency, and quota errors (mocked by design).
- OCR accuracy (requires Tesseract and scanned fixtures).
- File deletion on account deletion (only document deletion is asserted).
- Concurrency and load behaviour.
- Visual regression and cross-browser layout.
- A labelled retrieval/faithfulness benchmark (see `docs/AI_EVALUATION.md`).

## 7. Adding tests

- Prefer a real route call over mocking the service layer; the API contract is what the frontend uses.
- Keep the suite network-free. Inject `FakeLLM` through `app.services.answering.build_pipeline`.
- Generate PDFs with `pytest` fixtures rather than committing binaries.
- If a test needs a new environment variable, set it in `conftest.py` before importing `app`.
