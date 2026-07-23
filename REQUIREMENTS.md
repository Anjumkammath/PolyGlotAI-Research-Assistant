# PolyGlotAI Research Assistant - Requirements

## 1. Project Overview

PolyGlotAI Research Assistant is a multilingual AI research assistant for reading, querying, summarizing, translating, and discussing academic papers and technical PDFs. The project is designed as a flagship portfolio and research-oriented system for NLP/AI job applications and a Master's application in Japan.

The assistant will allow users to upload research papers or PDFs and then:

- Ask document-grounded questions using Retrieval-Augmented Generation (RAG).
- Receive answers with source citations from the uploaded documents.
- Generate summaries at different levels of detail.
- Translate text and answers across supported languages.
- Continue general assistant conversations with session memory.
- Support English, Malayalam, and Hindi initially.
- Add Japanese and additional Asian plus globally popular languages through configuration, not hardcoded logic.

The system will begin as a practical MVP using Streamlit and FastAPI, then grow into a more advanced multilingual research platform with a React frontend, a Qdrant-backed vector database, a router/orchestrator layer, dedicated translation models, and optional long-term memory.

## 2. Problem Statement

Research literature is still difficult to access for many multilingual users. Most academic papers are written in English, but students and researchers often think, search, and learn in their strongest language. A user may ask a question in Hindi or Malayalam about an English paper, expect an answer in Japanese for study purposes, or need a bilingual summary to compare technical terminology across languages.

This makes multilingual RAG a real NLP problem rather than a simple application feature. The system must retrieve semantically relevant document chunks even when the query and document are in different languages. It must generate answers that remain faithful to the source text, provide citations, preserve technical meaning during translation, and handle languages with different scripts and tokenization rules. Japanese is especially important because it does not separate words with whitespace, so naive English-centric chunking can damage retrieval quality.

PolyGlotAI Research Assistant explores these challenges through a full-stack system: multilingual embeddings, language-aware text processing, vector retrieval, citation-grounded answer generation, translation quality comparison, and memory-aware interaction.

## 3. Goals

### Primary Goals

- Build a working multilingual research assistant that can ingest PDFs and answer questions with citations.
- Support cross-lingual retrieval, where a query in one language can retrieve relevant content from documents in another language.
- Provide translation as a first-class module, not an afterthought.
- Keep language support configuration-driven through `languages.json`.
- Demonstrate practical understanding of NLP, RAG, embeddings, vector databases, FastAPI, frontend development, and deployment.

### Secondary Goals

- Compare embedding models for multilingual retrieval quality.
- Compare LLM-based translation with a dedicated machine translation model such as NLLB-200.
- Add memory while keeping document retrieval and user memory as separate vector collections.
- Prepare the project for a future React frontend and LangGraph-based agent orchestration.

## 4. Users and Use Cases

### Target Users

- Students reading research papers in AI, NLP, computer science, or related fields.
- Multilingual learners who want explanations in their preferred language.
- Researchers who need quick summaries and cited answers from PDFs.
- Master's applicants who want a study assistant for Japanese universities and technical papers.

### Core Use Cases

- Upload an English research paper and ask a question in Hindi.
- Upload a paper and request a Malayalam summary.
- Ask for a Japanese explanation of an English technical section.
- Translate an abstract from English into Japanese, Hindi, or Malayalam.
- Ask follow-up questions within the same session using short-term memory.
- Retrieve citations showing which page and passage supported an answer.

## 5. Core Features

### MVP Features

| Feature | Description | Priority |
| --- | --- | --- |
| PDF upload | User can upload one or more PDFs through the frontend. | P0 |
| Text extraction | Backend extracts page-wise text from PDFs. | P0 |
| Chunking | Documents are split into retrieval-friendly chunks with metadata. | P0 |
| Multilingual embeddings | Chunks and queries are embedded using a cross-lingual embedding model. | P0 |
| Vector retrieval | Relevant chunks are retrieved from Qdrant. | P0 |
| RAG answer generation | LLM generates answers grounded in retrieved chunks. | P0 |
| Citations | Answers include source file, page number, and passage references. | P0 |
| Basic summarization | User can request short, detailed, or section-wise summaries. | P1 |
| Translation | User can translate text or generated answers between supported languages. | P1 |
| Config-driven languages | Supported languages are defined in `languages.json`. | P1 |
| Streamlit frontend | Simple UI for upload, chat, summarize, and translate. | P1 |

