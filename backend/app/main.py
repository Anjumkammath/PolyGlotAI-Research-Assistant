from pathlib import Path
import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import get_settings
from backend.app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChunkingRequest,
    ChunkingResponse,
    DocumentDetail,
    DocumentSummary,
    DocumentUploadResponse,
    EmbeddingCompareRequest,
    EmbeddingCompareResponse,
    EmbeddingModelInfo,
    HealthResponse,
    Language,
    LanguageQualityReport,
    MemoryDeleteResponse,
    MemoryStatusResponse,
    SessionDetail,
    SessionSummary,
    SummaryRequest,
    SummaryResponse,
    TranslationCompareRequest,
    TranslationCompareResponse,
    TranslationMethodInfo,
    TranslateRequest,
    TranslateResponse,
    VectorIndexResponse,
    VectorSearchRequest,
    VectorSearchResponse,
)
from backend.app.services.document_chunks import DocumentChunkingService, ChunkingServiceError
from backend.app.services.chunker import tokenizer_setup_issues
from backend.app.services.documents import DocumentService, DocumentServiceError
from backend.app.services.embedding_comparison import EmbeddingComparisonService
from backend.app.services.embeddings import EmbeddingModelRegistry, EmbeddingService
from backend.app.services.languages import get_language_registry, is_supported_language
from backend.app.services.language_quality import LanguageQualityService
from backend.app.services.llm import LLMService
from backend.app.services.memory import MemoryStore
from backend.app.services.rag import RAGService
from backend.app.services.summarization import SummarizationService
from backend.app.services.translator import TranslationService, TranslationServiceError
from backend.app.services.vector_index import VectorIndexService
from backend.app.services.vector_store import VectorStore

settings = get_settings()
logger = logging.getLogger(__name__)
language_registry = get_language_registry()
for issue in tokenizer_setup_issues(
    {language.tokenizer_strategy for language in language_registry.languages}
):
    logger.warning("Tokenizer setup issue: %s", issue)
embedding_registry = EmbeddingModelRegistry(settings.embedding_config_path)
document_service = DocumentService(settings)
document_chunking_service = DocumentChunkingService(
    settings=settings,
    document_service=document_service,
    language_registry=language_registry,
)
embedding_service = EmbeddingService(settings.embedding_model, registry=embedding_registry)
embedding_comparison_service = EmbeddingComparisonService(embedding_registry)
vector_store = VectorStore(settings=settings, embedding_service=embedding_service)
vector_index_service = VectorIndexService(
    settings=settings,
    document_service=document_service,
    chunking_service=document_chunking_service,
    vector_store=vector_store,
)
memory_store = MemoryStore(settings.memory_db_path)
llm_service = LLMService(settings)
translation_service = TranslationService(
    settings=settings,
    language_registry=language_registry,
    llm_service=llm_service,
)
language_quality_service = LanguageQualityService(
    settings=settings,
    language_registry=language_registry,
)
summarization_service = SummarizationService(
    settings=settings,
    document_service=document_service,
    chunking_service=document_chunking_service,
    llm_service=llm_service,
    translation_service=translation_service,
    language_registry=language_registry,
)
rag_service = RAGService(
    settings=settings,
    vector_store=vector_store,
    llm_service=llm_service,
    translation_service=translation_service,
    memory_store=memory_store,
    language_registry=language_registry,
    document_service=document_service,
    chunking_service=document_chunking_service,
)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Multilingual RAG assistant for research PDFs.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        app_name=settings.app_name,
        status="ok",
        llm_provider=settings.llm_provider,
        vector_store=settings.vector_db_provider,
    )


@app.get("/languages", response_model=list[Language])
def languages() -> list[Language]:
    return language_registry.languages


@app.get("/evaluation/language-quality", response_model=LanguageQualityReport)
def language_quality() -> LanguageQualityReport:
    return language_quality_service.report()


@app.get("/memory/status", response_model=MemoryStatusResponse)
def memory_status() -> MemoryStatusResponse:
    return MemoryStatusResponse(
        short_term_enabled=True,
        short_term_store="sqlite",
        long_term_enabled=False,
        long_term_collection=settings.qdrant_memory_collection,
        notes=(
            "Short-term conversation memory is active per session. "
            "Long-term memory is reserved for a separate Qdrant collection and is not mixed with document vectors."
        ),
    )


