export type Language = {
  code: string;
  name: string;
  family: string;
  native_name?: string | null;
  enabled: boolean;
  script_direction: string;
  tokenizer_strategy: string;
  translation_supported: boolean;
  embedding_supported: boolean;
};

export type HealthResponse = {
  app_name: string;
  status: string;
  llm_provider: string;
  vector_store: string;
};

export type DocumentSummary = {
  document_id: string;
  filename: string;
  stored_filename: string;
  total_pages: number;
  pages_with_text: number;
  total_characters: number;
  extraction_status: string;
  chunks_ready: boolean;
  chunk_count: number;
  detected_languages: string[];
  indexed: boolean;
  created_at: string;
  updated_at: string;
};

export type Citation = {
  citation_id: string;
  source_name: string;
  page: number;
  chunk_id: string;
  excerpt: string;
  score?: number | null;
  page_start?: number | null;
  page_end?: number | null;
};

export type ChatResponse = {
  session_id: string;
  answer: string;
  target_language: string;
  answer_style: string;
  document_type?: string | null;
  citations: Citation[];
  retrieved_context: Citation[];
  memory_turns_used: number;
  retrieved_chunks: number;
  cited_chunks: number;
  context_available: boolean;
  retrieval_query: string;
  retrieval_mode: string;
  retrieval_warning?: string | null;
  grounding_verified: boolean;
  citation_confidence: string;
  citation_warning?: string | null;
  translation_applied: boolean;
};

export type SummaryResponse = {
  document_id: string;
  filename: string;
  summary_type: string;
  target_language: string;
  summary: string;
  citations: Citation[];
  chunks_used: number;
  context_available: boolean;
  translation_applied: boolean;
};

export type TranslateResponse = {
  source_language: string;
  target_language: string;
  translated_text: string;
  provider: string;
  method: string;
  quality_notes?: string | null;
};

export type TranslationMethodInfo = {
  id: string;
  display_name: string;
  provider: string;
  enabled: boolean;
  requires_model_download: boolean;
  best_for?: string | null;
  notes?: string | null;
};

export type LanguageQualityLanguage = {
  code: string;
  name: string;
  family: string;
  script_direction: string;
  tokenizer_strategy: string;
  priority_reason: string;
  configured: boolean;
  google_translation: boolean;
  nllb_translation: boolean;
  embedding_supported: boolean;
};

export type LanguageQualityCase = {
  id: string;
  category: string;
  source_language: string;
  target_language: string;
  source_text: string;
  prompt: string;
  expected_terms: string[];
  notes?: string | null;
};

export type LanguageQualityReport = {
  priority_languages: LanguageQualityLanguage[];
  cases: LanguageQualityCase[];
  readiness_score: number;
  missing_items: string[];
  notes: string[];
};