### Stretch Features

| Feature | Description | Priority |
| --- | --- | --- |
| Intent router | Classify requests as Q&A, summarization, translation, or general chat. | P1 |
| Short-term memory | Keep conversation history for the current session. | P1 |
| Long-term memory | Store user preferences and past research context in a separate memory collection. | P2 |
| LangGraph orchestration | Upgrade simple routing to graph-based multi-step workflows. | P2 |
| Dedicated MT model | Add NLLB-200 translation and compare with LLM translation. | P2 |
| Japanese-aware chunking | Use fugashi/unidic-lite or SudachiPy for Japanese segmentation. | P2 |
| React frontend | Replace Streamlit with a production-style React frontend. | P2 |
| Evaluation dashboard | Track retrieval, citation, summarization, and translation metrics. | P3 |
| User accounts | Save libraries, preferences, and sessions per user. | P3 |

## 6. Out of Scope for v1

The following are explicitly out of scope for the first working version:

- Full user authentication and role-based access control.
- Paid SaaS billing, subscriptions, or usage quotas.
- Collaborative document annotation.
- Browser extension support.
- Fine-tuning a custom LLM.
- Training a custom embedding model from scratch.
- OCR for scanned PDFs.
- Audio input, speech output, or voice assistant features.
- Mobile apps.
- Multi-tenant production scaling.
- Guaranteed legal, medical, or financial advice.

## 7. System Architecture

### High-Level Architecture

```text
User
  |
  v
Frontend: Streamlit v1 / React v2
  |
  v
FastAPI Backend Gateway
  |
  v
Intent Router / Orchestrator
  |
  +--> RAG Pipeline
  |      PDF parsing -> language-aware chunking -> embeddings -> Qdrant retrieval -> LLM answer with citations
  |
  +--> Summarization Module
  |      document selection -> chunk aggregation -> map/reduce or section summary -> cited summary
  |
  +--> Translation Module
  |      LLM translation and/or NLLB-200 translation -> quality comparison
  |
  +--> General Assistant Module
         short-term memory -> optional long-term memory retrieval -> LLM response
```

### Frontend

The first version will use Streamlit because it allows rapid experimentation and simple local demos. The second version will move to React for a stronger portfolio presentation and better user experience.

#### Streamlit v1 Requirements

- Upload PDFs.
- Show indexed documents and metadata.
- Chat interface for document Q&A.
- Summary controls.
- Translation panel.
- Language selector.
- Citation display with page numbers and excerpts.
- Session ID or simple session state.

#### React v2 Requirements

- Modern document library interface.
- Chat panel with source citations.
- Side-by-side source viewer.
- Translation workspace.
- Saved conversations.
- Responsive layout.
- API integration with FastAPI.

### FastAPI Backend Gateway

FastAPI will expose the system through a clean API layer.

