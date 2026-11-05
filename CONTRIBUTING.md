# Contributing

## Setup

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm ci
npm run dev
```

Configuration: copy `.env.example` to `.env` (repository root or `backend/`). Never commit it.

## Before opening a pull request

```bash
cd backend && ruff check app tests && pytest -q
cd frontend && npm run typecheck && npm run test && npm run build
```

Report any check you could not run in the pull request description. Do not mark a check as passing
unless it was executed.

## Standards

- **Layering:** routes → services → repositories. Routes contain no SQL; services contain no ORM
  queries.
- **Authorization:** every user-facing read of a document-scoped resource must include the owner in
  the predicate. Use `OwnedDocument` / `OwnedConversation`.
- **Errors:** raise `AppError` with a stable `code`; never return provider or database exception text.
- **Grounding:** do not weaken citation validation or the insufficient-evidence path to make an answer
  look better.
- **Types:** Python is typed; TypeScript is strict. No new `any`.
- **UI:** use the design tokens and primitives; include loading, empty, error and success states.
- **Tests:** no network or paid API calls. Inject the fake LLM and hashing embedder.
- **Docs:** update the relevant file under `docs/` when behaviour or the schema changes.

## Commit messages

Conventional Commits, imperative, one logical change per commit. No attribution trailers in this
repository.

```
feat: compare policies field by field with evidence
fix: keep page numbers when a chunk spans sections
test: assert invented citations are dropped
docs: document the streaming protocol
```

## Pull request checklist

- [ ] The change is scoped to one concern.
- [ ] Tests cover the new behaviour or the bug.
- [ ] Lint, typecheck, tests and build pass (or failures are explained).
- [ ] No secrets, uploaded files, build output or generated junk are committed.
- [ ] Documentation is updated when contracts change.
- [ ] Security impact considered: ownership, uploads, prompts, error messages.

## Reporting security issues

Do not open a public issue for a vulnerability. Contact the maintainers privately with reproduction
steps and affected endpoints.
