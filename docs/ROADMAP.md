# Roadmap

## Now (v2.0 baseline)

- Accounts with rotating refresh tokens and per-user isolation.
- PDF upload, page-accurate extraction, heading-aware chunking, optional OCR.
- Hybrid retrieval (BM25 + cosine + RRF) with heuristic reranking.
- Grounded streaming answers with server-validated citations and explicit insufficient evidence.
- Structured policy insights with quote, page, confidence and missing status.
- Deterministic multi-policy comparison with evidence.
- Document workspace, insights dashboard, comparison, settings, chat with voice input.
- Docker Compose, migrations, CI, offline test suite.

## Next (quality and operations)

1. **Email delivery** for password reset and verification; remove the development token response.
2. **Playwright end-to-end suite** covering register → upload → ask → citation → compare → delete.
3. **Evaluation harness** with a labelled policy corpus, retrieval recall, citation correctness and
   unsupported-claim sampling (see `docs/AI_EVALUATION.md`).
4. **Account deletion cleanup** of uploaded files, plus a storage usage report.
5. **Object storage** for uploads (S3-compatible) and virus scanning at ingress.
6. **Redis-backed rate limiting** and shared cache for multi-replica deployments.
7. **Observability**: metrics for upload duration, retrieval hits, citation rejection rate, LLM
   latency and errors; tracing across API → provider.
8. **Adversarial prompt-injection corpus** and a regression test that answers remain unchanged.

## Later (product depth)

- Cross-document chat ("which of my policies covers this?") with document-level routing.
- pgvector and approximate nearest neighbour for large corpora.
- Policy version diffing between renewals.
- Claim-pack generation from the policy's claim-document requirements.
- Team workspaces with roles (owner, analyst, viewer).
- Multi-language policies and answers.
- Mobile app or installable PWA with offline reading of extracted text.
- Export of insights and comparisons to PDF/CSV.

## Explicitly out of scope

- Selling insurance or quoting premiums.
- Adjudicating claims or predicting approval.
- Giving legal or medical advice.
- Training models on customer documents.