Required endpoints:

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/health` | GET | Check backend status. |
| `/languages` | GET | Return language configuration. |
| `/documents/upload` | POST | Upload and index PDFs. |
| `/documents` | GET | List uploaded/indexed documents. |
| `/chat` | POST | Ask questions or send general messages. |
| `/summarize` | POST | Summarize a document or selected pages. |
| `/translate` | POST | Translate text between supported languages. |
| `/sessions/{session_id}` | GET | Retrieve short-term session history. |

Backend responsibilities:

- Validate requests.
- Load language configuration.
- Store uploaded files.
- Coordinate document ingestion.
- Route user messages to the correct module.
- Return structured responses with citations and metadata.
- Keep document and memory storage separate.

## 8. Intent Router / Orchestrator

The orchestrator classifies each user request and routes it to the correct tool.

### Supported Intents

| Intent | Example | Route |
| --- | --- | --- |
| `document_qa` | "What is the main contribution of this paper?" | RAG pipeline |
| `summarize` | "Summarize this paper in Malayalam." | Summarization module |
| `translate` | "Translate this abstract to Japanese." | Translation module |
| `general_chat` | "Help me plan how to read this topic." | General assistant |

### v1 Router

Start with a simple LLM-based intent classifier that returns structured JSON:

```json
{
  "intent": "document_qa",
  "confidence": 0.92,
  "target_language": "hi",
  "requires_document_context": true
}
```

If the classifier confidence is low, the backend should fall back to a safe default:

- If documents are attached or selected, use `document_qa`.
- If the message contains translation language pairs, use `translate`.
- If the message asks for a summary, use `summarize`.
- Otherwise, use `general_chat`.

### Future LangGraph Upgrade

Later, replace the simple router with LangGraph. A graph-based workflow can support:

- Multi-step planning.
- Query rewriting.
- Retrieval validation.
- Citation verification.
- Translation quality checking.
- Memory read/write decisions.
- Human-in-the-loop correction.

## 9. RAG Pipeline Requirements

### Pipeline Steps

1. User uploads PDF.
2. Backend stores the original file.
3. PDF parser extracts page-wise text.
4. Language detector estimates dominant language per page or section.
5. Text is chunked using a language-aware strategy.
6. Chunks are embedded using a multilingual embedding model.
7. Chunks are stored in the Qdrant `documents` collection.
8. User asks a question.
9. Query is embedded using the same embedding model.
10. Qdrant retrieves top-k relevant chunks.
11. LLM generates an answer using retrieved chunks only.
12. Backend returns answer, citations, retrieved excerpts, page numbers, and confidence metadata.

### PDF Parsing

Supported in v1:

- Digital PDFs with extractable text.
- Academic papers, reports, lecture notes, and thesis chapters.

Out of scope in v1:

- Scanned PDFs requiring OCR.
- Handwritten notes.
- Complex tables as structured data.

Recommended libraries:

- `pypdf` for basic text extraction.
- `PyMuPDF` for stronger page-level extraction and layout metadata.
- Optional future OCR with Tesseract or cloud OCR.

### Chunking

Chunking must be language-aware. The system should not rely only on whitespace splitting.

General requirements:

- Preserve document metadata: document ID, filename, page number, section heading if available, language code, chunk index.
- Use overlapping chunks to preserve context.
- Keep chunks small enough for retrieval precision and LLM context windows.
- Track source page ranges for citations.

Recommended defaults:

| Parameter | v1 Target |
| --- | --- |
| Chunk size | 500-900 tokens or equivalent characters |
| Chunk overlap | 10-20 percent |
| Retrieval top-k | 5-8 chunks |
| Max answer context | 4-6 chunks |

### Japanese Tokenization Requirement

Japanese does not use whitespace between words, so naive whitespace chunking can split text poorly and reduce retrieval quality.

For Japanese text, use one of:

- `fugashi` with `unidic-lite`
- `SudachiPy`

The tokenizer strategy should be selected from language configuration:

```json
{
  "code": "ja",
  "name": "Japanese",
  "tokenizer_strategy": "sudachipy",
  "script_direction": "ltr",
  "enabled": true
}
```

The chunking module should choose the correct segmentation strategy based on `tokenizer_strategy`, not hardcoded language checks scattered throughout the codebase.

## 10. Embedding Requirements

Embeddings must be genuinely multilingual and cross-lingual. A Hindi query should retrieve the correct English document chunks if the meaning matches.

### Candidate Models

| Model | Strengths | Tradeoffs |
| --- | --- | --- |
| `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | Strong multilingual semantic similarity, easy SentenceTransformers integration, good baseline. | Moderate size, may be weaker than newer retrieval-specialized models. |
| `intfloat/multilingual-e5-large` | Strong multilingual retrieval performance, designed for query/document embedding patterns. | Larger model, slower inference, requires correct query/document prefixes. |

### Evaluation Requirement

The project should compare both models using the same multilingual retrieval test set.

Evaluation examples:

- English document, English query.
- English document, Hindi query.
- English document, Malayalam query.
- English document, Japanese query.
- Japanese document, English query.

Metrics:

- Recall@k
- Mean Reciprocal Rank (MRR)
- Top-1 accuracy
- Average retrieval latency
- Qualitative relevance score

### Embedding Format

For E5-style models, use the required prefixes:

```text
query: What is the main contribution of the paper?
passage: The paper proposes...
```

The embedding service should hide model-specific formatting behind a common interface.

## 11. Vector Database Requirements

Use Qdrant as the vector database.

### Collections

The system must keep document knowledge and user memory separate.

| Collection | Purpose |
| --- | --- |
| `documents` | Stores embedded chunks from uploaded PDFs. |
| `memory` | Stores optional long-term user preferences, recurring topics, and past document context. |

