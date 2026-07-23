# PolyGlotAI Task Tracker

Use this file as the main project checklist for turning PolyGlotAI Research Assistant into a polished portfolio and master's application project.

## Current Status

- [x] FastAPI backend scaffolded.
- [x] Streamlit frontend added.
- [x] React frontend added.
- [x] PDF upload and text extraction added.
- [x] Document chunking added.
- [x] Multilingual language configuration added.
- [x] RAG question answering flow added.
- [x] Source citations added.
- [x] Translation flow added.
- [x] Session memory added.
- [x] Summarization flow added.
- [x] Qdrant vector search integration added.
- [x] Local fallback behavior documented.
- [x] User guide, demo script, and evaluation plan added.

## Next Priority Tasks

- [ ] Run the app from a fresh terminal using `scripts/start_local.ps1`.
- [ ] Upload one clean research paper PDF and confirm document indexing works.
- [ ] Ask five English questions and verify citations are shown.
- [ ] Ask the same questions in Malayalam, Hindi, and Japanese.
- [ ] Record whether each answer used vector retrieval or lexical fallback.
- [ ] Add one sample demo PDF or demo dataset for repeatable presentations.
- [ ] Improve React UI polish for a portfolio demo.
- [ ] Add screenshots or a short demo video to the README.
- [ ] Write a short project summary for GitHub and resume use.

## Language And Translation Tasks

- [ ] Finalize the first official language list.
- [ ] Verify language codes in `config/languages.json`.
- [ ] Verify provider-specific translation codes in `config/translation_language_codes.json`.
- [ ] Test Malayalam translation with technical AI terms.
- [ ] Test Hindi translation with technical AI terms.
- [ ] Test Japanese translation with research-paper vocabulary.
- [ ] Compare Google translation, LLM translation, and any future NLLB option.
- [ ] Add translation examples to the demo script.

## RAG And Citation Tasks

- [ ] Create a small gold test set of questions and expected source passages.
- [ ] Add automated retrieval metrics such as Recall@5.
- [ ] Add citation integrity tests for unsupported claims.
- [ ] Improve answer generation when only fallback mode is available.
- [ ] Add a side-by-side view of answer and source passage in the React UI.

## Memory And Agent Tasks

- [ ] Separate document memory from user/session memory.
- [ ] Add user preference memory for preferred answer language and answer style.
- [ ] Add a router that detects Q&A, summary, translation, and general assistant requests.
- [ ] Plan a future LangGraph workflow with research, citation-checking, translation, and memory nodes.
- [ ] Add a citation verifier step before showing final answers.

## Japanese Master's Application Tasks

- [ ] Add a Japanese research-paper reading mode.
- [ ] Add bilingual English-Japanese summaries.
- [ ] Add glossary extraction for technical Japanese vocabulary.
- [ ] Add flashcard export for important terms.
- [ ] Write a project motivation section connecting PolyGlotAI to multilingual NLP research.

## Deployment Tasks

- [ ] Confirm Docker Compose starts backend, Qdrant, Streamlit, and React.
- [x] Add `.env.example` notes for OpenAI, Ollama, and fallback mode.
- [x] Add production deployment notes.
- [x] Add production Docker Compose file with persistent volumes.
- [x] Add production environment template.
- [ ] Prepare GitHub repository description and tags.
- [ ] Add license and contribution notes if the repository will be public.
