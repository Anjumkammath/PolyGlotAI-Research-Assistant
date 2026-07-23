# PolyGlotAI Research Assistant

PolyGlotAI Research Assistant is a multilingual research-paper assistant. It can ingest PDFs, search the most relevant passages, answer questions with citations, translate text, and keep conversation memory by session.

This first version is intentionally practical: you can run it locally with a no-key fallback, then upgrade it with OpenAI or Ollama when you want higher quality answers.

New to the app? Start with the [User Guide](USER_GUIDE.md).

## What It Does

- Upload and index research PDFs.
- Ask questions about indexed papers.
- Retrieve source passages through multilingual embeddings when Qdrant is available, with explicit fallback warnings when local lexical search is used.
- Return cited sources separately from retrieved context, with file name, page number, and excerpt.
- Translate text between English, Malayalam, Hindi, Japanese, other Asian languages, and popular global languages.
- Keep lightweight conversation memory in SQLite.
- Run through Streamlit locally or through Docker Compose.

## Tech Stack

- Backend: Python, FastAPI
- Frontend: Streamlit
- RAG: PDF extraction, chunking, embeddings, vector search
- Embeddings: config-driven SentenceTransformers models, including multilingual MiniLM, multilingual MPNet, and multilingual E5
- Vector database: Qdrant
- Translation: `deep-translator`
- Memory: SQLite
- Optional LLM providers: OpenAI or Ollama

## Project Structure

```text
backend/
  app/
    main.py              FastAPI app and endpoints
    core/config.py       Environment settings
    models/schemas.py    Request and response models
    services/            PDF, RAG, vector, memory, LLM, translation logic
frontend/
  streamlit_app.py       Simple user interface
frontend-react/
  src/                   React interface for the same FastAPI backend
  Dockerfile             Production React container
storage/
  uploads/               Uploaded PDFs
  extracted/             Extracted text and prepared chunks
  qdrant/                Qdrant vector database data when using Docker
tests/
docker-compose.yml
```

## Local Setup

Create a virtual environment, install dependencies, and copy the example environment file.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-backend.txt -r requirements-frontend.txt
Copy-Item .env.example .env
```

Start the backend, Streamlit frontend, and React frontend:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_local.ps1
```

The app will open minimized PowerShell windows. Keep them open while using the assistant.

Open either frontend:

```text
Streamlit: http://127.0.0.1:8501
React:     http://127.0.0.1:5173
```

To stop the local servers:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\stop_local.ps1
```

If you prefer starting each process manually, start the backend:

```powershell
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

For local vector search, Qdrant must also be running at:

```text
http://localhost:6333
```

