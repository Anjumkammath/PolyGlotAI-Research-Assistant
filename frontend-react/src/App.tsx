import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  API_BASE_URL,
  askQuestion,
  getDocuments,
  getHealth,
  getLanguageQuality,
  getLanguages,
  getTranslationMethods,
  indexDocument,
  prepareDocument,
  summarizeDocument,
  translateText,
  uploadDocument,
} from "./api";
import type {
  ChatResponse,
  Citation,
  DocumentSummary,
  HealthResponse,
  Language,
  LanguageQualityReport,
  SummaryResponse,
  TranslateResponse,
  TranslationMethodInfo,
} from "./types";

type Tab = "ask" | "summarize" | "translate" | "qa";
type Notice = { kind: "success" | "warning" | "error" | "info"; text: string };

const fallbackLanguages: Language[] = [
  {
    code: "en",
    name: "English",
    family: "global",
    enabled: true,
    script_direction: "ltr",
    tokenizer_strategy: "whitespace",
    translation_supported: true,
    embedding_supported: true,
  },
  {
    code: "ml",
    name: "Malayalam",
    family: "indian",
    enabled: true,
    script_direction: "ltr",
    tokenizer_strategy: "indic",
    translation_supported: true,
    embedding_supported: true,
  },
  {
    code: "hi",
    name: "Hindi",
    family: "indian",
    enabled: true,
    script_direction: "ltr",
    tokenizer_strategy: "indic",
    translation_supported: true,
    embedding_supported: true,
  },
  {
    code: "ja",
    name: "Japanese",
    family: "east_asian",
    enabled: true,
    script_direction: "ltr",
    tokenizer_strategy: "sudachipy",
    translation_supported: true,
    embedding_supported: true,
  },
];

const tabs: { id: Tab; label: string }[] = [
  { id: "ask", label: "Ask papers" },
  { id: "summarize", label: "Summarize" },
  { id: "translate", label: "Translate text" },
  { id: "qa", label: "Language QA" },
];

const answerStyles = ["auto", "short", "detailed", "beginner", "technical"];
const summaryTypes = ["short", "detailed", "technical", "bilingual"];