@app.get("/sessions", response_model=list[SessionSummary])
def list_sessions(limit: int = 25) -> list[SessionSummary]:
    return [
        SessionSummary(**session)
        for session in memory_store.list_sessions(limit=limit)
    ]


@app.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(session_id: str, limit: int = 100) -> SessionDetail:
    messages = memory_store.session_messages(session_id=session_id, limit=limit)
    return SessionDetail(
        session_id=session_id,
        message_count=len(messages),
        messages=messages,
    )


@app.delete("/sessions/{session_id}", response_model=MemoryDeleteResponse)
def delete_session(session_id: str) -> MemoryDeleteResponse:
    deleted = memory_store.delete_session(session_id)
    return MemoryDeleteResponse(
        deleted_messages=deleted,
        message=f"Deleted {deleted} messages for session {session_id}.",
    )


@app.delete("/sessions", response_model=MemoryDeleteResponse)
def clear_sessions() -> MemoryDeleteResponse:
    deleted = memory_store.clear_all()
    return MemoryDeleteResponse(
        deleted_messages=deleted,
        message=f"Deleted {deleted} messages across all sessions.",
    )


@app.get("/embeddings/models", response_model=list[EmbeddingModelInfo])
def embedding_models() -> list[EmbeddingModelInfo]:
    return embedding_registry.models


@app.post("/embeddings/compare", response_model=EmbeddingCompareResponse)
def compare_embeddings(request: EmbeddingCompareRequest) -> EmbeddingCompareResponse:
    try:
        return embedding_comparison_service.compare(
            query=request.query,
            positive_text=request.positive_text,
            negative_texts=request.negative_texts,
            model_ids=request.model_ids,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Embedding comparison failed: {exc}") from exc


@app.get("/documents", response_model=list[DocumentSummary])
def list_documents() -> list[DocumentSummary]:
    return document_service.list_documents()


@app.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str) -> DocumentDetail:
    try:
        return document_service.get_document(document_id)
    except DocumentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    filename = Path(file.filename or "document.pdf").name
    try:
        return document_service.upload_pdf(filename=filename, stream=file.file)
    except DocumentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/documents/{document_id}/chunks", response_model=ChunkingResponse)
def chunk_document(
    document_id: str,
    request: ChunkingRequest | None = None,
) -> ChunkingResponse:
    request = request or ChunkingRequest()
    try:
        return document_chunking_service.chunk_document(
            document_id=document_id,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )
    except DocumentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ChunkingServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.get("/documents/{document_id}/chunks", response_model=ChunkingResponse)
def get_document_chunks(document_id: str) -> ChunkingResponse:
    try:
        return document_chunking_service.get_chunks(document_id)
    except DocumentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ChunkingServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/documents/{document_id}/index", response_model=VectorIndexResponse)
def index_document(document_id: str) -> VectorIndexResponse:
    try:
        return vector_index_service.index_document(document_id)
    except DocumentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ChunkingServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not index chunks in Qdrant: {exc}") from exc


@app.post("/vectors/search", response_model=VectorSearchResponse)
def search_vectors(request: VectorSearchRequest) -> VectorSearchResponse:
    try:
        return vector_index_service.search(
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Vector search failed: {exc}") from exc


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        return rag_service.answer(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not answer question: {exc}") from exc


@app.post("/summarize", response_model=SummaryResponse)
def summarize(request: SummaryRequest) -> SummaryResponse:
    try:
        return summarization_service.summarize(request)
    except DocumentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ChunkingServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not summarize document: {exc}") from exc


@app.get("/translation/methods", response_model=list[TranslationMethodInfo])
def translation_methods() -> list[TranslationMethodInfo]:
    return translation_service.methods


@app.post("/translate", response_model=TranslateResponse)
def translate(request: TranslateRequest) -> TranslateResponse:
    if not is_supported_language(request.target_language):
        raise HTTPException(status_code=400, detail="Unsupported target language.")
    try:
        return translation_service.translate_with_metadata(
            text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
            method=request.method,
        )
    except TranslationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Translation failed: {exc}") from exc


@app.post("/translate/compare", response_model=TranslationCompareResponse)
def compare_translations(request: TranslationCompareRequest) -> TranslationCompareResponse:
    if not is_supported_language(request.target_language):
        raise HTTPException(status_code=400, detail="Unsupported target language.")
    try:
        return translation_service.compare(
            text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
            methods=request.methods,
        )
    except TranslationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Translation comparison failed: {exc}") from exc
