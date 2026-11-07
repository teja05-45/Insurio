# Test Execution Report

All results below were produced by commands run in this environment. Nothing is inferred from
documentation or from a previous revision.

## 1. Environment

| Item | Value |
|---|---|
| OS | Windows (Git Bash) |
| Python | 3.11.9 (project venv) |
| Node / npm | 24.15.0 / 11.12.1 |
| Next.js | 15.5.29 (upgraded from 15.1.6 after a vulnerability advisory) |
| Docker | 29.6.1, Compose v2 |
| Database in Docker | `postgres:16-alpine` |
| Groq API key | **Not provided** — live generation was not executed |

## 2. Backend

### Lint

```bash
cd backend
./.venv/Scripts/python.exe -m ruff check app tests
```

Result: **Passed** (exit 0). Output: `All checks passed!`

During the rebuild, ruff initially reported 45 findings. Real defects were fixed (a shadowed
`delete` import in `services/conversations.py`, a removed unused `ValidatedCitation` import, and
`getattr` misuse in `ai/types.py`), long lines were reformatted, and per-file ignores were added only
for three documented false positives: the development-secret sentinel and `token_type` labels flagged
as hardcoded passwords.

### Tests

```bash
cd backend
./.venv/Scripts/python.exe -m pytest -q
```

Result: **Passed** (exit 0). 55 test functions across 8 files:

| File | Tests | Area |
|---|---|---|
| `test_auth_api.py` | 11 | Registration, login, rotation, reset, profile, sessions |
| `test_documents_api.py` | 10 | Upload validation, ingestion, pages, insights, ownership, delete |
| `test_citations.py` | 9 | Verbatim validation, invented quotes, grounded answer parsing |
| `test_chat_api.py` | 8 | SSE stream, citations dropped, insufficient evidence, regenerate, feedback |
| `test_extraction.py` | 5 | Rule extraction, missing fields, comparison matrix |
| `test_chunking.py` | 4 | Page provenance, headings, deduplication |
| `test_comparison_api.py` | 4 | Two-policy comparison, ownership, library |
| `test_retrieval.py` | 4 | BM25 ranking, hybrid mode, empty query, top-k |

The suite is network-free: SQLite, the deterministic hashing embedder, and an injected `FakeLLM`.
Deprecation warnings from native dependencies (`swig`, `anyio`) are emitted but do not affect the
result.

## 3. Frontend

| Command | Result | Notes |
|---|---|---|
| `npm run typecheck` | **Passed** (exit 0) | `tsc --noEmit` |
| `npm run test` | **Passed** (exit 0) | 2 files, 7 tests |
| `npm run build` | **Passed** (exit 0) | 13 routes compiled |

Build output (first load JS):

```
○ /                    142 kB
ƒ /chat/[id]           163 kB
ƒ /documents/[id]      114 kB
ƒ /insights/[id]       220 kB
○ /dashboard           114 kB
○ /documents           113 kB
○ /compare             113 kB
○ /settings            111 kB
○ /login, /register, /forgot-password   113 kB
Shared JS              103 kB
```

The first production build failed type checking on a missing optional `error_message` field in the
client `Message` type. After adding the field, the build compiled but the bundled React Compiler lint
rejected several effects. Those were genuine style violations (synchronous `setState` in effect
bodies, a `Date.now()` in a render-reachable handler) and were fixed by deferring loads and using a
ref counter — not by disabling rules. The build then passed.

## 4. Docker

```bash
docker compose config -q          # valid
docker compose up --build -d      # images built, stack started
```

| Service | Observed status |
|---|---|
| `db` | Up (healthy), PostgreSQL 16 |
| `api` | Up (healthy), migrations applied on startup |
| `web` | Up (healthy) |

`GET http://localhost:8000/health/ready` returned:

```json
{"status":"ok","database":"connected","version":"2.0.0"}
```

The web container's host publishing on port 3000 could not bind because an unrelated process already
listens on that host port (PID 21536). Re-running with `WEB_PORT=3100` produced
`0.0.0.0:3100->3000/tcp`, status healthy, and `GET http://localhost:3100/` returned **200**. The
container itself always served 200 internally; the conflict is environmental, not a code defect.

## 5. End-to-end smoke test (containerized API)

Executed against the Compose API with no Groq key:

| Step | Result |
|---|---|
| Register a new account | Passed (access token returned, length 263) |
| Upload PDF A | Passed (202) |
| Poll processing | Passed — `DOC_A_STATUS=ready` |
| Structured insights | Passed — `sum_insured=found '500000' page 1` |
| Upload PDF B and compare | Passed — `differs=True`, values `['500000','1000000']` |
| Create conversation | Passed (201) |
| Ask a question without AI key | **503** `llm_not_configured` — the intended explicit failure |
| Foreign user reads document A | **404** — ownership isolation verified |
| Web root and `/login` | 200 (via published port 3100) |

## 6. Not tested (reported as limitations, not passes)

| Item | Status | Reason |
|---|---|---|
| Live Groq generation with a real key | **Blocked** | No API key available in this environment |
| Citation validation against a real model response | **Not tested live** | Covered by unit/API tests with a deterministic fake |
| OCR path | **Not tested** | Requires Tesseract binary and a scanned fixture |
| Playwright / browser end-to-end flows | **Not implemented** | No browser automation dependency installed |
| Visual regression and screenshots | **Not captured** | No screenshots are committed; none were fabricated |
| Voice input | **Not tested** | Requires a browser with speech recognition and a microphone |
| Account deletion file cleanup | **Known gap** | Database rows removed; files remain on the volume |
| Concurrency, load, and performance benchmarks | **Not measured** | No benchmark harness |
| Migration downgrade against PostgreSQL | **Not tested** | `upgrade head` verified via container startup |
| Email delivery of reset tokens | **Not implemented** | Token is returned only outside production |

