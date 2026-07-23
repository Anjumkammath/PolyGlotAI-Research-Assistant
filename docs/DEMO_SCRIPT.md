# PolyGlotAI Demo Script

Use this script for portfolio walkthroughs, job interviews, and master's application demos. The demo should show the project as an applied multilingual NLP system, not only as a UI.

## 1. Opening Pitch

PolyGlotAI Research Assistant is a multilingual research assistant that reads PDFs, answers questions in the user's language, summarizes documents, translates technical content, and shows the source passages behind its answers.

Tagline:

```text
A multilingual research assistant that reads your papers, answers in your language, and always shows its work.
```

## 2. What To Open

Start with either UI:

- Streamlit version: `http://127.0.0.1:8501`
- React version: `http://127.0.0.1:5173` during local development

Keep the backend running at:

```text
http://127.0.0.1:8000
```

## 3. Demo Flow

### Step 1: Show the language support

Open the language or QA area and explain:

- Languages are not hardcoded in the UI.
- They are loaded from `config/languages.json`.
- Japanese uses a Japanese-aware tokenizer strategy.
- The project supports Indian languages, East Asian languages, and globally popular languages.

### Step 2: Upload a PDF

Upload a research paper or a clean lecture-note PDF.

Say:

```text
The backend extracts text page by page, prepares chunks, stores metadata, and indexes the chunks for retrieval.
```

### Step 3: Ask an English question

Ask:

```text
What problem does this paper solve? Explain the method and evidence.
```

Expected behavior:

- The answer should be more than one sentence.
- The answer should cite source chunks.
- Source passages should be visible.

### Step 4: Ask a multilingual question

Ask a Hindi, Tamil, Kannada, Malayalam, or Japanese version of:

```text
What is the main contribution of this paper?
```

Expected behavior:

- The retrieval should still find relevant document chunks.
- The answer should appear in the selected answer language.
- Citations should remain visible.

### Step 5: Show summarization

Generate a short and detailed summary.

Explain:

```text
The summary is source-grounded. It uses selected document chunks and returns citations so the user can trace where the summary came from.
```

### Step 6: Show translation

Translate:

```text
The RAG system retrieves source passages before generating a cited answer.
```

Try Malayalam, Hindi, Japanese, Korean, French, and Spanish.

Explain:

```text
The translation module is separate from RAG so the project can compare general LLM translation against dedicated machine translation models such as NLLB.
```

### Step 7: Show Language QA

Open the Language QA tab/section.

Say:

```text
This part turns the app into a measurable research project. It lists priority languages, expected tokenizer strategies, translation readiness, and manual evaluation cases.
```

## 4. Strong Interview Talking Points

- The project separates document vectors from future memory vectors.
- It uses multilingual embeddings so a non-English query can retrieve English document chunks.
- It keeps language support config-driven instead of hardcoded.
- It treats Japanese tokenization as a real NLP issue, not a UI checkbox.
- It includes an evaluation plan, not only a demo interface.
- It has both Streamlit and React frontends connected to the same FastAPI backend.

## 5. Known Limitations To Mention Honestly

- The no-key fallback mode is useful for local testing but less fluent than a real LLM.
- Translation quality depends on the selected provider.
- Scanned PDFs need OCR, which is planned as a later extension.
- Automated retrieval and translation scoring are planned after the manual QA baseline.

## 6. Closing Line

```text
This project connects my interests in multilingual NLP, information retrieval, translation, and human-centered AI tools for research access.
```