### Document Collection Payload

Each vector in `documents` should store:

```json
{
  "document_id": "uuid",
  "filename": "paper.pdf",
  "page_start": 3,
  "page_end": 4,
  "chunk_index": 12,
  "text": "retrieved passage text",
  "language": "en",
  "section_title": "Methodology",
  "created_at": "2026-07-13T00:00:00Z"
}
```

### Memory Collection Payload

Each vector in `memory` should store:

```json
{
  "user_id": "local-user",
  "session_id": "uuid",
  "memory_type": "preference",
  "text": "User prefers bilingual English-Japanese explanations.",
  "language": "en",
  "created_at": "2026-07-13T00:00:00Z"
}
```

### Retrieval Requirements

- Support filtering by document ID.
- Support filtering by user/session for memory.
- Return top-k chunks with scores.
- Return source metadata for citations.
- Keep memory retrieval optional and separate from document retrieval.

## 12. Translation Module Requirements

Translation should be a dedicated module, not just a prompt inside the main chat flow.

### Translation Methods to Compare

| Method | Use Case | Strengths | Risks |
| --- | --- | --- | --- |
| LLM-based translation | Explanatory translation, technical paraphrasing, bilingual summaries. | Fluent, context-aware, can explain terms. | May paraphrase too much or alter technical meaning. |
| NLLB-200 | Direct machine translation across many languages. | Strong multilingual coverage, dedicated MT model. | Larger model, may require GPU for speed, less explanatory. |

### Translation API Requirements

The translation endpoint should accept:

```json
{
  "text": "Transformer models use self-attention.",
  "source_language": "en",
  "target_language": "ja",
  "method": "llm"
}
```

The response should include:

```json
{
  "translated_text": "...",
  "source_language": "en",
  "target_language": "ja",
  "method": "llm",
  "quality_notes": null
}
```

### Translation Evaluation

Evaluate translation quality using:

- Human review for technical faithfulness.
- Back-translation checks.
- Terminology preservation tests.
- BLEU or chrF for controlled sentence pairs.
- Side-by-side comparison between LLM and NLLB-200.

Priority language pairs:

- English -> Hindi
- Hindi -> English
- English -> Malayalam
- Malayalam -> English
- English -> Japanese
- Japanese -> English

## 13. Memory System Requirements

Memory must be split into two distinct layers.

### Short-Term Memory

Short-term memory stores the conversation buffer for the current session.

Requirements:

- Store recent user and assistant messages.
- Keep a configurable maximum message count or token budget.
- Use short-term memory for follow-up questions.
- Clear or reset memory when a new session starts.
- Store in application memory or SQLite for v1.

Example:

```json
{
  "session_id": "uuid",
  "messages": [
    {"role": "user", "content": "Summarize the methodology."},
    {"role": "assistant", "content": "The methodology..."}
  ]
}
```

### Long-Term Memory

Long-term memory is optional/stretch. It stores durable user preferences and recurring research context.

Requirements:

- Store long-term memory in the Qdrant `memory` collection.
- Never mix memory vectors with document vectors.
- Store only useful, user-approved or system-inferred preferences.
- Allow deleting or resetting memory.
- Retrieve memory only when relevant.

Examples:

- Preferred answer language.
- Interest in NLP and Japanese research.
- Preference for bilingual summaries.
- Previously studied topics.

## 14. Language Configuration

Language support must be config-driven through a `languages.json` file.

Adding a new language should not require changing backend routing, chunking, or UI code. The application should load the language list and behavior from configuration.

### Required Fields

```json
[
  {
    "code": "en",
    "name": "English",
    "native_name": "English",
    "enabled": true,
    "script_direction": "ltr",
    "tokenizer_strategy": "whitespace",
    "translation_supported": true,
    "embedding_supported": true,
    "family": "global"
  },
  {
    "code": "ml",
    "name": "Malayalam",
    "native_name": "Malayalam",
    "enabled": true,
    "script_direction": "ltr",
    "tokenizer_strategy": "indic",
    "translation_supported": true,
    "embedding_supported": true,
    "family": "indian"
  },
  {
    "code": "hi",
    "name": "Hindi",
    "native_name": "Hindi",
    "enabled": true,
    "script_direction": "ltr",
    "tokenizer_strategy": "indic",
    "translation_supported": true,
    "embedding_supported": true,
    "family": "indian"
  },
  {
    "code": "ja",
    "name": "Japanese",
    "native_name": "Japanese",
    "enabled": true,
    "script_direction": "ltr",
    "tokenizer_strategy": "sudachipy",
    "translation_supported": true,
    "embedding_supported": true,
    "family": "east_asian"
  }
]
```