## 7. Reproducing

```bash
cd backend && ruff check app tests && python -m pytest -q
cd ../frontend && npm run typecheck && npm run test && npm run build
cd .. && docker compose up --build -d
curl http://localhost:8000/health/ready
```

Set `GROQ_API_KEY` before starting the API to exercise chat with a live provider.

## 8. CI failure investigation and re-verification (2026-11-07)

### Original failure

GitHub Actions run `42010011699`, job `Backend (lint + tests)`:

```
ImportError while loading conftest.py
backend/tests/conftest.py:32
from app.db.session import engine
ModuleNotFoundError: No module named 'app'
```

### Root cause

The workflow already ran from `backend/` (`defaults.run.working-directory`), and `backend/app` is a
valid package. The failure came from how pytest builds `sys.path`: with prepend import mode it inserts
the first non-package parent of the test file (`backend/tests`, since `tests/` has no `__init__.py`),
and the bare `pytest` console script does not add the current directory. `python -m pytest` adds the
cwd, so local runs passed while CI failed.

Reproduction before the fix, from `backend/`:

```
$ .venv/Scripts/pytest.exe -q
ImportError while loading conftest '...\backend\tests\conftest.py'.
tests\conftest.py:32: in <module>
    from app.db.session import engine
E   ModuleNotFoundError: No module named 'app'
```

### Fix

- `backend/pyproject.toml`: added `pythonpath = ["."]`, `--strict-markers`, and the `unit` /
  `integration` marker definitions.
- Each test module declares `pytestmark = pytest.mark.unit` or `pytest.mark.integration`.
- CI now runs `python -m pytest -q` from `backend/`, split into a unit job and an integration job.
- Added the missing `backend/app/ai/__init__.py`.
- CI restructured into `backend-lint`, `backend-unit`, `backend-integration`, `frontend`, `docker-api`,
  `docker-web`, `docker-compose`, with Docker jobs gated on their prerequisites.

### Commands and results

| Command (from the stated directory) | Status | Result |
|---|---|---|
| `backend: .venv/Scripts/pytest.exe -q` | **Passed** | 55 passed (bare console script, the CI invocation shape) |
| `backend: python -m pytest -q` | **Passed** | 55 passed |
| `backend: python -m pytest -q -m unit` | **Passed** | 22 passed, 33 deselected |
| `backend: python -m pytest -q -m integration` | **Passed** | 33 passed, 22 deselected |
| `backend: ruff check app tests` | **Passed** | exit 0, `All checks passed!` |
| `backend: alembic upgrade head` / `downgrade base` / `upgrade head` (SQLite) | **Passed** | revision `456095a86652`, all exit 0 |
| `backend: alembic check` (SQLite) | **Passed** | no new upgrade operations detected |
| `frontend: npm ci` | **Passed** | exit 0 |
| `frontend: npm run typecheck` | **Passed** | exit 0 |
| `frontend: npm run test` | **Passed** | 2 files, 7 tests |
| `frontend: npm run build` | **Passed** | exit 0, 13 routes |
| `docker compose config --quiet` | **Passed** | valid |
| `docker compose build` | **Passed** | `insurio-api` and `insurio-web` built |
| `docker run insurio-api python -c "from app.main import app"` | **Passed** | `Insurio API 2.0.0` |
| `docker run insurio-api alembic upgrade head` (scratch SQLite) | **Passed** | revision applied |
| `docker run insurio-web node -e accessSync('server.js')` | **Passed** | standalone server present |
| `docker compose up -d` (`API_PORT=8100`, `WEB_PORT=3100`, `POSTGRES_PORT=55432`) | **Passed** | db, api, web all healthy |
| `GET :8100/health/live`, `/health/ready` | **Passed** | 200, database connected |
| `GET :3100/`, `/login` | **Passed** | 200 |

Containerized API smoke test against PostgreSQL (no Groq key):

| Step | Result |
|---|---|
| Two accounts registered | 201, tokens issued |
| Two PDFs uploaded | 202 |
| Ingestion reached ready | `ready`, 1 page, 3 chunks |
| Pages endpoint | 200, 195 chars on page 1 |
| Insights | 200, 20 fields |
| Comparison | 201, 5 differences |
| Conversation created | 201 |
| Chat without a key | 503 `llm_not_configured` (intended explicit failure) |
| Other user reads the document | 404 (ownership isolation) |
| PDF download | 200, `application/pdf`, 1011 bytes |
| Document delete | 200 |

### Not verified in this pass

- **Live Groq generation** — no API key; the fake-LLM API tests remain the evidence for the streaming
  and citation contract. **Blocked**, not passed.
- **GitHub-hosted run** — **Passed**. [Run 42390594919](https://github.com/teja05-45/Insurio/actions/runs/42390594919)
  on commit `2935a5f` completed with conclusion `success`; every job reported success:
  `Backend lint`, `Backend unit tests` (22 passed, 33 deselected), `Backend integration tests`
  (33 passed, 22 deselected), `Frontend (typecheck + tests + build)` (7 tests passed, production build),
  `Docker backend image` (build, app import, `alembic upgrade head`), `Docker frontend image`
  (build, `server.js` check) and `Docker Compose validation`.
- **PostgreSQL migration downgrade** — only verified on SQLite; upgrade verified on PostgreSQL through
  container startup.
- **OCR, voice input, browser E2E, visual regression, load tests** — unchanged from section 6.
