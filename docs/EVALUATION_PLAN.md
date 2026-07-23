# PolyGlotAI Evaluation Plan

This document defines how to evaluate PolyGlotAI Research Assistant as an NLP/RAG portfolio project. The goal is not only to show that the app runs, but to demonstrate measurable behavior across retrieval, summarization, translation, citations, and multilingual usability.

## Evaluation Goals

1. Verify that uploaded PDFs are parsed, chunked, indexed, and retrieved correctly.
2. Check that answers are grounded in document passages and include visible citations.
3. Measure whether cross-lingual retrieval works, for example a Tamil or Hindi question retrieving relevant English document chunks.
4. Compare translation quality across supported methods where available: Google translation, LLM translation, and NLLB.
5. Confirm that language-specific tokenization is respected, especially Japanese and other languages without simple whitespace word boundaries.
6. Confirm that the assistant remains usable with the no-key fallback mode, while documenting how answer quality improves with OpenAI or Ollama.

## Priority Languages

The first manual evaluation round focuses on:

| Code | Language | Reason |
| --- | --- | --- |
| ml | Malayalam | Home-language comfort and regional accessibility. |
| hi | Hindi | High-impact Indian language with broad user base. |
| ta | Tamil | Major South Indian language and cross-lingual retrieval check. |
| kn | Kannada | Major South Indian language and Indic script validation. |
| ja | Japanese | Important for Japanese academic/research preparation. |
| ko | Korean | East Asian non-Latin script retrieval check. |
| fr | French | Globally common academic language. |
| es | Spanish | Globally common language and useful translation baseline. |

The complete language registry is config-driven in `config/languages.json`.

## Feature-Level Success Criteria

| Feature | Success metric | Minimum target |
| --- | --- | --- |
| PDF ingestion | Valid PDF upload creates document metadata and page previews. | 100% for clean text PDFs under configured size limit. |
| Chunking | Chunks preserve readable spacing and page metadata. | No broken word-joining in English/Indic text; citations retain page numbers. |
| Retrieval | Relevant chunks appear in top-k results for known questions. | At least 3 of 5 manually prepared questions retrieve relevant chunks in top 5. |
| Cross-lingual retrieval | Non-English query retrieves relevant English passages. | Hindi, Tamil, Kannada, Japanese test questions retrieve the expected topic. |
| Answer generation | Answer is useful, explanatory, and grounded. | Each factual claim should be supported by at least one citation marker. |
| Summarization | Summary captures document purpose, method, and key points. | No one-word or unrelated summaries for resumes, papers, and notes. |
| Translation | Technical terms are preserved or explained. | RAG, embeddings, retrieval, citation, and model names remain understandable. |
| Memory | Current session history remains available. | Session message count updates and follow-up questions keep context. |
| UI | New user can upload, ask, summarize, translate, and inspect QA. | All core actions visible without reading backend details. |

## Manual Test Set

Use at least three document types:

1. A real research paper PDF.
2. A resume/CV PDF.
3. A lecture-note or textbook-style PDF.

For each document, run these questions:

| Question type | Example |
| --- | --- |
| Overview | What is this document about? Explain it clearly. |
| Contribution | What is the main contribution or purpose? |
| Method | What method, workflow, or approach is described? |
| Evidence | What evidence, results, or examples support the claims? |
| Limitations | What limitations or missing details can you infer from the document? |

For multilingual checks, translate one question into each priority language and compare whether retrieval still finds the same source passages.

Record the API `retrieval_mode` for every RAG result:

- `vector`: Qdrant vector retrieval was used.
- `lexical_fallback`: vector retrieval was unavailable or empty, so local lexical search was used. Do not count this as successful cross-lingual retrieval.
- `overview_bypass`: document-order chunks were used for an overview answer. Useful for demos, but do not count it as vector retrieval.

## Translation Comparison

For each priority target language:

1. Translate a technical sentence from English.
2. Translate a short research abstract-style paragraph.
3. Compare outputs from available methods.
4. Record whether technical terms are preserved, transliterated, or incorrectly translated.

Suggested sentence:

```text
The RAG system retrieves source passages before generating a cited answer.
```

## Citation Integrity Checklist

Every answer should be checked for:

- Citation markers such as `[C1]`, `[C2]`, or equivalent source labels.
- Source list with filename and page number.
- Source excerpts that match the answer.
- No citation markers attached to unsupported claims.
- No hidden backend metadata such as tokenizer strategy shown to normal users.

Use `grounding_verified=true` and `citation_confidence=high` or `partial` only when the answer contains inline source markers that match retrieved source IDs. Treat `retrieved_context` as context shown to the model, not proof that a claim was cited.

## Reporting Format

Use this format when recording manual results:

| Date | Document | Language | Feature | Retrieval mode | Grounding | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | paper.pdf | hi | RAG Q&A | vector | verified/partial/none | Pass/Needs work | Relevant citations appeared in top 3. |

## Next Evaluation Improvements

- Add a small gold dataset of questions and expected source chunks.
- Add automated retrieval metrics such as Recall@5 and MRR.
- Add translation metrics such as COMET or chrF for prepared examples.
- Add side-by-side comparison of embedding models.
- Add a saved demo dataset for repeatable portfolio presentations.