### Initial Languages

| Code | Language | Priority | Tokenizer Strategy |
| --- | --- | --- | --- |
| `en` | English | P0 | `whitespace` |
| `ml` | Malayalam | P0 | `indic` |
| `hi` | Hindi | P0 | `indic` |
| `ja` | Japanese | P1 | `sudachipy` or `fugashi` |

### Later Expansion

Candidate later languages:

- Tamil
- Telugu
- Kannada
- Bengali
- Korean
- Chinese Simplified
- Indonesian
- Thai
- Vietnamese
- Arabic
- Spanish
- French
- German

## 15. Summarization Requirements

The assistant should support multiple summary types.

| Summary Type | Description |
| --- | --- |
| Short summary | 5-8 bullet points. |
| Detailed summary | Section-wise explanation of the paper. |
| Technical summary | Focus on methods, datasets, models, metrics, and limitations. |
| Bilingual summary | Summary in target language plus key English terms. |
| Japanese study summary | Japanese explanation with important technical vocabulary. |

Summaries should include citations when possible, especially for claims about methods, results, or limitations.

For long documents, summarization should use a map-reduce or hierarchical strategy:

1. Summarize chunks or sections.
2. Merge section summaries.
3. Produce final summary with citations.

## 16. Non-Functional Requirements

### Performance Targets

| Operation | Target for v1 |
| --- | --- |
| Backend health check | Under 300 ms |
| Small PDF upload, under 20 pages | Under 30 seconds after model warm-up |
| Medium PDF upload, 20-60 pages | Under 2 minutes after model warm-up |
| Q&A response | Under 8 seconds with cloud LLM |
| Q&A response with local LLM | Under 20 seconds |
| Translation short text | Under 5 seconds with LLM or lightweight MT |
| Vector retrieval | Under 1 second for small local collections |

### File Requirements

| Requirement | v1 Target |
| --- | --- |
| Supported file type | PDF |
| Max PDF size | 25 MB |
| Max pages per PDF | 100 pages |
| Text extraction | Digital text PDFs only |
| Multiple documents | Supported after MVP ingestion is stable |

### Concurrency Targets

| Environment | Expected Users |
| --- | --- |
| Local development | 1 user |
| Portfolio demo | 1-5 concurrent users |
| Small deployed demo | 5-20 concurrent users |

### Reliability Requirements

- Failed PDF ingestion should return a clear error.
- Unsupported language requests should return a structured validation error.
- Missing citations should be treated as a response quality issue.
- The system should not hallucinate citations.
- If retrieval confidence is low, the assistant should say that the uploaded documents may not contain enough information.

### Security and Privacy Requirements

- Do not commit uploaded PDFs to Git.
- Do not commit API keys.
- Store secrets in `.env`.
- Validate file type and size before ingestion.
- Keep user memory deleteable.
- Avoid sending private documents to external APIs unless the user configures that provider knowingly.

## 17. Full Tech Stack

| Layer | v1 Choice | v2 / Stretch Choice | Purpose |
| --- | --- | --- | --- |
| Frontend | Streamlit | React | User interface |
| Backend | FastAPI | FastAPI | API gateway and orchestration |
| Data validation | Pydantic | Pydantic | Request and response schemas |
| PDF parsing | pypdf / PyMuPDF | PyMuPDF + OCR option | Extract document text |
| Chunking | Custom Python service | Language-aware chunking framework | Prepare text for retrieval |
| Japanese tokenization | fugashi/unidic-lite or SudachiPy | SudachiPy with configurable modes | Japanese sentence/word segmentation |
| Embeddings | multilingual MPNet or multilingual E5 | Evaluated best model | Cross-lingual semantic retrieval |
| Vector DB | Qdrant | Qdrant Cloud or self-hosted | Store document and memory vectors |
| LLM | OpenAI / local Ollama model | Provider-agnostic LLM layer | Answer generation and routing |
| Translation | LLM translation | NLLB-200 comparison | Multilingual translation |
| Short-term memory | SQLite or in-memory buffer | Redis or database-backed sessions | Session context |
| Long-term memory | Qdrant `memory` collection | Qdrant with memory policies | User preferences and durable context |
| Deployment | Docker Compose | Cloud deployment | Reproducible running environment |
| Testing | Pytest | Pytest + evaluation harness | Functional and NLP evaluation |
| Documentation | Markdown | GitHub Pages or docs site | Portfolio presentation |

