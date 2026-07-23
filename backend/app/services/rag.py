from pathlib import Path
from dataclasses import dataclass
import logging
import re
from uuid import uuid4

from backend.app.core.config import Settings
from backend.app.models.schemas import ChatRequest, ChatResponse, Citation, UploadResponse
from backend.app.services.chunker import chunk_pages
from backend.app.services.document_chunks import ChunksNotFoundError, DocumentChunkingService
from backend.app.services.documents import DocumentService
from backend.app.services.languages import LanguageRegistry, get_language_registry
from backend.app.services.llm import LLMService
from backend.app.services.memory import MemoryStore
from backend.app.services.pdf_loader import extract_pdf_pages
from backend.app.services.text_cleanup import clean_pdf_text
from backend.app.services.translator import TranslationService
from backend.app.services.vector_store import VectorSearchHit, VectorStore


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievalResult:
    hits: list[VectorSearchHit]
    mode: str
    warning: str | None = None


class RAGService:
    def __init__(
        self,
        settings: Settings,
        vector_store: VectorStore,
        llm_service: LLMService,
        translation_service: TranslationService,
        memory_store: MemoryStore,
        language_registry: LanguageRegistry | None = None,
        document_service: DocumentService | None = None,
        chunking_service: DocumentChunkingService | None = None,
    ) -> None:
        self.settings = settings
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.translation_service = translation_service
        self.memory_store = memory_store
        self.language_registry = language_registry or get_language_registry()
        self.document_service = document_service
        self.chunking_service = chunking_service

    def ingest_pdf(
        self,
        pdf_path: Path,
        original_filename: str,
        document_id: str | None = None,
    ) -> UploadResponse:
        pages = extract_pdf_pages(pdf_path)
        chunks = chunk_pages(
            pages=pages,
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            language_resolver=self.language_registry.resolve_text,
        )
        document_id = document_id or str(uuid4())
        self.vector_store.add_chunks(
            document_id=document_id,
            filename=original_filename,
            chunks=chunks,
        )
        return UploadResponse(
            document_id=document_id,
            filename=original_filename,
            pages=len(pages),
            chunks_indexed=len(chunks),
        )

    def answer(self, request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or str(uuid4())
        question = request.question.strip()
        target_language = request.target_language
        if not self.language_registry.is_supported(target_language):
            target_language = self.settings.default_answer_language

        self.memory_store.add_message(
            session_id=session_id,
            role="user",
            content=question,
            language=target_language,
            document_id=request.document_id,
            metadata={
                "top_k": request.top_k,
                "translate_answer": request.translate_answer,
                "answer_style": request.answer_style,
            },
        )
        memory_messages = self.memory_store.recent_messages(session_id=session_id)
        retrieval_result = self._retrieve_hits(
            question=question,
            top_k=min(request.top_k, self.settings.max_context_chunks),
            document_id=request.document_id,
        )
        hits = retrieval_result.hits
        document_type = _classify_document_type(hits)
        answer = self.llm_service.answer(
            question=question,
            context_hits=hits,
            memory_messages=memory_messages,
            target_language=target_language,
            answer_style=request.answer_style,
        )

        translation_applied = False
        if (
            request.translate_answer
            and self.settings.llm_provider.lower().strip() == "fallback"
            and target_language != "en"
        ):
            try:
                answer = self.translation_service.translate(
                    text=answer,
                    source_language="auto",
                    target_language=target_language,
                )
                translation_applied = True
            except Exception:
                translation_applied = False

        citation_pairs = _referenced_hit_pairs(answer, hits)
        grounding_verified = bool(citation_pairs)
        citation_confidence = _citation_confidence(answer=answer, hits=hits, citation_pairs=citation_pairs)
        citation_warning = _citation_warning(answer=answer, hits=hits, citation_pairs=citation_pairs)
        self.memory_store.add_message(
            session_id=session_id,
            role="assistant",
            content=answer,
            language=target_language,
            document_id=request.document_id,
            metadata={
                "retrieved_chunks": len(hits),
                "cited_chunks": len(citation_pairs),
                "citation_count": len(citation_pairs),
                "grounding_verified": grounding_verified,
                "citation_confidence": citation_confidence,
                "retrieval_mode": retrieval_result.mode,
                "retrieval_warning": retrieval_result.warning,
                "citation_warning": citation_warning,
                "translation_applied": translation_applied,
                "answer_style": request.answer_style,
                "document_type": document_type,
            },
        )

        citations = [
            Citation(
                citation_id=f"C{index}",
                source_name=hit.source_name,
                page=hit.page,
                chunk_id=hit.chunk_id,
                excerpt=_excerpt(hit.text),
                score=hit.score,
                page_start=hit.page_start,
                page_end=hit.page_end,
                language=hit.language,
                tokenizer_strategy=hit.tokenizer_strategy,
            )
            for index, hit in citation_pairs
        ]
        retrieved_context = [
            Citation(
                citation_id=f"C{index}",
                source_name=hit.source_name,
                page=hit.page,
                chunk_id=hit.chunk_id,
                excerpt=_excerpt(hit.text),
                score=hit.score,
                page_start=hit.page_start,
                page_end=hit.page_end,
                language=hit.language,
                tokenizer_strategy=hit.tokenizer_strategy,
            )
            for index, hit in enumerate(hits, start=1)
        ]
        return ChatResponse(
            session_id=session_id,
            answer=answer,
            target_language=target_language,
            answer_style=request.answer_style,
            document_type=document_type,
            citations=citations,
            retrieved_context=retrieved_context,
            memory_turns_used=len(memory_messages),
            retrieved_chunks=len(hits),
            cited_chunks=len(citation_pairs),
            context_available=bool(hits),
            retrieval_query=question,
            retrieval_mode=retrieval_result.mode,
            retrieval_warning=retrieval_result.warning,
            grounding_verified=grounding_verified,
            citation_confidence=citation_confidence,
            citation_warning=citation_warning,
            translation_applied=translation_applied,
        )

    def _retrieve_hits(
        self,
        question: str,
        top_k: int,
        document_id: str | None,
    ) -> RetrievalResult:
        if document_id and _is_document_overview_question(question):
            overview_hits = self._overview_local_chunks(
                document_id=document_id,
                top_k=max(top_k, min(self.settings.max_context_chunks, 5)),
            )
            if overview_hits:
                return RetrievalResult(
                    hits=overview_hits,
                    mode="overview_bypass",
                    warning=(
                        "Overview questions use document-order chunks for readability; "
                        "this is not vector similarity retrieval."
                    ),
                )

        if not self._should_use_vector_search(document_id):
            hits = self._search_local_chunks(
                question=question,
                top_k=top_k,
                document_id=document_id,
            )
            return RetrievalResult(
                hits=hits,
                mode="lexical_fallback",
                warning=(
                    "This document is not indexed in Qdrant, so PolyGlotAI used local lexical "
                    "fallback search. Cross-lingual retrieval may be weaker."
                ),
            )

        try:
            hits = self.vector_store.query(
                question=question,
                top_k=top_k,
                document_id=document_id,
            )
        except Exception as exc:
            logger.warning(
                "Vector retrieval failed; using lexical fallback. document_id=%s error=%s",
                document_id,
                exc,
            )
            hits = self._search_local_chunks(
                question=question,
                top_k=top_k,
                document_id=document_id,
            )
            return RetrievalResult(
                hits=hits,
                mode="lexical_fallback",
                warning=(
                    "Vector search failed, so PolyGlotAI used local lexical fallback search. "
                    "Cross-lingual retrieval may be weaker."
                ),
            )

        if hits:
            return RetrievalResult(hits=hits, mode="vector")

        fallback_hits = self._search_local_chunks(
            question=question,
            top_k=top_k,
            document_id=document_id,
        )
        return RetrievalResult(
            hits=fallback_hits,
            mode="lexical_fallback",
            warning=(
                "Vector search returned no passages, so PolyGlotAI used local lexical "
                "fallback search. Cross-lingual retrieval may be weaker."
            ),
        )

    def _should_use_vector_search(self, document_id: str | None) -> bool:
        if self.document_service is None:
            return True
        try:
            if document_id:
                return bool(self.document_service.get_document(document_id).indexed)
            return any(document.indexed for document in self.document_service.list_documents())
        except Exception:
            return True

    def _search_local_chunks(
        self,
        question: str,
        top_k: int,
        document_id: str | None,
    ) -> list[VectorSearchHit]:
        if self.document_service is None or self.chunking_service is None:
            return []

        documents = self._candidate_documents(document_id)
        candidates = []
        for document in documents:
            chunks = self._load_or_create_chunks(document.document_id)
            for chunk in chunks:
                score = _lexical_score(question, chunk.text)
                candidates.append((score, document, chunk))

        if not candidates:
            return []

        candidates.sort(
            key=lambda item: (item[0], -item[2].chunk_index),
            reverse=True,
        )
        positive_matches = [item for item in candidates if item[0] > 0]
        selected = (positive_matches or candidates)[:top_k]

        return [
            VectorSearchHit(
                chunk_id=f"{document.document_id}:{chunk.chunk_index}",
                document_id=document.document_id,
                source_name=document.filename,
                page=chunk.page,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                text=chunk.text,
                score=score,
                language=chunk.language,
                tokenizer_strategy=chunk.tokenizer_strategy,
            )
            for score, document, chunk in selected
        ]

    def _overview_local_chunks(
        self,
        document_id: str,
        top_k: int,
    ) -> list[VectorSearchHit]:
        if self.document_service is None or self.chunking_service is None:
            return []

        try:
            document = self.document_service.get_document(document_id)
        except Exception:
            return []

        chunks = self._load_or_create_chunks(document_id)
        if not chunks:
            return []

        scored_chunks = [
            (_overview_chunk_score(chunk.text, chunk.chunk_index), chunk)
            for chunk in chunks
        ]
        scored_chunks.sort(
            key=lambda item: (item[0], -item[1].chunk_index),
            reverse=True,
        )
        selected = scored_chunks[:top_k]
        selected.sort(key=lambda item: item[1].chunk_index)

        return [
            VectorSearchHit(
                chunk_id=f"{document.document_id}:{chunk.chunk_index}",
                document_id=document.document_id,
                source_name=document.filename,
                page=chunk.page,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                text=chunk.text,
                score=round(score, 4),
                language=chunk.language,
                tokenizer_strategy=chunk.tokenizer_strategy,
            )
            for score, chunk in selected
        ]

    def _candidate_documents(self, document_id: str | None):
        if self.document_service is None:
            return []
        if document_id:
            try:
                return [self.document_service.get_document(document_id)]
            except Exception:
                return []
        try:
            return self.document_service.list_documents()
        except Exception:
            return []

    def _load_or_create_chunks(self, document_id: str):
        if self.chunking_service is None:
            return []
        try:
            chunks, _, _ = self.chunking_service.load_chunks(document_id)
        except ChunksNotFoundError:
            try:
                self.chunking_service.chunk_document(document_id)
                chunks, _, _ = self.chunking_service.load_chunks(document_id)
            except Exception:
                return []
        except Exception:
            return []
        return chunks


def _query_terms(text: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[\w]+", text.lower(), flags=re.UNICODE)
        if len(term) > 2
    }


def _lexical_score(question: str, text: str) -> float:
    terms = _query_terms(question)
    if not terms:
        return 0.0
    normalized_text = text.lower()
    matches = sum(1 for term in terms if term in normalized_text)
    return round(matches / len(terms), 4)


def _is_document_overview_question(question: str) -> bool:
    normalized = question.lower().strip()
    if re.search(r"\b(summary|summarize|overview|main idea)\b", normalized):
        return True
    if re.search(r"\bwhat\s+is\s+(this|it)\s+about\b", normalized):
        return True
    if re.search(r"\bwhat\s+does\s+(this|it)\s+(explain|discuss|cover)\b", normalized):
        return True
    if re.search(
        r"\b(what|tell\s+me).*\b(paper|document|pdf|file|resume|cv)\b.*\b(about|explain|discuss|cover)\b",
        normalized,
    ):
        return True
    if re.search(
        r"\b(paper|document|pdf|file|resume|cv)\b.*\b(about|explain|discuss|cover)\b",
        normalized,
    ):
        return True
    return False


def _overview_chunk_score(text: str, chunk_index: int) -> float:
    normalized = text.lower()
    markers = [
        "abstract",
        "introduction",
        "objective",
        "overview",
        "professional summary",
        "technical skills",
        "work experience",
        "projects",
        "education",
        "conclusion",
    ]
    marker_score = sum(2.0 for marker in markers if marker in normalized)
    early_score = max(0.0, 5.0 - min(chunk_index, 5))
    return marker_score + early_score


def _classify_document_type(hits: list[VectorSearchHit]) -> str | None:
    if not hits:
        return None

    combined = clean_pdf_text(" ".join(hit.text for hit in hits[:8])).lower()
    resume_markers = [
        "professional summary",
        "technical skills",
        "work experience",
        "projects",
        "education",
        "certifications",
    ]
    research_markers = [
        "abstract",
        "introduction",
        "method",
        "methodology",
        "experiment",
        "results",
        "references",
        "conclusion",
    ]
    notes_markers = [
        "notes by",
        "what is",
        "data types",
        "syntax",
        "commands",
        "example",
    ]

    if sum(1 for marker in resume_markers if marker in combined) >= 2:
        return "resume_cv"
    if sum(1 for marker in research_markers if marker in combined) >= 3:
        return "research_paper"
    if sum(1 for marker in notes_markers if marker in combined) >= 2:
        return "study_notes"
    return "document"


def _referenced_hit_pairs(
    answer: str,
    hits: list[VectorSearchHit],
) -> list[tuple[int, VectorSearchHit]]:
    referenced = {
        int(match)
        for match in re.findall(r"\[C(\d+)\]", answer)
        if match.isdigit()
    }
    if not referenced:
        return []
    return [
        (index, hit)
        for index, hit in enumerate(hits, start=1)
        if index in referenced
    ]


def _citation_confidence(
    answer: str,
    hits: list[VectorSearchHit],
    citation_pairs: list[tuple[int, VectorSearchHit]],
) -> str:
    if not hits:
        return "none"
    if not re.search(r"\[C\d+\]", answer):
        return "none"
    if citation_pairs and len(citation_pairs) == len(hits):
        return "high"
    if citation_pairs:
        return "partial"
    return "invalid"


def _citation_warning(
    answer: str,
    hits: list[VectorSearchHit],
    citation_pairs: list[tuple[int, VectorSearchHit]],
) -> str | None:
    if not hits:
        return None
    if citation_pairs:
        return None
    if re.search(r"\[C\d+\]", answer):
        return (
            "The answer included citation markers, but none matched retrieved source IDs. "
            "Sources are shown only as retrieved context."
        )
    return (
        "The answer did not include valid inline citation markers. Sources are shown "
        "as retrieved context, not verified claim-level citations."
    )


def _excerpt(text: str, limit: int = 500) -> str:
    normalized = _clean_pdf_text(text)
    normalized = re.sub(r"([A-Za-z])-\s+([a-z])", r"\1\2", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def _clean_pdf_text(text: str) -> str:
    return clean_pdf_text(text)
