from __future__ import annotations

import re

from backend.app.core.config import Settings
from backend.app.models.schemas import Citation, SummaryRequest, SummaryResponse
from backend.app.services.chunker import TextChunk
from backend.app.services.document_chunks import ChunksNotFoundError, DocumentChunkingService
from backend.app.services.documents import DocumentService
from backend.app.services.languages import LanguageRegistry
from backend.app.services.llm import LLMService
from backend.app.services.text_cleanup import clean_pdf_text
from backend.app.services.translator import TranslationService
from backend.app.services.vector_store import VectorSearchHit


class SummarizationService:
    def __init__(
        self,
        settings: Settings,
        document_service: DocumentService,
        chunking_service: DocumentChunkingService,
        llm_service: LLMService,
        translation_service: TranslationService,
        language_registry: LanguageRegistry,
    ) -> None:
        self.settings = settings
        self.document_service = document_service
        self.chunking_service = chunking_service
        self.llm_service = llm_service
        self.translation_service = translation_service
        self.language_registry = language_registry

    def summarize(self, request: SummaryRequest) -> SummaryResponse:
        detail = self.document_service.get_document(request.document_id)
        target_language = request.target_language
        if not self.language_registry.is_supported(target_language):
            target_language = self.settings.default_answer_language

        chunks = self._load_or_create_chunks(request.document_id)
        selected_chunks = _select_representative_chunks(chunks, request.max_chunks)
        hits = [
            _chunk_to_hit(
                chunk=chunk,
                document_id=request.document_id,
                filename=detail.filename,
            )
            for chunk in selected_chunks
        ]

        summary = self.llm_service.summarize(
            document_name=detail.filename,
            summary_type=request.summary_type,
            context_hits=hits,
            target_language=target_language,
        )

        translation_applied = False
        if (
            request.translate_summary
            and self.settings.llm_provider.lower().strip() == "fallback"
            and target_language != "en"
        ):
            try:
                summary = self.translation_service.translate(
                    text=summary,
                    source_language="auto",
                    target_language=target_language,
                )
                translation_applied = True
            except Exception:
                translation_applied = False

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
            for index, hit in enumerate(hits, start=1)
        ]

        return SummaryResponse(
            document_id=request.document_id,
            filename=detail.filename,
            summary_type=request.summary_type,
            target_language=target_language,
            summary=summary,
            citations=citations,
            chunks_used=len(hits),
            context_available=bool(hits),
            translation_applied=translation_applied,
        )

    def _load_or_create_chunks(self, document_id: str) -> list[TextChunk]:
        try:
            chunks, _, _ = self.chunking_service.load_chunks(document_id)
        except ChunksNotFoundError:
            self.chunking_service.chunk_document(document_id)
            chunks, _, _ = self.chunking_service.load_chunks(document_id)
        return chunks


def _select_representative_chunks(
    chunks: list[TextChunk],
    max_chunks: int,
) -> list[TextChunk]:
    if len(chunks) <= max_chunks:
        return chunks
    if max_chunks <= 1:
        return [chunks[0]]

    indexes = {
        round(index * (len(chunks) - 1) / (max_chunks - 1))
        for index in range(max_chunks)
    }
    return [chunks[index] for index in sorted(indexes)]


def _chunk_to_hit(
    chunk: TextChunk,
    document_id: str,
    filename: str,
) -> VectorSearchHit:
    return VectorSearchHit(
        chunk_id=f"{document_id}:{chunk.chunk_index}",
        document_id=document_id,
        source_name=filename,
        page=chunk.page,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        text=chunk.text,
        score=None,
        language=chunk.language,
        tokenizer_strategy=chunk.tokenizer_strategy,
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
