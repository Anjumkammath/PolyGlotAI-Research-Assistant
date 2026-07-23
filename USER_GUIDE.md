# PolyGlotAI Research Assistant - User Guide

Welcome to PolyGlotAI Research Assistant. This guide is for new users who want to upload research papers, ask questions, summarize content, and translate text without needing to understand the technical system behind the app.

## 1. What This App Does

PolyGlotAI Research Assistant helps you work with research papers and PDFs.

You can use it to:

- Upload academic papers or technical PDFs.
- Ask questions about uploaded documents.
- Get answers with source citations.
- Summarize papers.
- Translate text or answers into another language.
- Continue a conversation in the same session.

The app is especially designed for multilingual research use. It currently supports English, major Indian languages such as Malayalam, Hindi, Tamil, Kannada, Telugu, Bengali, Marathi, Gujarati, Punjabi, Urdu, Odia, and Assamese, plus Japanese, Korean, Chinese, Southeast Asian languages, and globally popular languages such as Spanish, French, German, Portuguese, Russian, Italian, Turkish, Arabic, and Persian.

## 2. Who This Is For

This app is useful for:

- Students reading research papers.
- Beginners trying to understand academic writing.
- Multilingual users who prefer explanations in their own language.
- Researchers who want fast document search with citations.
- Master's applicants who want help studying papers, especially for NLP/AI topics.

## 3. Before You Start

For the best results, use PDFs that:

- Contain selectable text.
- Are not scanned images.
- Have clear page structure.
- Are research papers, reports, lecture notes, or thesis chapters.

The app may not work well with:

- Scanned PDFs.
- Handwritten notes.
- Very large books.
- PDFs where the text is stored as images.
- Complex tables, formulas, or diagrams that need visual interpretation.

## 4. Opening the App

When the app is running, open the frontend in your browser:

```text
http://localhost:8501
```

You should see the PolyGlotAI Research Assistant interface with:

- A document upload area.
- A chat or question area.
- A language selector.
- A translation section.
- A sidebar showing session information.

## 5. Uploading a PDF

To upload a paper:

1. Open the app.
2. Go to the paper upload section.
3. Choose a PDF file from your computer.
4. Click the button to index or process the PDF.
5. Wait until the app confirms that the PDF has been indexed.

Indexing means the app has:

- Read the PDF text.
- Split it into smaller searchable sections.
- Stored those sections so the assistant can search them later.

After indexing is complete, you can ask questions about the document.

## 6. Asking Questions

After uploading a paper, type a question in the assistant area.

Good examples:

```text
What is the main contribution of this paper?
```

```text
Summarize the methodology used in this study.
```

```text
What dataset did the authors use?
```

```text
Explain the limitations of this paper in simple language.
```

```text
Give me the answer in Hindi.
```

```text
Explain this paper in Japanese for a beginner.
```

For best results:

- Ask one clear question at a time.
- Mention the section you care about if you know it.
- Ask for a simple explanation if the paper is difficult.
- Ask follow-up questions in the same session.

### Choosing an Answer Style

The Ask screen includes an answer style selector:

- `Auto`: lets the assistant choose the right level of detail.
- `Short`: best for quick facts and definitions.
- `Detailed`: best when you want a fuller explanation.
- `Beginner-friendly`: best when the topic is new or difficult.
- `Technical`: best for methods, models, metrics, limitations, and research analysis.

For example, use `Beginner-friendly` for:

```text
Explain this paper as if I am new to machine learning.
```

Use `Technical` for:

```text
Explain the method, dataset, metrics, results, and limitations.
```

## 7. Understanding Citations

When the assistant answers from an uploaded paper, it should show citations.

A citation usually includes:

- Citation ID, such as `C1` or `C2`.
- Source file name.
- Page number.
- A short excerpt from the paper.

Example:

```text
C1 - paper.pdf - page 4
```

Use citations to check where the answer came from. This is important because research assistants should not just sound confident; they should show evidence.

If an answer does not include useful citations, treat it carefully and ask:

```text
Show the source passages for that answer.
```

## 8. Summarizing a Paper

You can ask for different types of summaries.

Useful summary prompts:

```text
Give me a short summary of this paper.
```

```text
Summarize this paper section by section.
```

```text
Give me a technical summary focusing on model, dataset, method, results, and limitations.
```

```text
Summarize this paper in Malayalam.
```

```text
Create a Japanese study summary with key English technical terms.
```

For long papers, the assistant may summarize the paper in parts before creating a final summary.

## 9. Translating Text

Use the translation section when you want to translate text directly.

Steps:

1. Paste or type the text you want to translate.
2. Choose the source language, or use auto-detect if available.
3. Choose the target language.
4. Click translate.

Example translation tasks:

```text
Translate this abstract into Japanese.
```

```text
Translate this explanation into Malayalam.
```

```text
Translate this Hindi question into English.
```

Translation is useful for:

- Understanding English papers in your preferred language.
- Preparing bilingual notes.
- Studying Japanese technical vocabulary.
- Comparing technical terms across languages.

