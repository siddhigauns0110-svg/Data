# AI Customer Support Intelligence API

A portfolio-grade starter backend for support ticket triage and knowledge-grounded answer drafting.

## Features
- FastAPI REST API and interactive Swagger docs.
- Automatic ticket category, priority, sentiment, and escalation signals.
- SQLite by default; PostgreSQL via DATABASE_URL.
- TF-IDF knowledge retrieval and a no-key local answer fallback.
- Optional OpenAI-powered RAG answer drafting.
- Ticket analytics, persistent tickets and conversations.
- API-key protection and automated tests.

## Run locally (Python 3.10+)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Copy .env.example to .env (PowerShell: Copy-Item .env.example .env)
uvicorn src.main:app --reload
```
Open http://127.0.0.1:8000/docs. Default development key: `local-dev-key`; replace it before deployment. Send it as `X-API-Key`.

## Example
```bash
curl -X POST http://127.0.0.1:8000/tickets -H "Content-Type: application/json" -H "X-API-Key: local-dev-key" -d '{"customer_email":"alex@example.com","subject":"API returns 401","message":"Urgent: our API integration is blocked after token rotation."}'
```

Ask: POST `/assistant/ask` with `{"question":"How do I rotate an API token?","conversation_id":"demo"}`.

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | /health | Health check |
| POST | /tickets | Create and classify ticket |
| GET | /tickets/{id} | Retrieve ticket |
| GET | /analytics/overview | Ticket metrics |
| GET/POST | /knowledge-base/articles | List or add articles |
| POST | /assistant/ask | Retrieve sources and draft answer |

## Environment
See `.env.example`. For PostgreSQL set `DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/support_ai`.

## Tests
```bash
pytest -q
```

## Engineering roadmap
1. Replace TF-IDF with sentence-transformer embeddings and a vector store.
2. Add document chunking, ingestion jobs, and retrieval evaluation.
3. Add role-based access, rate limits, audit logs, CI and monitoring.
4. Add model-quality and latency benchmarks.

**Honest limitations:** The ticket classifier is a rules-based baseline, not a trained ML model. TF-IDF retrieval is lexical. LLM output can be wrong and should be reviewed. Never send private customer data to a third-party model without appropriate approval. This is a learning/portfolio MVP, not a production deployment.
