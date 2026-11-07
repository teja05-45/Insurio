# Troubleshooting

## Backend

| Symptom | Cause | Fix |
|---|---|---|
| `sqlalchemy.exc.OperationalError: connection refused` | PostgreSQL not running | `docker compose up -d db`; check `DATABASE_URL` host/port |
| `psycopg.OperationalError: password authentication failed` | Credentials mismatch | Align `POSTGRES_*` and `DATABASE_URL` |
| `alembic.util.exc.CommandError: Can't locate revision` | Database at an unknown revision | `alembic current`, then `alembic stamp head` only if the schema is known-good |
| `RuntimeError: SECRET_KEY must be set...` | `APP_ENV=production` with the default secret | Set a unique `SECRET_KEY` |
| `503 llm_not_configured` from chat | No `GROQ_API_KEY` | Set the key; upload/insights/comparison still work without it |
| `502 llm_unavailable` | Provider outage, bad model id, or quota | Check `GROQ_MODEL` against the provider's model list and the API logs |
| Document stuck at `queued` | Background task did not start | Check API logs for `document_processing_error`; the job row records the failure |
| `no_extractable_text` | Scanned PDF with OCR disabled | Enable `OCR_ENABLED=true` and install Tesseract, or upload a text PDF |
| `pdf_encrypted` | Password-protected PDF | Upload an unlocked copy |
| Upload returns 413 | File or page limit | Raise `MAX_UPLOAD_MB` / `MAX_PDF_PAGES` deliberately |
| 429 on upload/chat | Rate limit hit | Wait for the window, or adjust the limit for local testing |
| PDF preview blank in the browser | Blob fetch failed or CSP blocked it | Use **Open in new tab**; check the browser console and the API `content-type` |

## Frontend

| Symptom | Cause | Fix |
|---|---|---|
| Login succeeds but every request is 401 | Access token expired and refresh failed | Sign in again; check `/auth/refresh` in the network tab |
| `CORS` error in the console | Origin not allowlisted | Add the exact origin to `CORS_ORIGINS` |
| `NEXT_PUBLIC_API_BASE_URL` ignored | Env is inlined at build time | Rebuild (`npm run build`) after changing it |
| Dashboard shows "AI answers are not configured" | `/meta` reports no key | Expected without `GROQ_API_KEY` |
| Chat answer never appears | Proxy buffering SSE | Disable buffering; the API sends `X-Accel-Buffering: no` |
| `npm ci` fails | Lockfile out of sync | `npm install` to refresh `package-lock.json`, then commit it |
| `next build` fails on lint | React Compiler rules flag an effect | Keep the async/`await` pattern used in the codebase; see `docs/TESTING.md` |
| Port 3000/8000 already in use | Another process | Set `WEB_PORT`/`API_PORT`, or stop the process |

## Docker

| Symptom | Cause | Fix |
|---|---|---|
| `db` unhealthy | Existing incompatible volume | `docker compose down -v`, then start again |
| `api` exits immediately | Migration failure or bad env | `docker compose logs api`; verify `DATABASE_URL` |
| Web image points at the wrong API | URL baked at build | Rebuild `web` with the corrected build arg |
| Changes not visible | Old image | `docker compose up --build -d` |
| Uploads vanish after `down -v` | Volume removed | Do not use `-v` unless you intend to delete data |

## Tests

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'app'` while loading `tests/conftest.py` | Bare `pytest` inserts only `backend/tests` on `sys.path`; `python -m pytest` inserts the cwd, which masked the problem locally | Resolved in the repository: `pyproject.toml` sets `pythonpath = ["."]`, so any invocation from `backend/` works. Still run commands from `backend/` |
| CI backend job fails to import `app` but local tests pass | CI invoked the bare `pytest` console script while local runs used `python -m pytest` | Same fix; CI now runs `python -m pytest -q` from `backend/` |
| `pytest` reports `PytestUnknownMarkWarning` / unknown marker | Marker not registered | Add it to `markers` in `[tool.pytest.ini_options]`; `--strict-markers` turns unknown markers into errors |
| Tests hit the network | A test replaced the LLM incorrectly | Use the `fake_llm` fixture; never call Groq in tests |
| `greenlet`/`swig` deprecation warnings | Native dependency warnings | Harmless; the suite still exits 0 |
| Frontend tests fail to resolve `@/` | Vitest config not loaded | Run `npm run test` from `frontend/` |
