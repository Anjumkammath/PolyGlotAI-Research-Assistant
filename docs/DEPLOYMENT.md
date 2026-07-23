# PolyGlotAI Deployment Guide

This guide covers deployment preparation for PolyGlotAI Research Assistant. The recommended portfolio setup is:

- React frontend as the public demo UI.
- FastAPI backend as the API service.
- Qdrant as the vector database.
- Streamlit kept as an optional local/admin demo UI.

## Recommended Deployment Paths

| Path | Best for | Notes |
| --- | --- | --- |
| VPS with Docker Compose | Strong engineering portfolio demo | Runs React, FastAPI, Qdrant, and optional Streamlit together with persistent Docker volumes. |
| React static hosting + backend host + Qdrant Cloud | Polished public link | Use Vercel/Netlify-style hosting for React, a backend host for FastAPI, and managed Qdrant. |
| Local-only demo | Interviews and screen recordings | Use `scripts/start_local.ps1` for quick demos without public exposure. |

## Production Files Added

| File | Purpose |
| --- | --- |
| `.env.production.example` | Production environment template. Copy to `.env.production` before deployment. |
| `docker-compose.prod.yml` | Production-style Docker Compose with persistent volumes and health checks. |
| `backend/Dockerfile` | Backend image with `/health` container healthcheck. |

## VPS Docker Compose Deployment

1. Copy the production env template:

```powershell
Copy-Item .env.production.example .env.production
```

2. Edit `.env.production`.

Set these carefully:

```text
BACKEND_CORS_ORIGINS=https://your-frontend-domain.com
PUBLIC_API_BASE_URL=https://your-backend-domain.com
LLM_PROVIDER=fallback
OPENAI_API_KEY=
```

For an IP-based demo without HTTPS, use:

```text
BACKEND_CORS_ORIGINS=http://YOUR_SERVER_IP
PUBLIC_API_BASE_URL=http://YOUR_SERVER_IP:8000
```

3. Build and start the production stack:

```powershell
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
```

4. Check service health:

```powershell
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

5. Open:

```text
React frontend: http://YOUR_SERVER_IP
Backend health: http://YOUR_SERVER_IP:8000/health
FastAPI docs:   http://YOUR_SERVER_IP:8000/docs
```

Streamlit is optional. Start it only when needed:

```powershell
docker compose --env-file .env.production -f docker-compose.prod.yml --profile streamlit up --build -d
```

Then open:

```text
Streamlit: http://YOUR_SERVER_IP:8501
```

## Persistent Storage

The production compose file uses Docker volumes:

| Volume | Stores |
| --- | --- |
| `polyglotai_app_storage` | Uploaded PDFs, extracted pages, chunks, document index, SQLite memory. |
| `polyglotai_qdrant_data` | Qdrant vector collections. |

Do not remove these volumes unless you intentionally want to erase uploaded files, memory, and vectors.

Backup example:

```powershell
docker compose --env-file .env.production -f docker-compose.prod.yml stop
docker run --rm -v polyglotai_app_storage:/data -v ${PWD}:/backup alpine tar czf /backup/polyglotai_app_storage_backup.tar.gz /data
docker run --rm -v polyglotai_qdrant_data:/data -v ${PWD}:/backup alpine tar czf /backup/polyglotai_qdrant_backup.tar.gz /data
```

## Split Deployment

Use this path if you want React on static hosting and the backend elsewhere.

### React Frontend

Set this build variable:

```text
VITE_API_BASE_URL=https://your-backend-domain.com
```

Then build:

```powershell
cd frontend-react
npm.cmd ci
npm.cmd run build
```

Deploy `frontend-react/dist`.

### FastAPI Backend

The backend needs:

```text
APP_ENV=production
BACKEND_CORS_ORIGINS=https://your-frontend-domain.com
QDRANT_URL=https://your-qdrant-url
QDRANT_API_KEY=your-qdrant-key-if-managed
QDRANT_DOCUMENT_COLLECTION=documents_minilm_384
QDRANT_VECTOR_SIZE=384
EMBEDDING_MODEL=multilingual-minilm
LLM_PROVIDER=fallback
```

If using OpenAI:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o-mini
```

## Security Notes

- Do not expose Qdrant publicly without authentication. The production compose binds Qdrant to `127.0.0.1`.
- Use exact CORS origins in production.
- Do not upload private or sensitive PDFs to a public demo unless authentication is added.
- The current app has no user accounts. Public visitors share the same backend storage.
- Keep `MAX_PDF_SIZE_MB` conservative for free or low-resource hosting.
- `fallback` mode is safer for public demos without API-key cost, but generated answers are less fluent than OpenAI/Ollama.

## Required Post-Deploy Checks

| Check | Expected |
| --- | --- |
| `/health` | Returns `{"status":"ok"}`. |
| React UI loads | The public frontend appears without console API errors. |
| Upload PDF | Document metadata appears after upload. |
| Prepare chunks | Chunks are created and page metadata is retained. |
| Index document | Qdrant indexing succeeds. |
| Ask question | Response includes `retrieval_mode`, cited sources, or retrieved context warning. |
| Translate text | Translation endpoint returns the configured method. |
| Language QA | `/evaluation/language-quality` has `readiness_score=1.0` after tokenizer dependencies are installed. |

## Current Limitations To Mention In Portfolio

- Public deployment does not yet include authentication or per-user libraries.
- Uploaded files are stored on the backend server, not S3/object storage.
- Cross-lingual retrieval must be evaluated with a gold question/source dataset before claiming measured accuracy.
- Citation tracking verifies inline marker/source ID alignment, not full sentence-level entailment.
- OCR for scanned PDFs is out of scope for the current version.

## Troubleshooting

| Problem | Likely cause | Fix |
| --- | --- | --- |
| React loads but API calls fail | `PUBLIC_API_BASE_URL` points to the wrong backend URL or CORS is missing the frontend origin. | Update `.env.production`, rebuild React, restart compose. |
| Upload works but indexing fails | Qdrant is unavailable or collection vector size mismatches the embedding model. | Check backend logs and use model-specific collection names. |
| Japanese chunking fails | `sudachipy` or `sudachidict_core` missing in backend image/environment. | Rebuild backend after installing `requirements-backend.txt`. |
| Answers show fallback warning | Qdrant retrieval failed or the document was not indexed. | Start Qdrant, index the document, and retry. |
| Data disappears after redeploy | Deployment used ephemeral storage instead of persistent volumes. | Use Docker volumes or managed persistent storage. |

## Deployment Command Summary

```powershell
Copy-Item .env.production.example .env.production
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```
