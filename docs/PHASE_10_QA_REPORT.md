# Phase 10 QA Report

Status: Implementation ready, manual quality evaluation not yet completed

Phase 10 focuses on making PolyGlotAI presentable as a serious NLP/RAG project. The code now exposes a language-quality report through the backend and a visible Language QA section in the UI.

## Implemented Checks

| Area | Status | Notes |
| --- | --- | --- |
| Priority language registry | Configured | Malayalam, Hindi, Tamil, Kannada, Japanese, Korean, French, and Spanish are covered in the QA plan. This is configuration coverage, not retrieval quality evidence. |
| Translation code coverage | Configured | Priority languages have Google and NLLB code mappings. Translation quality still needs manual or metric-based evaluation. |
| Embedding readiness | Configured | Priority languages are marked as embedding-supported. Cross-lingual retrieval accuracy has not been measured yet. |
| Japanese tokenizer strategy | Configured, dependency-sensitive | Japanese is configured with `sudachipy`; real tokenization requires `sudachipy` and `sudachidict_core` to be installed. |
| Manual QA cases | Not yet evaluated | Cases cover translation, RAG, chunking, answer quality, and citation integrity, but results have not been recorded. |
| Backend endpoint | Implemented | `/evaluation/language-quality` returns the readiness/manual QA report. |
| Streamlit visibility | Implemented | The Language QA tab displays the report for users. |

## Manual QA Cases To Run

| ID | Category | Source | Target | Purpose |
| --- | --- | --- | --- | --- |
| translation-technical-terms | translation | en | ml | Preserve RAG and citation terms. |
| translation-research-summary | translation | en | hi | Preserve multilingual embedding terminology. |
| rag-tamil-query | rag | ta | en | Retrieve English chunks from a Tamil query. |
| rag-kannada-query | rag | kn | en | Retrieve method and limitation passages from a Kannada query. |
| japanese-tokenization | chunking | ja | en | Confirm Japanese-aware tokenizer strategy. |
| korean-cjk-retrieval | rag | ko | en | Check Korean query retrieval. |
| french-answer-style | answer_quality | en | fr | Check beginner-friendly French answer with citations. |
| spanish-citation-integrity | citation | en | es | Confirm citations remain visible in Spanish answer. |

## Current Automated Test Result

```text
53 passed
```

Automated tests are unit and smoke tests. They verify the response fields, fallback behavior, citation separation, tokenizer dependency handling, and service plumbing. They do not prove multilingual retrieval quality or translation quality on real documents.

Japanese tokenizer spot check after installing `sudachipy` and `sudachidict_core`:

```text
TOKENS: これ | は | 研究 | 論文 | です | 。 | 手法 | を | 説明 | し | ます | 。 | 結果 | と | 限界 | も | 述べ | ます | 。
```

## Recommended Manual Result Table

| Date | Case ID | Document | Result | Notes |
| --- | --- | --- | --- | --- |
| YYYY-MM-DD | rag-tamil-query | sample-paper.pdf | Not run | Add result after manual testing. |
| YYYY-MM-DD | rag-kannada-query | sample-paper.pdf | Not run | Add result after manual testing. |
| YYYY-MM-DD | spanish-citation-integrity | sample-paper.pdf | Not run | Add result after manual testing. |

Do not present this report as evidence that cross-lingual retrieval or Japanese tokenization "works" until this table contains real results from real documents.

## Next Improvement

The next research step is to convert these manual cases into a small gold evaluation dataset with expected source chunks. That would allow measuring retrieval quality with Recall@5 and MRR.