In another terminal, start the frontend:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run frontend/streamlit_app.py
```

For the React frontend:

```powershell
cd frontend-react
npm.cmd install
npm.cmd run dev
```

## Using an LLM

The default `LLM_PROVIDER=fallback` lets the app run without API keys. It returns relevant source passages instead of a polished generated answer.

To use OpenAI, set these in `.env`:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

To use Ollama, run Ollama locally and set:

```text
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434
```

## Evaluation And Demo Materials

- [Evaluation Plan](docs/EVALUATION_PLAN.md): how to test RAG, citations, translation, and multilingual retrieval.
- [Demo Script](docs/DEMO_SCRIPT.md): a walkthrough for interviews, portfolio videos, and master's application demos.
- [Phase 10 QA Report](docs/PHASE_10_QA_REPORT.md): current readiness checklist and manual QA cases.
- [Deployment Guide](docs/DEPLOYMENT.md): production Docker Compose, environment variables, storage, and deployment checks.

## Docker

For local Docker testing, copy the development environment file first:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Docker Compose starts Qdrant, the FastAPI backend, the Streamlit frontend, and the React frontend. Then open:

```text
Streamlit: http://localhost:8501
React:     http://localhost:5173
```

For production-style deployment, use the separate production compose file:

```powershell
Copy-Item .env.production.example .env.production
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
```

See [Deployment Guide](docs/DEPLOYMENT.md) before exposing the app publicly. The production setup uses persistent Docker volumes and keeps Qdrant bound to localhost by default.

## API Endpoints

- `GET /health`
- `GET /languages`
- `GET /evaluation/language-quality`
- `GET /memory/status`
- `GET /sessions`
- `GET /sessions/{session_id}`
- `DELETE /sessions/{session_id}`
- `DELETE /sessions`
- `GET /embeddings/models`
- `POST /embeddings/compare`
- `POST /documents/upload`
- `POST /documents/{document_id}/chunks`
- `GET /documents/{document_id}/chunks`
- `POST /documents/{document_id}/index`
- `POST /vectors/search`
- `POST /chat`
- `POST /summarize`
- `GET /translation/methods`
- `POST /translate`
- `POST /translate/compare`

FastAPI docs are available at:

```text
http://localhost:8000/docs
```

## Language Expansion

The current language list is in `config/languages.json`, and translation-provider codes are in `config/translation_language_codes.json`. Adding a language means adding a config entry rather than changing application logic.

Current enabled languages include:

- Indian languages: Malayalam, Hindi, Tamil, Telugu, Kannada, Bengali, Marathi, Gujarati, Punjabi, Urdu, Odia, and Assamese.
- Asian languages outside India: Japanese, Korean, Chinese Simplified, Indonesian, Thai, and Vietnamese.
- Global languages: English, Arabic, Spanish, French, German, Portuguese, Russian, Italian, Turkish, and Persian.

Japanese uses the `sudachipy` tokenizer strategy. Install `requirements-backend.txt` before testing Japanese PDFs so `sudachipy` and `sudachidict_core` are available. If those packages are missing, the backend now raises a clear tokenizer setup error instead of silently falling back to weak character or regex splitting.

## Embedding Models

Embedding models are configured in `config/embedding_models.json`.

Current options:

- `multilingual-minilm`: fast baseline for local development.
- `multilingual-mpnet`: stronger multilingual semantic similarity baseline.
- `multilingual-e5-large`: retrieval-focused model with `query:` and `passage:` formatting.

The Streamlit app includes an Embeddings tab for small comparison experiments.

## RAG Q&A

The chat flow uses Qdrant retrieval before answer generation when the document is indexed and Qdrant is reachable. If vector retrieval fails, the response reports `retrieval_mode=lexical_fallback` instead of pretending cross-lingual retrieval succeeded. Overview-style questions can use `retrieval_mode=overview_bypass` for a better document-level explanation.

A user can search across all indexed papers or select one indexed document as the search scope. Responses include:

- cited source IDs such as `C1`
- file name and page number
- retrieved excerpt
- similarity score when available
- selected answer style: `auto`, `short`, `detailed`, `beginner`, or `technical`
- document type hint such as research paper, study notes, resume/CV, or generic document
- `retrieval_mode`, `retrieval_warning`, `grounding_verified`, and `citation_confidence`

The fallback mode now produces structured source-grounded answers for common question types, including definitions, overviews, study notes, and resumes/CVs. With OpenAI or Ollama configured, the assistant synthesizes a more fluent answer while still requiring inline citation markers for verified citations.

Important honesty note: `citations` means passages explicitly referenced by inline markers like `[C1]`. `retrieved_context` means passages that were retrieved and shown to the model, whether or not the final answer cited them. This is marker-level citation tracking, not full sentence-level evidence verification.

## Memory

The app keeps short-term conversation memory per session in SQLite. Each stored turn includes:

- role and message content
- answer language
- active document scope when used
- small metadata such as retrieval count and translation status

Memory is visible from the Streamlit sidebar. Users can start a new session, inspect recent session messages, or clear the current session memory.

Long-term memory is intentionally separate from document retrieval. The planned Qdrant `memory` collection will store user preferences and recurring research context later, without mixing personal memory vectors into the `documents` collection.

## Summarization

The app can generate cited summaries from prepared document chunks.

Supported summary types:

- `short`: concise bullet-style overview.
- `detailed`: section-style student-friendly overview.
- `technical`: problem, method, data, metrics, results, and limitations when available.
- `bilingual`: target-language summary that preserves useful technical terms.

Summaries use source chunks from the uploaded PDF and return citations with page numbers and excerpts.

## Translation

Translation is method-aware and configurable.

Current translation methods:

- `google`: fast general translation through `deep-translator`.
- `llm`: context-aware technical translation through the configured OpenAI or Ollama provider.
- `nllb`: optional dedicated NLLB-200 machine translation path.

Translation language codes are configured in `config/translation_language_codes.json`. NLLB loads lazily only when selected.

## Suggested Portfolio Roadmap

1. Phase 1: PDF upload, RAG search, citations, Streamlit interface.
2. Phase 2: Better answer generation with OpenAI or Ollama.
3. Phase 3: Translation quality evaluation for Malayalam, Hindi, Japanese, and other target languages.
4. Phase 4: Agent workflow with separate research, citation-checking, translation, and memory agents.
5. Phase 5: React frontend with user accounts, saved libraries, document folders, and deployment.
6. Phase 6: Japanese-focused features for your master's journey, such as paper vocabulary extraction, bilingual summaries, and JLPT-style glossary cards.

## Agent Ideas for Later

- Research agent: plans searches across uploaded papers.
- Citation verifier: checks every answer sentence against retrieved passages.
- Translator agent: produces bilingual answers and glossary notes.
- Memory agent: remembers user goals, preferred languages, and recurring research topics.
- Study agent: turns Japanese papers into summaries, flashcards, and thesis-reading notes.
