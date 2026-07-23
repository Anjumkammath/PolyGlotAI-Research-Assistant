# PolyGlotAI React Frontend

This is the Phase 11 React interface for PolyGlotAI Research Assistant. It connects to the same FastAPI backend as the Streamlit interface.

## Local Development

Install dependencies:

```powershell
npm.cmd install
```

Start the React frontend:

```powershell
npm.cmd run dev
```

Open:

```text
http://127.0.0.1:5173
```

The backend must also be running at:

```text
http://127.0.0.1:8000
```

## Build

```powershell
npm.cmd run build
```

## Environment

Create a local `.env` file if the backend URL is different:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Included Workflows

- Upload and prepare PDFs.
- Ask cited questions about uploaded documents.
- Summarize documents with source citations.
- Translate technical text.
- Inspect language quality readiness and manual QA cases.
