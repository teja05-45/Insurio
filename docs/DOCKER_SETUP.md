# Docker Setup

## 1. Services

| Service | Image | Port | Health |
|---|---|---|---|
| `db` | `postgres:16-alpine` | 5432 | `pg_isready` |
| `api` | built from `backend/Dockerfile` | 8000 | `/health/ready` |
| `web` | built from `frontend/Dockerfile` | 3000 | HTTP `/` |

Volumes: `pgdata` for PostgreSQL, `uploads` mounted at `/data/uploads` in the API.

## 2. Start

```bash
cp .env.example .env      # optional; Compose has development defaults
docker compose up --build -d
docker compose ps
```

Expected:

```
NAME          IMAGE                SERVICE   STATUS                   PORTS
insurio-api-1   insurio-api        api       Up (healthy)             0.0.0.0:8000->8000/tcp
insurio-db-1    postgres:16-alpine db        Up (healthy)             0.0.0.0:5432->5432/tcp
insurio-web-1   insurio-web        web       Up                       0.0.0.0:3000->3000/tcp
```

The API container runs `alembic upgrade head` before Uvicorn, so the schema is created on first boot.
`web` waits for the API health check, and `api` waits for PostgreSQL.

## 3. Verify

```bash
curl http://localhost:8000/health/live     # {"status":"ok","version":"2.0.0"}
curl http://localhost:8000/health/ready    # {"status":"ok","database":"connected",...}
curl -I http://localhost:3000/             # 200
```

Open `http://localhost:3000`, register, upload a PDF, and watch processing in the workspace.

## 4. Logs and inspection

```bash
docker compose logs -f api
docker compose logs -f web
docker compose ps
docker compose exec db psql -U insurio -d insurio
# \dt                     list tables
# select status, count(*) from documents group by status;
# select version_num from alembic_version;
```

## 5. Configuration

Compose reads `.env` in the repository root. The important values:

| Variable | Effect |
|---|---|
| `SECRET_KEY` | Must be changed before any real deployment |
| `GROQ_API_KEY` | Enables chat; left empty by default |
| `EMBEDDING_PROVIDER` | `none` by default in Compose (no model download); set `auto` after installing ML extras in the image |
| `NEXT_PUBLIC_API_BASE_URL` | Baked into the browser bundle at image build time, so it must be the URL the browser can reach |
| `APP_ENV` | `development` keeps `/docs` enabled; `production` disables it and enforces a non-default secret |
| `POSTGRES_*`, `API_PORT`, `WEB_PORT` | Local port and credential overrides |

Rebuild the web image after changing `NEXT_PUBLIC_API_BASE_URL`:

```bash
docker compose build web && docker compose up -d web
```

## 6. Stop and reset

```bash
docker compose down            # stop, keep volumes
docker compose down -v         # also delete database and uploads
docker compose up --build -d   # fresh stack
```

## 7. Notes and limits

- The Compose defaults are for local evaluation. They use development credentials and a development
  secret; do not expose this stack to the internet without changing them and adding TLS.
- The API uses `--workers 2`. Rate limiting is per process, so limits apply per worker.
- PDFs are stored in the `uploads` volume, not object storage; back it up together with `pgdata`.
- The default image does not include ML extras, so retrieval runs BM25-only unless you extend
  `backend/Dockerfile` with `requirements-ml.txt`.
