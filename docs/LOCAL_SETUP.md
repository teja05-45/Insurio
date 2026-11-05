# Local Setup

## 1. Prerequisites

| Tool | Version used | Notes |
|---|---|---|
| Python | 3.11.9 (3.11–3.12 supported) | `python --version` |
| Node.js | 24 (20.9+ required) | `node --version` |
| npm | 11 | Ships with Node |
| PostgreSQL | 16 | Local install, or the Compose `db` service |
| Git | any | |

Optional: `requirements-ml.txt` for embeddings/OCR, and the Tesseract binary for OCR.

## 2. Backend

```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Create `backend/.env` (copy `.env.example` from the repository root). Minimum for local use:

```bash
APP_ENV=development
SECRET_KEY=dev-only-secret-replace-me-0123456789
DATABASE_URL=postgresql+psycopg://insurio:insurio@localhost:5432/insurio
UPLOAD_DIR=./data/uploads
CORS_ORIGINS=http://localhost:3000
GROQ_API_KEY=
```

Without `GROQ_API_KEY`, everything except chat works. To enable chat, create a key at
`https://console.groq.com/keys` and set `GROQ_MODEL` to a model that provider currently serves.

### Database

If PostgreSQL is not installed, start only the database from Compose:

```bash
docker compose up -d db
```

or create it manually:

```bash
createdb insurio
# or: psql -U postgres -c "CREATE ROLE insurio LOGIN PASSWORD 'insurio';"
#     psql -U postgres -c "CREATE DATABASE insurio OWNER insurio;"
```

Apply migrations:

```bash
alembic upgrade head
alembic current        # should print the head revision
```

### Run

```bash
uvicorn app.main:app --reload
```

Expected output includes `Uvicorn running on http://127.0.0.1:8000`. Verify:

```bash
curl http://localhost:8000/health/ready
# {"status":"ok","database":"connected","version":"2.0.0"}
```

API docs: `http://localhost:8000/docs` (disabled when `APP_ENV=production`).

## 3. Frontend

```bash
cd frontend
npm ci
cp .env.local.example .env.local     # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
npm run dev
```

Open `http://localhost:3000`. The API must allow that origin via `CORS_ORIGINS`.

## 4. First run

1. Register at `/register` (password ≥ 10 characters, with a letter and a number).
2. Upload a text-based PDF policy (≤ 20 MB, ≤ 400 pages).
3. Wait for `Ready` in the workspace; extraction and insights run in the background.
4. Open **Insights** for structured fields, or **Ask questions** for chat.
5. Compare requires two processed policies.

## 5. Checks

```bash
cd backend && ruff check app tests && pytest -q
cd frontend && npm run typecheck && npm run test && npm run build
```

## 6. Optional ML extras

```bash
pip install -r requirements-ml.txt   # fastembed, pytesseract, Pillow
# and set OCR_ENABLED=true plus EMBEDDING_PROVIDER=fastembed
```

Embeddings are attempted only when the provider is importable; otherwise retrieval reports
`bm25`. To force lexical mode deliberately, set `EMBEDDING_PROVIDER=none`.

## 7. Reset local state

```bash
rm -rf backend/data/uploads
alembic downgrade base && alembic upgrade head    # drops and recreates schema
```

Never run the downgrade against a database whose data you need.
