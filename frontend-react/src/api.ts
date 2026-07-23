import type {
  ChatResponse,
  DocumentSummary,
  HealthResponse,
  Language,
  LanguageQualityReport,
  SummaryResponse,
  TranslateResponse,
  TranslationMethodInfo,
} from "./types";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function getHealth() {
  return requestJson<HealthResponse>("/health");
}

export function getLanguages() {
  return requestJson<Language[]>("/languages");
}

export function getDocuments() {
  return requestJson<DocumentSummary[]>("/documents");
}

export function getTranslationMethods() {
  return requestJson<TranslationMethodInfo[]>("/translation/methods");
}

export function getLanguageQuality() {
  return requestJson<LanguageQualityReport>("/evaluation/language-quality");
}

export function uploadDocument(file: File) {
  const form = new FormData();
  form.append("file", file);
  return requestJson<DocumentSummary>("/documents/upload", {
    method: "POST",
    body: form,
  });
}

export function prepareDocument(documentId: string) {
  return requestJson(`/documents/${documentId}/chunks`, {
    method: "POST",
  });
}

export function indexDocument(documentId: string) {
  return requestJson(`/documents/${documentId}/index`, {
    method: "POST",
  });
}

export function askQuestion(payload: {
  question: string;
  session_id: string;
  document_id?: string | null;
  target_language: string;
  translate_answer: boolean;
  top_k: number;
  answer_style: string;
}) {
  return requestJson<ChatResponse>("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function summarizeDocument(payload: {
  document_id: string;
  summary_type: string;
  target_language: string;
  max_chunks: number;
  translate_summary: boolean;
}) {
  return requestJson<SummaryResponse>("/summarize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function translateText(payload: {
  text: string;
  source_language: string;
  target_language: string;
  method?: string;
}) {
  return requestJson<TranslateResponse>("/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