## 18. Success Criteria and Evaluation Plan

### PDF Ingestion

Success criteria:

- Extract text from at least 90 percent of digital PDFs in the test set.
- Preserve page numbers for citations.
- Store chunks with correct document metadata.

Evaluation:

- Test with 10-20 academic PDFs.
- Manually inspect page-to-text alignment.
- Verify chunk counts and metadata.

### Retrieval

Success criteria:

- Relevant chunk appears in top 5 results for at least 80 percent of test questions.
- Cross-lingual retrieval works for Hindi, Malayalam, and Japanese queries against English documents.

Evaluation:

- Build a test set of question-answer pairs per document.
- Include one query set per target language.
- Compare `paraphrase-multilingual-mpnet-base-v2` and `intfloat/multilingual-e5-large`.

Metrics:

- Recall@5
- MRR
- Top-1 accuracy
- Retrieval latency

### RAG Answer Quality

Success criteria:

- Answers are grounded in retrieved context.
- Every factual answer includes citations.
- If context is insufficient, the assistant says so.

Evaluation:

- Human review on 30-50 questions.
- Score each answer for faithfulness, completeness, citation correctness, and clarity.

Suggested rubric:

| Score | Meaning |
| --- | --- |
| 5 | Fully correct, cited, complete, and clear. |
| 4 | Mostly correct with minor missing detail. |
| 3 | Partially correct but incomplete. |
| 2 | Weak answer or poor citation support. |
| 1 | Incorrect or hallucinated. |

### Summarization

Success criteria:

- Short summaries cover objective, method, result, and limitation.
- Technical summaries include models, datasets, metrics, and findings when available.
- Bilingual summaries preserve key technical terms.

Evaluation:

- Human review against paper abstracts and conclusions.
- Check whether summary claims are supported by source pages.

### Translation

Success criteria:

- Technical terms are preserved or explained.
- Meaning is not changed across translation.
- Japanese output is natural enough for study use.

Evaluation:

- Compare LLM translation and NLLB-200 on a fixed test set.
- Use human review for technical faithfulness.
- Use back-translation for sanity checks.
- Track chrF or BLEU where reference translations exist.

### Memory

Success criteria:

- Short-term memory supports follow-up questions in the same session.
- Long-term memory does not pollute document retrieval.
- User preferences can be reset.

Evaluation:

- Test multi-turn conversations.
- Confirm memory collection is separate from document collection.
- Check that irrelevant memory is not injected into answers.

### Router / Orchestrator

Success criteria:

- Correctly classifies at least 90 percent of common user requests in a test set.
- Routes ambiguous requests safely.
- Produces structured routing decisions.

Evaluation:

- Create 100 sample prompts across Q&A, summarize, translate, and general chat.
- Compare predicted intent to expected intent.

## 19. Phased Roadmap

### Phase 1 - Project Scaffolding

- Create repository structure.
- Add FastAPI backend.
- Add Streamlit frontend.
- Add `.env.example`, Docker files, README, and requirements.
- Add basic health endpoint.

Deliverable: A runnable empty application.

### Phase 2 - PDF Upload and Text Extraction

- Add PDF upload endpoint.
- Store uploaded PDFs locally.
- Extract page-wise text.
- Return extraction metadata.

Deliverable: Upload a PDF and view extracted page counts/text metadata.

### Phase 3 - Chunking and Metadata

- Implement chunking service.
- Preserve page numbers and document IDs.
- Add tokenizer strategy abstraction.
- Prepare for Japanese tokenization.

Deliverable: PDF text becomes structured chunks with metadata.

### Phase 4 - Qdrant Integration

- Add Qdrant Docker service.
- Create `documents` collection.
- Store chunk embeddings and payloads.
- Add retrieval endpoint for testing.

Deliverable: Search document chunks from Qdrant.

### Phase 5 - Multilingual Embeddings