## 10. Choosing an Answer Language

The app includes an answer language selector.

Use it when you want the assistant to reply in a specific language.

Examples:

- English for general academic answers.
- Malayalam, Hindi, Tamil, Kannada, Telugu, Bengali, Marathi, Gujarati, Punjabi, Urdu, Odia, or Assamese for Indian-language explanations.
- Japanese or Korean for East Asian study practice.
- Spanish, French, German, Portuguese, Russian, Italian, Turkish, Arabic, or Persian for broader multilingual reading.

If a language is not available yet, it can be added later through the language configuration system.

## 11. Using Conversation Memory

The assistant can remember the current session.

This means you can ask follow-up questions like:

```text
Can you explain that more simply?
```

```text
What are the limitations of the method you just described?
```

```text
Translate the previous answer into Japanese.
```

Starting a new session clears the short-term conversation context.

The sidebar also includes memory controls:

- `Start new session` creates a fresh conversation.
- `Clear current memory` deletes the saved messages for the current session.
- The memory panel shows recent messages and recent sessions when the backend is running.

Future versions may include long-term memory for things like:

- Preferred answer language.
- Favorite explanation style.
- Research interests.
- Previously studied topics.

## 12. Good Prompt Examples

### For Understanding a Paper

```text
Explain the main idea of this paper as if I am new to NLP.
```

```text
What problem are the authors trying to solve?
```

```text
What is new compared to previous work?
```

### For Research Analysis

```text
List the methodology, dataset, evaluation metrics, results, and limitations.
```

```text
What assumptions does this paper make?
```

```text
What are possible future research directions based on this paper?
```

### For Multilingual Study

```text
Explain this paper in Malayalam but keep important AI terms in English.
```

```text
Give me a Japanese summary with simple vocabulary.
```

```text
Translate the abstract into Hindi and explain the technical terms.
```

### For Citations

```text
Answer with citations from the paper.
```

```text
Which page supports this claim?
```

```text
Show the exact source passages used for the answer.
```

## 13. Common Problems and Fixes

### The PDF Upload Fails

Possible reasons:

- The file is not a PDF.
- The file is too large.
- The PDF is scanned or image-based.
- The PDF is password-protected.

Try another digital PDF with selectable text.

### The Answer Is Too General

Try asking a more specific question.

Instead of:

```text
Explain this paper.
```

Ask:

```text
What is the main contribution of this paper, and what evidence do the authors give?
```

### The Assistant Cannot Find an Answer

Possible reasons:

- The uploaded paper does not contain the answer.
- The question is too broad.
- The retrieval system did not find the right passage.

Try:

```text
Search for passages related to the dataset used in the paper.
```

### The Translation Sounds Awkward

Machine translation can sometimes sound unnatural or change technical meaning.

Try:

```text
Translate this more naturally but keep the technical terms accurate.
```

### The Citation Looks Wrong

Ask the assistant to show the source passage again:

```text
Show the source passages and page numbers for your answer.
```

## 14. Current Limitations

In early versions, the app may have these limitations:

- It works best with text-based PDFs.
- It may not understand images, charts, or equations deeply.
- It may miss information if the PDF extraction is poor.
- Translation quality may vary by language.
- Very long papers may take more time to process.
- Local LLM answers may be slower than cloud LLM answers.
- The assistant should not be used as the only source for high-stakes decisions.

Always verify important claims from the cited source passages.

## 15. Privacy Notes

Be careful when uploading private or sensitive documents.

Depending on the configured AI provider, document text may be sent to an external model API. For private research, use a local model setup when possible.

Recommended safety habits:

- Do not upload confidential documents to a public demo.
- Do not paste private personal information.
- Review provider settings before using cloud LLMs.
- Delete stored files and memory when no longer needed.

## 16. Best Practices

To get the best experience:

- Upload clean, text-based PDFs.
- Ask focused questions.
- Use citations to verify answers.
- Request summaries in the format you want.
- Use your preferred language for understanding, then compare with the source.
- Ask for bilingual explanations when studying technical terms.
- Start a new session when switching to a different topic.

## 17. Quick Start Example

1. Open the app.
2. Upload a research paper PDF.
3. Wait for indexing to finish.
4. Choose `English`, `Hindi`, `Malayalam`, or `Japanese` as the answer language.
5. Choose an answer style such as `Detailed` or `Beginner-friendly`.
6. Ask:

```text
What is the main contribution of this paper? Answer with citations.
```

7. Read the answer.
8. Open the citations and check the source passages.
9. Ask a follow-up:

```text
Explain the methodology more simply.
```

10. Translate the answer if needed:

```text
Translate the previous answer into Japanese.
```

## 18. What To Expect From Future Versions

Future versions of PolyGlotAI Research Assistant may include:

- Better Japanese tokenization.
- More supported languages.
- Stronger multilingual retrieval.
- React frontend.
- Long-term memory.
- Agent-based routing.
- Citation verification.
- Translation model comparison.
- Research evaluation dashboard.
- Saved document libraries.
