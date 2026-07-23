from typing import Literal

from pydantic import BaseModel, Field


AnswerStyle = Literal["auto", "short", "detailed", "beginner", "technical"]


class Language(BaseModel):
    code: str
    name: str
    family: str = "global"
    native_name: str | None = None
    enabled: bool = True
    script_direction: str = "ltr"
    tokenizer_strategy: str = "whitespace"
    translation_supported: bool = True
    embedding_supported: bool = True


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    pages: int
    chunks_indexed: int


class PagePreview(BaseModel):
    page_number: int
    character_count: int
    has_text: bool
    preview: str


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    stored_filename: str
    total_pages: int
    pages_with_text: int
    total_characters: int
    extraction_status: str
    chunks_ready: bool = False
    chunk_count: int = 0
    detected_languages: list[str] = Field(default_factory=list)
    indexed: bool = False
    created_at: str
    updated_at: str


class DocumentDetail(DocumentSummary):
    page_previews: list[PagePreview]


class DocumentUploadResponse(DocumentDetail):
    message: str


class ChunkPreview(BaseModel):
    chunk_id: str
    chunk_index: int
    page_start: int
    page_end: int
    language: str
    tokenizer_strategy: str
    character_count: int
    preview: str


class ChunkingRequest(BaseModel):
    chunk_size: int | None = Field(default=None, ge=200, le=2000)
    chunk_overlap: int | None = Field(default=None, ge=0, le=500)


class ChunkingResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    chunk_size: int
    chunk_overlap: int
    detected_languages: list[str]
    tokenizer_strategies: list[str]
    chunks: list[ChunkPreview]
    message: str


class EmbeddingModelInfo(BaseModel):
    id: str
    display_name: str
    model_name: str
    provider: str
    strategy: str
    dimension: int
    enabled: bool = True
    recommended_for: str | None = None
    notes: str | None = None
    query_prefix: str | None = None
    document_prefix: str | None = None


class LanguageQualityLanguage(BaseModel):
    code: str
    name: str
    family: str
    script_direction: str
    tokenizer_strategy: str
    priority_reason: str
    configured: bool
    google_translation: bool
    nllb_translation: bool
    embedding_supported: bool


class LanguageQualityCase(BaseModel):
    id: str
    category: str
    source_language: str
    target_language: str
    source_text: str
    prompt: str
    expected_terms: list[str] = Field(default_factory=list)
    notes: str | None = None


class LanguageQualityReport(BaseModel):
    priority_languages: list[LanguageQualityLanguage]
    cases: list[LanguageQualityCase]
    readiness_score: float
    missing_items: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class EmbeddingCompareRequest(BaseModel):
    query: str = Field(min_length=1)
    positive_text: str = Field(min_length=1)
    negative_texts: list[str] = Field(default_factory=list)
    model_ids: list[str] = Field(default_factory=list)


class EmbeddingCandidateScore(BaseModel):
    label: str
    text: str
    score: float


class EmbeddingModelComparison(BaseModel):
    model_id: str
    model_name: str
    strategy: str
    best_label: str
    positive_rank: int
    scores: list[EmbeddingCandidateScore]


class EmbeddingCompareResponse(BaseModel):
    query: str
    comparisons: list[EmbeddingModelComparison]


class VectorIndexResponse(BaseModel):
    document_id: str
    filename: str
    collection_name: str
    chunks_indexed: int
    embedding_model: str
    vector_db_provider: str
    message: str


class VectorSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=12)
    document_id: str | None = None


class VectorSearchResult(BaseModel):
    chunk_id: str
    document_id: str
    source_name: str
    page: int
    score: float | None = None
    language: str | None = None
    tokenizer_strategy: str | None = None
    excerpt: str


class VectorSearchResponse(BaseModel):
    query: str
    collection_name: str
    results: list[VectorSearchResult]


class Citation(BaseModel):
    citation_id: str
    source_name: str
    page: int
    chunk_id: str
    excerpt: str
    score: float | None = None
    page_start: int | None = None
    page_end: int | None = None
    language: str | None = None
    tokenizer_strategy: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: str | None = None
    document_id: str | None = None
    target_language: str = "en"
    translate_answer: bool = True
    top_k: int = Field(default=5, ge=1, le=12)
    answer_style: AnswerStyle = "auto"


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    target_language: str
    answer_style: AnswerStyle = "auto"
    document_type: str | None = None
    citations: list[Citation]
    retrieved_context: list[Citation] = Field(default_factory=list)
    memory_turns_used: int
    retrieved_chunks: int = 0
    cited_chunks: int = 0
    context_available: bool = False
    retrieval_query: str
    retrieval_mode: str = "unknown"
    retrieval_warning: str | None = None
    grounding_verified: bool = False
    citation_confidence: str = "none"
    citation_warning: str | None = None
    translation_applied: bool = False


class SessionMessage(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    language: str | None = None
    document_id: str | None = None
    created_at: str
    metadata: dict = Field(default_factory=dict)


class SessionSummary(BaseModel):
    session_id: str
    message_count: int
    first_message_at: str
    last_message_at: str
    preferred_language: str | None = None
    last_document_id: str | None = None


class SessionDetail(BaseModel):
    session_id: str
    message_count: int
    messages: list[SessionMessage]


class MemoryDeleteResponse(BaseModel):
    deleted_messages: int
    message: str


class MemoryStatusResponse(BaseModel):
    short_term_enabled: bool
    short_term_store: str
    long_term_enabled: bool
    long_term_collection: str
    notes: str


SummaryType = Literal["short", "detailed", "technical", "bilingual"]
TranslationMethod = Literal["google", "llm", "nllb"]


class SummaryRequest(BaseModel):
    document_id: str = Field(min_length=1)
    summary_type: SummaryType = "short"
    target_language: str = "en"
    max_chunks: int = Field(default=8, ge=1, le=20)
    translate_summary: bool = True


class SummaryResponse(BaseModel):
    document_id: str
    filename: str
    summary_type: SummaryType
    target_language: str
    summary: str
    citations: list[Citation]
    chunks_used: int
    context_available: bool
    translation_applied: bool = False


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1)
    target_language: str
    source_language: str = "auto"
    method: TranslationMethod | None = None


class TranslateResponse(BaseModel):
    source_language: str
    target_language: str
    translated_text: str
    provider: str
    method: TranslationMethod
    quality_notes: str | None = None


class TranslationMethodInfo(BaseModel):
    id: TranslationMethod
    display_name: str
    provider: str
    enabled: bool = True
    requires_model_download: bool = False
    best_for: str | None = None
    notes: str | None = None


class TranslationCompareRequest(BaseModel):
    text: str = Field(min_length=1)
    target_language: str
    source_language: str = "auto"
    methods: list[TranslationMethod] = Field(default_factory=list)


class TranslationCompareResponse(BaseModel):
    source_language: str
    target_language: str
    results: list[TranslateResponse]


class HealthResponse(BaseModel):
    app_name: str
    status: str
    llm_provider: str
    vector_store: str