- Add embedding provider interface.
- Implement multilingual MPNet baseline.
- Add multilingual E5 option.
- Add query/document formatting for E5.

Deliverable: Cross-lingual semantic retrieval works on sample questions.

### Phase 6 - RAG Q&A with Citations

- Build RAG answer endpoint.
- Retrieve top-k chunks.
- Generate answer with LLM.
- Return citations with page numbers and excerpts.

Deliverable: Ask questions about PDFs and receive cited answers.

### Phase 7 - Summarization

- Add summary endpoint.
- Support short, detailed, technical, and bilingual summaries.
- Add long-document map-reduce summarization.

Deliverable: Generate useful summaries from uploaded papers.

### Phase 8 - Translation Module

- Add translation endpoint.
- Implement LLM-based translation.
- Add NLLB-200 experimental implementation.
- Compare translation quality for target language pairs.

Deliverable: Translate text and compare translation methods.

### Phase 9 - Language Configuration

- Add `languages.json`.
- Move language settings out of hardcoded lists.
- Add tokenizer strategy loading.
- Add UI language selection from backend config.

Deliverable: New languages can be added through config.

### Phase 10 - Memory

- Add short-term session memory.
- Add optional long-term memory collection in Qdrant.
- Keep `documents` and `memory` collections separate.
- Add memory reset controls.

Deliverable: The assistant supports follow-up questions and preferences.

### Phase 11 - Intent Router and Agent Upgrade Path

- Add LLM-based intent classifier.
- Route to Q&A, summarize, translate, or general chat.
- Log routing decisions.
- Design LangGraph workflow for future upgrade.

Deliverable: One chat endpoint can handle multiple task types.

### Phase 12 - Evaluation, Deployment, and Portfolio Polish

- Build evaluation datasets.
- Add retrieval and routing metrics.
- Add Docker Compose deployment.
- Improve README with architecture diagrams and screenshots.
- Record demo workflow.
- Prepare final project write-up for GitHub and applications.

Deliverable: A portfolio-ready research project with measurable results.

## 20. API Response Requirements

All major backend responses should be structured and predictable.

### RAG Answer Response

```json
{
  "answer": "The paper proposes...",
  "target_language": "en",
  "citations": [
    {
      "citation_id": "C1",
      "document_id": "uuid",
      "filename": "paper.pdf",
      "page_start": 2,
      "page_end": 2,
      "excerpt": "The paper proposes...",
      "score": 0.86
    }
  ],
  "retrieval_model": "intfloat/multilingual-e5-large",
  "session_id": "uuid"
}
```

### Error Response

```json
{
  "error": {
    "code": "UNSUPPORTED_FILE_TYPE",
    "message": "Only PDF files are supported in v1.",
    "details": null
  }
}
```

## 21. Testing Requirements

### Unit Tests

- PDF extraction.
- Chunking.
- Language config loading.
- Tokenizer strategy selection.
- Embedding formatting.
- Router output parsing.
- Citation formatting.

### Integration Tests

- Upload PDF -> extract text -> chunk -> embed -> store in Qdrant.
- Query -> retrieve chunks -> generate cited answer.
- Translate text between supported languages.
- Use short-term memory in follow-up questions.

### Evaluation Tests

- Cross-lingual retrieval test set.
- Translation quality comparison set.
- Intent classification dataset.
- Citation correctness review.

## 22. Documentation Requirements

The GitHub repository should include:

- `README.md` with overview, screenshots, setup, and demo flow.
- `REQUIREMENTS.md` with this specification.
- `ARCHITECTURE.md` with diagrams and module details.
- `EVALUATION.md` with metrics, datasets, and results.
- `.env.example` for configuration.
- Clear instructions for local setup and Docker setup.
- A roadmap checklist.

## 23. Research Framing for Statement of Purpose

PolyGlotAI Research Assistant reflects my interest in multilingual NLP systems that make technical knowledge more accessible across language barriers. The project focuses on cross-lingual retrieval, citation-grounded generation, language-aware text processing, and translation quality, especially for users who study from English research literature while thinking or communicating in languages such as Malayalam, Hindi, and Japanese. Building this system gives me a practical way to explore research questions in multilingual representation learning, retrieval-augmented generation, and human-centered AI tools for education. This connects directly to my goal of pursuing graduate study in Japan, where I hope to deepen my understanding of NLP and contribute to AI systems that support multilingual learning and research.

