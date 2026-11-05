# Deployment

## 1. What must be provisioned

| Requirement | Purpose | Notes |
|---|---|---|
| PostgreSQL 16 | All durable state | Managed instance is fine; migrations run at API startup |
| Container host or PaaS | API and web images | Two services, one database |
| Persistent volume or object storage | Uploaded PDFs | `UPLOAD_DIR`; must survive restarts |
| Groq API key | Chat and optional insight enrichment | Absence degrades chat to 503, not a crash |
| TLS termination | Bearer tokens and documents | Reverse proxy or platform ingress |

## 2. Production checklist

1. Set `APP_ENV=production`. Startup fails if `SECRET_KEY` is still the development default.
2. Generate `SECRET_KEY` with `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
3. Set `CORS_ORIGINS` to the exact web origin. No wildcard.
4. Set `DATABASE_URL` with TLS if the database is remote (`?sslmode=require`).
5. Set `GROQ_API_KEY` and verify `GROQ_MODEL` against the provider's current model list.
6. Set `NEXT_PUBLIC_API_BASE_URL` to the public API URL **before building the web image**.
7. Mount a persistent volume at `/data/uploads` for the API.
8. Put the web app and API behind TLS; forward `X-Request-ID` and avoid buffering SSE
   (`proxy_buffering off` in Nginx, or `X-Accel-Buffering: no`, which the API already sends).
9. Configure database backups, including the uploads volume.
10. Decide on embeddings: install ML extras or deliberately run `EMBEDDING_PROVIDER=none`.

## 3. Nginx sketch

```nginx
server {
  listen 443 ssl;
  server_name insurio.example.com;

  location /api/ {
    proxy_pass http://api:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;          # required for SSE chat
    proxy_read_timeout 300s;
  }

  location / {
    proxy_pass http://web:3000;
    proxy_set_header Host $host;
  }
}
```

If the API is path-prefixed, `NEXT_PUBLIC_API_BASE_URL` must include the same prefix.

## 4. Scaling

- **Multiple API replicas:** move uploads to shared object storage and rate limiting to Redis first.
- **Worker separation:** ingestion is `BackgroundTasks`; move it to a queue when documents get large.
- **Database:** add indexes only from measured query plans; the current ones cover ownership lists.
- **SSE:** ensure the proxy and load balancer do not buffer or time out before the LLM finishes.

## 5. Health and readiness

- Liveness: `GET /health/live` (no database access).
- Readiness: `GET /health/ready` (database round trip).
- Web: `GET /` returns 200 once Next is serving.

Use these for orchestrator probes and deploy gates.

## 6. Limitations before a public launch

- No email provider: password reset tokens are only returned outside production.
- No object storage and no virus scanning.
- Account deletion leaves uploaded files on disk (database rows are removed).
- Rate limiting is per process.
- No automated backups or observability stack in the repository.
- No Playwright end-to-end suite; verification is unit/API/build level.

These are tracked in `docs/FINAL_AUDIT_REPORT.md` and `docs/ROADMAP.md`.
