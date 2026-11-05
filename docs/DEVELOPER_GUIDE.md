# Developer Guide

## 1. Repository map

```
backend/            FastAPI service
  app/core/         settings, security, logging, errors, rate limit, middleware
  app/api/          deps.py + routes (HTTP only)
  app/schemas/      Pydantic contracts
  app/services/     business logic
  app/repositories/ SQL access
  app/models/       SQLAlchemy models
  app/ai/           retrieval and generation (no database imports)
  alembic/          migrations
  tests/            offline pytest suite
frontend/           Next.js application
  app/              routes (public + (app) authenticated group)
  components/       design system + feature components
  lib/              API client, auth context, types, formatting
docs/               product, architecture, operations
legacy/streamlit/   preserved original prototype (not part of the runtime)
```

## 2. Conventions

**Backend**

- Routes do not contain SQL or business rules. Resolve dependencies, call a service, return a schema.
- Raise `AppError(message, code=..., status_code=...)` for expected failures; the handler produces the
  standard envelope. Never return provider exception text.
- All user-facing reads go through an ownership predicate (`get_owned`, `OwnedDocument`,
  `OwnedConversation`).
- Keep the AI layer free of ORM imports. It accepts page/chunk objects with simple attributes.
- Timestamps are timezone-aware; use `datetime.now(UTC)`.
- Ruff selects `E,F,I,B,UP,S,C4,SIM`. Fix findings rather than adding ignores; per-file ignores exist
  only for documented false positives (token type labels, the development-secret sentinel).

**Frontend**

- TypeScript strict; no `any` in new code.
- Every authenticated page has loading, empty, error, and success states.
- Use the primitives in `components/ui.tsx`; do not hardcode colours or radii.
- Data access goes through `lib/api.ts` (refresh + retry + SSE live there only).
- Effects that fetch must update state after an `await` (the build's React Compiler lint enforces it).
- Icons are Lucide; icon-only controls need an accessible name.

## 3. Adding a backend feature

1. Model + migration (`alembic revision --autogenerate`).
2. Repository functions with owner scoping.
3. Pydantic request/response schemas.
4. Service function(s) with `AppError` for expected failures.
5. Route in `api/routes/`, registered in `main.py` if it is a new router.
6. Tests at the API boundary, plus unit tests for pure logic.
7. Documentation: `API.md`, and `DATABASE.md` if the schema changed.

## 4. Changing the AI pipeline

- Retrieval: `ai/retrieval.py` (BM25, RRF, filtering) and `ai/rerank.py`.
- Chunking: `ai/chunking.py` (parameters are function defaults, not settings).
- Prompt and context budget: `ai/prompts.py`.
- Grounding and streaming parse: `ai/pipeline.py`.
- Citation acceptance: `ai/citations.py`.
- Provider boundary: `ai/llm.py`; keep the `LLM` protocol so tests can inject `FakeLLM`.

Any change to citation or insufficient-evidence behaviour must update tests in
`tests/test_citations.py` and/or `tests/test_chat_api.py`.

## 5. Frontend data flow

```
page component → lib/api.ts → FastAPI
                      ↓
              refresh on 401 (single-flight)
                      ↓
              streamAnswer() async generator for chat
```

`lib/auth.tsx` owns user state and exposes `useAuth()`. `RequireAuth` blocks the `(app)` group until
the bootstrap request finishes.

## 6. Database changes

```bash
cd backend
alembic revision --autogenerate -m "describe change"
# review the generated file; autogenerate is a draft
alembic upgrade head
pytest -q        # SQLite creates schema from models, not migrations
```

`tests` create tables from `Base.metadata`, so a migration/model mismatch will not be caught by the
suite. Review migrations manually and test `upgrade head` against PostgreSQL when possible.

## 7. Testing requirements

- `ruff check app tests` and `pytest -q` must pass.
- Frontend: `npm run typecheck`, `npm run test`, `npm run build` must pass.
- Do not call paid APIs in tests; inject fakes.
- Never claim a check passed unless it ran.

## 8. Commit style

Conventional Commits, imperative, one logical change, no attribution trailers required by this
repository. Examples:

```
feat: stream grounded answers over SSE
fix: reject encrypted PDFs with an actionable error
test: cover citation validation against invented quotes
docs: document the retrieval ranking
```

## 9. Useful commands

```bash
# API with reload
cd backend && uvicorn app.main:app --reload

# OpenAPI JSON
curl http://localhost:8000/openapi.json | python -m json.tool | head

# Frontend dev
cd frontend && npm run dev

# Compose
docker compose up --build -d && docker compose logs -f api
```