function makeSessionId() {
  if ("crypto" in window && "randomUUID" in window.crypto) {
    return window.crypto.randomUUID();
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function cleanDisplayText(text: string) {
  return text.replace(/\s+/g, " ").replace(/\s+([.,;:!?])/g, "$1").trim();
}

function displayRetrievalMode(mode?: string | null) {
  const labels: Record<string, string> = {
    vector: "Vector search",
    lexical_fallback: "Fallback search",
    overview_bypass: "Overview mode",
    unknown: "Unknown",
  };
  return labels[mode || "unknown"] || mode || "Unknown";
}

function App() {
  const [activeTab, setActiveTab] = useState<Tab>("ask");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [languages, setLanguages] = useState<Language[]>(fallbackLanguages);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [methods, setMethods] = useState<TranslationMethodInfo[]>([]);
  const [qualityReport, setQualityReport] = useState<LanguageQualityReport | null>(null);
  const [sessionId, setSessionId] = useState(makeSessionId);
  const [activeDocumentId, setActiveDocumentId] = useState<string>("");
  const [uploadFileState, setUploadFileState] = useState<File | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const [question, setQuestion] = useState("What is this document about? Explain it clearly.");
  const [answerLanguage, setAnswerLanguage] = useState("en");
  const [answerStyle, setAnswerStyle] = useState("detailed");
  const [topK, setTopK] = useState(5);
  const [chatResponse, setChatResponse] = useState<ChatResponse | null>(null);

  const [summaryType, setSummaryType] = useState("short");
  const [summaryLanguage, setSummaryLanguage] = useState("en");
  const [summaryResponse, setSummaryResponse] = useState<SummaryResponse | null>(null);

  const [sourceLanguage, setSourceLanguage] = useState("auto");
  const [targetLanguage, setTargetLanguage] = useState("ml");
  const [translationMethod, setTranslationMethod] = useState("google");
  const [translationText, setTranslationText] = useState(
    "The RAG system retrieves source passages before generating a cited answer.",
  );
  const [translationResponse, setTranslationResponse] = useState<TranslateResponse | null>(null);

  const activeDocument = useMemo(
    () => documents.find((document) => document.document_id === activeDocumentId) ?? null,
    [activeDocumentId, documents],
  );

  const enabledMethods = useMemo(
    () => methods.filter((method) => method.enabled),
    [methods],
  );

  useEffect(() => {
    void bootstrap();
  }, []);

  async function bootstrap() {
    setBusy("Connecting to PolyGlotAI...");
    try {
      await Promise.all([loadHealth(), loadLanguages(), refreshDocuments(), loadMethods(), loadQuality()]);
      setNotice({ kind: "success", text: "Assistant is ready." });
    } catch (error) {
      setNotice({
        kind: "warning",
        text: error instanceof Error ? error.message : "Some startup details could not be loaded.",
      });
    } finally {
      setBusy(null);
    }
  }

  async function loadHealth() {
    setHealth(await getHealth());
  }

  async function loadLanguages() {
    const loadedLanguages = await getLanguages();
    if (loadedLanguages.length) {
      setLanguages(loadedLanguages);
    }
  }

  async function refreshDocuments() {
    const loadedDocuments = await getDocuments();
    setDocuments(loadedDocuments);
    if (!activeDocumentId && loadedDocuments.length) {
      setActiveDocumentId(loadedDocuments[0].document_id);
    }
  }

  async function loadMethods() {
    setMethods(await getTranslationMethods());
  }

  async function loadQuality() {
    setQualityReport(await getLanguageQuality());
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!uploadFileState) {
      setNotice({ kind: "warning", text: "Choose a PDF first." });
      return;
    }

    setBusy("Reading, chunking, and indexing the PDF...");
    try {
      const uploaded = await uploadDocument(uploadFileState);
      setActiveDocumentId(uploaded.document_id);

      try {
        await prepareDocument(uploaded.document_id);
      } catch (error) {
        setNotice({
          kind: "warning",
          text: error instanceof Error ? error.message : "The PDF uploaded, but chunking needs another try.",
        });
      }

      try {
        await indexDocument(uploaded.document_id);
        setNotice({ kind: "success", text: "PDF uploaded and prepared for cited questions." });
      } catch {
        setNotice({
          kind: "warning",
          text: "PDF uploaded and chunked. Enhanced vector search needs Qdrant running, but local fallback search can still answer.",
        });
      }

      await refreshDocuments();
    } catch (error) {
      setNotice({
        kind: "error",
        text: error instanceof Error ? error.message : "Upload failed.",
      });
    } finally {
      setBusy(null);
    }
  }

  async function handlePrepare(documentId: string) {
    setBusy("Preparing this PDF for questions...");
    try {
      await prepareDocument(documentId);
      try {
        await indexDocument(documentId);
        setNotice({ kind: "success", text: "Document is ready for enhanced search." });
      } catch {
        setNotice({
          kind: "warning",
          text: "Chunks are ready. Enhanced vector search needs Qdrant, so fallback retrieval will be used if needed.",
        });
      }
      await refreshDocuments();
    } catch (error) {
      setNotice({
        kind: "error",
        text: error instanceof Error ? error.message : "Could not prepare the document.",
      });
    } finally {
      setBusy(null);
    }
  }

  async function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim()) {
      setNotice({ kind: "warning", text: "Write a question first." });
      return;
    }

    setBusy("Searching sources and drafting an answer...");
    try {
      const response = await askQuestion({
        question: question.trim(),
        session_id: sessionId,
        document_id: activeDocumentId || null,
        target_language: answerLanguage,
        translate_answer: true,
        top_k: topK,
        answer_style: answerStyle,
      });
      setChatResponse(response);
      setSessionId(response.session_id);
      setNotice({ kind: "success", text: `Answer generated with ${response.citations.length} source citation(s).` });
    } catch (error) {
      setNotice({
        kind: "error",
        text: error instanceof Error ? error.message : "Could not answer the question.",
      });
    } finally {
      setBusy(null);
    }
  }

  async function handleSummarize(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeDocumentId) {
      setNotice({ kind: "warning", text: "Upload or choose a document first." });
      return;
    }

    setBusy("Creating a source-grounded summary...");
    try {
      const response = await summarizeDocument({
        document_id: activeDocumentId,
        summary_type: summaryType,
        target_language: summaryLanguage,
        max_chunks: 8,
        translate_summary: true,
      });
      setSummaryResponse(response);
      setNotice({ kind: "success", text: `Summary created from ${response.chunks_used} source chunk(s).` });
    } catch (error) {
      setNotice({
        kind: "error",
        text: error instanceof Error ? error.message : "Could not summarize the document.",
      });
    } finally {
      setBusy(null);
    }
  }

  async function handleTranslate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!translationText.trim()) {
      setNotice({ kind: "warning", text: "Add text to translate first." });
      return;
    }

    setBusy("Translating technical text...");
    try {
      const response = await translateText({
        text: translationText.trim(),
        source_language: sourceLanguage,
        target_language: targetLanguage,
        method: translationMethod || undefined,
      });
      setTranslationResponse(response);
      setNotice({ kind: "success", text: `Translated with ${response.provider}.` });
    } catch (error) {
      setNotice({
        kind: "error",
        text: error instanceof Error ? error.message : "Translation failed.",
      });
    } finally {
      setBusy(null);
    }
  }

  function languageName(code: string) {
    if (code === "auto") {
      return "Auto detect";
    }
    return languages.find((language) => language.code === code)?.name ?? code;
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-kicker">PolyGlotAI</span>
          <h2>Workspace</h2>
        </div>

        <div className="status-card">
          <span className={`status-dot ${health?.status === "ok" ? "ready" : ""}`} />
          <div>
            <strong>{health?.status === "ok" ? "Assistant is ready" : "Checking assistant"}</strong>
            <p>{health ? `${health.llm_provider} mode, ${health.vector_store}` : API_BASE_URL}</p>
          </div>
        </div>

        <button
          className="ghost-button"
          onClick={() => {
            setSessionId(makeSessionId());
            setChatResponse(null);
            setNotice({ kind: "info", text: "Started a new conversation session." });
          }}
        >
          Start new session
        </button>

        <section className="sidebar-section">
          <h3>Documents</h3>
          {documents.length === 0 ? (
            <p className="muted">No PDFs uploaded yet.</p>
          ) : (
            <div className="document-list">
              {documents.slice(0, 6).map((document) => (
                <button
                  key={document.document_id}
                  className={`document-item ${activeDocumentId === document.document_id ? "selected" : ""}`}
                  onClick={() => setActiveDocumentId(document.document_id)}
                >
                  <span>{document.filename}</span>
                  <small>
                    {document.total_pages} pages, {document.chunk_count || 0} chunks
                  </small>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="sidebar-section">
          <h3>Languages</h3>
          <p className="muted">{languages.length} enabled languages</p>
          <div className="mini-tags">
            {languages.slice(0, 10).map((language) => (
              <span key={language.code}>{language.code}</span>
            ))}
          </div>
        </section>
      </aside>

      <section className="content">
        <Hero languages={languages} />

        <div className="tabbar" role="tablist" aria-label="PolyGlotAI tools">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={activeTab === tab.id ? "active" : ""}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>

        {notice && <div className={`notice ${notice.kind}`}>{notice.text}</div>}
        {busy && <div className="busy">{busy}</div>}

        {activeTab === "ask" && (
          <AskPanel
            activeDocument={activeDocument}
            answerLanguage={answerLanguage}
            answerStyle={answerStyle}
            chatResponse={chatResponse}
            documents={documents}
            handleAsk={handleAsk}
            handlePrepare={handlePrepare}
            handleUpload={handleUpload}
            languageName={languageName}
            languages={languages}
            question={question}
            setActiveDocumentId={setActiveDocumentId}
            setAnswerLanguage={setAnswerLanguage}
            setAnswerStyle={setAnswerStyle}
            setQuestion={setQuestion}
            setTopK={setTopK}
            setUploadFileState={setUploadFileState}
            topK={topK}
            uploadFileState={uploadFileState}
          />
        )}

        {activeTab === "summarize" && (
          <SummarizePanel
            activeDocumentId={activeDocumentId}
            documents={documents}
            handleSummarize={handleSummarize}
            languages={languages}
            setActiveDocumentId={setActiveDocumentId}
            setSummaryLanguage={setSummaryLanguage}
            setSummaryType={setSummaryType}
            summaryLanguage={summaryLanguage}
            summaryResponse={summaryResponse}
            summaryType={summaryType}
          />
        )}

        {activeTab === "translate" && (
          <TranslatePanel
            enabledMethods={enabledMethods}
            handleTranslate={handleTranslate}
            languages={languages}
            setSourceLanguage={setSourceLanguage}
            setTargetLanguage={setTargetLanguage}
            setTranslationMethod={setTranslationMethod}
            setTranslationText={setTranslationText}
            sourceLanguage={sourceLanguage}
            targetLanguage={targetLanguage}
            translationMethod={translationMethod}
            translationResponse={translationResponse}
            translationText={translationText}
          />
        )}

        {activeTab === "qa" && (
          <LanguageQaPanel
            loadQuality={loadQuality}
            qualityReport={qualityReport}
          />
        )}
      </section>
    </main>
  );
}

function Hero({ languages }: { languages: Language[] }) {
  const featureCards = [
    {
      stat: "Ready",
      title: "Ask papers",
      copy: "Upload PDFs and get answers grounded in source passages.",
    },
    {
      stat: `${languages.length} languages`,
      title: "Multilingual support",
      copy: "Work across English, Indian languages, Japanese, Korean, French, Spanish, and more.",
    },
    {
      stat: "Cited",
      title: "Shows its work",
      copy: "Every answer can include source labels, page numbers, and excerpts.",
    },
    {
      stat: "Research tools",
      title: "Summarize and translate",
      copy: "Create summaries and translate technical text without leaving the workspace.",
    },
  ];

  return (
    <header className="hero-grid">
      <div className="hero-card">
        <p className="eyebrow">Multilingual Research Assistant</p>
        <h1>PolyGlotAI Research Assistant</h1>
        <p className="tagline">
          A multilingual research assistant that reads your papers, answers in your language,
          and always shows its work.
        </p>
        <div className="hero-tags">
          <span>RAG</span>
          <span>Citations</span>
          <span>Translation</span>
          <span>Memory</span>
          <span>FastAPI</span>
        </div>
      </div>

      <div className="hero-feature-panel" aria-label="Assistant capabilities">
        {featureCards.map((card) => (
          <article className="hero-feature-card" key={card.title}>
            <span>{card.stat}</span>
            <h2>{card.title}</h2>
            <p>{card.copy}</p>
          </article>
        ))}
      </div>
    </header>
  );
}

function AskPanel(props: {
  activeDocument: DocumentSummary | null;
  answerLanguage: string;
  answerStyle: string;
  chatResponse: ChatResponse | null;
  documents: DocumentSummary[];
  handleAsk: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  handlePrepare: (documentId: string) => Promise<void>;
  handleUpload: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  languageName: (code: string) => string;
  languages: Language[];
  question: string;
  setActiveDocumentId: (id: string) => void;
  setAnswerLanguage: (language: string) => void;
  setAnswerStyle: (style: string) => void;
  setQuestion: (question: string) => void;
  setTopK: (topK: number) => void;
  setUploadFileState: (file: File | null) => void;
  topK: number;
  uploadFileState: File | null;
}) {
  return (
    <div className="workspace-grid">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Papers</p>
            <h2>Upload and prepare</h2>
          </div>
        </div>

        <form className="upload-box" onSubmit={props.handleUpload}>
          <input
            accept="application/pdf"
            id="pdf-upload"
            type="file"
            onChange={(event) => props.setUploadFileState(event.target.files?.[0] ?? null)}
          />
          <label htmlFor="pdf-upload">
            <strong>{props.uploadFileState?.name ?? "Choose a PDF"}</strong>
            <span>Upload, chunk, and index it for cited answers.</span>
          </label>
          <button className="primary-button" type="submit">Upload and read</button>
        </form>

        <div className="document-cards">
          {props.documents.map((document) => (
            <article className="document-card" key={document.document_id}>
              <div>
                <h3>{document.filename}</h3>
                <p>
                  {document.total_pages} pages, {document.pages_with_text} with text,{" "}
                  {document.chunk_count || 0} chunks
                </p>
              </div>
              <div className="document-actions">
                <button className="secondary-button" onClick={() => props.setActiveDocumentId(document.document_id)}>
                  Use
                </button>
                {!document.chunks_ready && (
                  <button className="ghost-button compact" onClick={() => props.handlePrepare(document.document_id)}>
                    Prepare
                  </button>
                )}
                {document.indexed && <span className="ready-pill">Indexed</span>}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Assistant</p>
            <h2>Ask about the paper</h2>
          </div>
          {props.activeDocument && <span className="active-source">{props.activeDocument.filename}</span>}
        </div>

        <form className="assistant-form" onSubmit={props.handleAsk}>
          <label>
            Question
            <textarea
              value={props.question}
              onChange={(event) => props.setQuestion(event.target.value)}
              rows={5}
            />
          </label>

          <div className="form-grid">
            <label>
              Search scope
              <select
                value={props.activeDocument?.document_id ?? ""}
                onChange={(event) => props.setActiveDocumentId(event.target.value)}
              >
                <option value="">All indexed papers</option>
                {props.documents.map((document) => (
                  <option key={document.document_id} value={document.document_id}>
                    {document.filename}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Answer language
              <select
                value={props.answerLanguage}
                onChange={(event) => props.setAnswerLanguage(event.target.value)}
              >
                {props.languages.map((language) => (
                  <option key={language.code} value={language.code}>
                    {language.name} ({language.code})
                  </option>
                ))}
              </select>
            </label>

            <label>
              Answer style
              <select
                value={props.answerStyle}
                onChange={(event) => props.setAnswerStyle(event.target.value)}
              >
                {answerStyles.map((style) => (
                  <option key={style} value={style}>{style}</option>
                ))}
              </select>
            </label>

            <label>
              Source chunks
              <input
                max="12"
                min="1"
                type="number"
                value={props.topK}
                onChange={(event) => props.setTopK(Number(event.target.value))}
              />
            </label>
          </div>

          <button className="primary-button" type="submit">Ask with citations</button>
        </form>

        {props.chatResponse && (
          <AnswerBlock
            citations={props.chatResponse.citations}
            citationWarning={props.chatResponse.citation_warning}
            groundingVerified={props.chatResponse.grounding_verified}
            meta={`${props.languageName(props.chatResponse.target_language)} answer | ${displayRetrievalMode(props.chatResponse.retrieval_mode)} | ${props.chatResponse.cited_chunks} cited of ${props.chatResponse.retrieved_chunks} retrieved`}
            retrievalWarning={props.chatResponse.retrieval_warning}
            retrievedContext={props.chatResponse.retrieved_context}
            text={props.chatResponse.answer}
            title="Answer"
          />
        )}
      </section>
    </div>
  );
}

function SummarizePanel(props: {
  activeDocumentId: string;
  documents: DocumentSummary[];
  handleSummarize: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  languages: Language[];
  setActiveDocumentId: (id: string) => void;
  setSummaryLanguage: (language: string) => void;
  setSummaryType: (type: string) => void;
  summaryLanguage: string;
  summaryResponse: SummaryResponse | null;
  summaryType: string;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Document summaries</p>
          <h2>Source-grounded summary</h2>
        </div>
      </div>

      <form className="assistant-form" onSubmit={props.handleSummarize}>
        <div className="form-grid">
          <label>
            Document
            <select
              value={props.activeDocumentId}
              onChange={(event) => props.setActiveDocumentId(event.target.value)}
            >
              <option value="">Choose a document</option>
              {props.documents.map((document) => (
                <option key={document.document_id} value={document.document_id}>
                  {document.filename}
                </option>
              ))}
            </select>
          </label>

          <label>
            Summary type
            <select
              value={props.summaryType}
              onChange={(event) => props.setSummaryType(event.target.value)}
            >
              {summaryTypes.map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </label>

          <label>
            Summary language
            <select
              value={props.summaryLanguage}
              onChange={(event) => props.setSummaryLanguage(event.target.value)}
            >
              {props.languages.map((language) => (
                <option key={language.code} value={language.code}>
                  {language.name} ({language.code})
                </option>
              ))}
            </select>
          </label>
        </div>

        <button className="primary-button" type="submit">Create summary</button>
      </form>

      {props.summaryResponse && (
        <AnswerBlock
          citations={props.summaryResponse.citations}
          meta={`${props.summaryResponse.summary_type} summary | ${props.summaryResponse.chunks_used} chunks used`}
          text={props.summaryResponse.summary}
          title={props.summaryResponse.filename}
        />
      )}
    </section>
  );
}

function TranslatePanel(props: {
  enabledMethods: TranslationMethodInfo[];
  handleTranslate: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  languages: Language[];
  setSourceLanguage: (language: string) => void;
  setTargetLanguage: (language: string) => void;
  setTranslationMethod: (method: string) => void;
  setTranslationText: (text: string) => void;
  sourceLanguage: string;
  targetLanguage: string;
  translationMethod: string;
  translationResponse: TranslateResponse | null;
  translationText: string;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Translation lab</p>
          <h2>Translate technical text</h2>
        </div>
      </div>

      <form className="assistant-form" onSubmit={props.handleTranslate}>
        <label>
          Text
          <textarea
            value={props.translationText}
            onChange={(event) => props.setTranslationText(event.target.value)}
            rows={6}
          />
        </label>

        <div className="form-grid">
          <label>
            Source language
            <select
              value={props.sourceLanguage}
              onChange={(event) => props.setSourceLanguage(event.target.value)}
            >
              <option value="auto">Auto detect</option>
              {props.languages.map((language) => (
                <option key={language.code} value={language.code}>
                  {language.name} ({language.code})
                </option>
              ))}
            </select>
          </label>

          <label>
            Target language
            <select
              value={props.targetLanguage}
              onChange={(event) => props.setTargetLanguage(event.target.value)}
            >
              {props.languages.map((language) => (
                <option key={language.code} value={language.code}>
                  {language.name} ({language.code})
                </option>
              ))}
            </select>
          </label>

          <label>
            Method
            <select
              value={props.translationMethod}
              onChange={(event) => props.setTranslationMethod(event.target.value)}
            >
              {props.enabledMethods.map((method) => (
                <option key={method.id} value={method.id}>
                  {method.display_name}
                </option>
              ))}
            </select>
          </label>
        </div>

        <button className="primary-button" type="submit">Translate</button>
      </form>

      {props.translationResponse && (
        <article className="answer-block">
          <div className="answer-header">
            <h3>Translation</h3>
            <span>{props.translationResponse.provider}</span>
          </div>
          <p className="answer-text">{cleanDisplayText(props.translationResponse.translated_text)}</p>
          {props.translationResponse.quality_notes && (
            <p className="muted">{props.translationResponse.quality_notes}</p>
          )}
        </article>
      )}
    </section>
  );
}

function LanguageQaPanel(props: {
  loadQuality: () => Promise<void>;
  qualityReport: LanguageQualityReport | null;
}) {
  if (!props.qualityReport) {
    return (
      <section className="panel">
        <h2>Language quality evaluation</h2>
        <button className="primary-button" onClick={() => void props.loadQuality()}>Load QA report</button>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Evaluation</p>
          <h2>Language quality dashboard</h2>
        </div>
        <button className="secondary-button" onClick={() => void props.loadQuality()}>Refresh</button>
      </div>

      <div className="metric-grid">
        <Metric label="Readiness" value={`${Math.round(props.qualityReport.readiness_score * 100)}%`} />
        <Metric label="Priority languages" value={String(props.qualityReport.priority_languages.length)} />
        <Metric label="Evaluation cases" value={String(props.qualityReport.cases.length)} />
      </div>

      {props.qualityReport.missing_items.length === 0 ? (
        <div className="notice success">Priority language readiness checks passed.</div>
      ) : (
        <div className="notice warning">{props.qualityReport.missing_items.join(", ")}</div>
      )}

      <div className="qa-grid">
        {props.qualityReport.priority_languages.map((language) => (
          <article className="qa-card" key={language.code}>
            <div className="qa-card-header">
              <h3>{language.name}</h3>
              <span>{language.code}</span>
            </div>
            <p>{language.priority_reason}</p>
            <div className="mini-tags">
              <span>{language.family}</span>
              <span>{language.tokenizer_strategy}</span>
              <span>{language.google_translation ? "google" : "no google"}</span>
              <span>{language.nllb_translation ? "nllb" : "no nllb"}</span>
            </div>
          </article>
        ))}
      </div>

      <h3 className="section-subtitle">Manual evaluation cases</h3>
      <div className="case-list">
        {props.qualityReport.cases.map((testCase) => (
          <article className="case-card" key={testCase.id}>
            <div>
              <span className="case-category">{testCase.category}</span>
              <h4>{testCase.id}</h4>
            </div>
            <p>{testCase.prompt}</p>
            <code>{testCase.source_text}</code>
            <div className="mini-tags">
              <span>{testCase.source_language} to {testCase.target_language}</span>
              {testCase.expected_terms.map((term) => (
                <span key={term}>{term}</span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function AnswerBlock(props: {
  citations: Citation[];
  citationWarning?: string | null;
  groundingVerified?: boolean;
  meta: string;
  retrievalWarning?: string | null;
  retrievedContext?: Citation[];
  text: string;
  title: string;
}) {
  const retrievedContext = props.retrievedContext ?? [];
  const hasVerifiedCitations = props.citations.length > 0 && (props.groundingVerified ?? true);

  return (
    <article className="answer-block">
      <div className="answer-header">
        <h3>{props.title}</h3>
        <span>{props.meta}</span>
      </div>
      {props.retrievalWarning && <p className="answer-warning">{props.retrievalWarning}</p>}
      {props.citationWarning && <p className="answer-warning">{props.citationWarning}</p>}
      <div className="answer-text">
        {cleanDisplayText(props.text)
          .split(/\n+/)
          .filter(Boolean)
          .map((line) => (
            <p key={line}>{line}</p>
          ))}
      </div>

      {hasVerifiedCitations && (
        <div className="citations">
          <h4>Cited sources</h4>
          {props.citations.map((citation) => (
            <details key={citation.citation_id}>
              <summary>
                {citation.citation_id} {citation.source_name} - page {citation.page}
              </summary>
              <p>{cleanDisplayText(citation.excerpt)}</p>
            </details>
          ))}
        </div>
      )}

      {!hasVerifiedCitations && retrievedContext.length > 0 && (
        <div className="citations">
          <h4>Retrieved context</h4>
          {retrievedContext.map((citation) => (
            <details key={citation.citation_id}>
              <summary>
                {citation.citation_id} {citation.source_name} - page {citation.page}
              </summary>
              <p>{cleanDisplayText(citation.excerpt)}</p>
            </details>
          ))}
        </div>
      )}
    </article>
  );
}

export default App;
