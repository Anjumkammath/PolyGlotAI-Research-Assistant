from __future__ import annotations

import json
import re

from backend.app.core.config import Settings
from backend.app.models.schemas import ChunkingResponse, ChunkPreview
from backend.app.services.chunker import TextChunk, TokenizerUnavailableError, chunk_pages
from backend.app.services.documents import DocumentService
from backend.app.services.languages import LanguageRegistry


class ChunkingServiceError(Exception):
    status_code = 400


class ChunksNotFoundError(ChunkingServiceError):
    status_code = 404


class ChunkingDependencyError(ChunkingServiceError):
    status_code = 500


class DocumentChunkingService:
    def __init__(
        self,
        settings: Settings,
        document_service: DocumentService,
        language_registry: LanguageRegistry,
    ) -> None:
        self.settings = settings
        self.document_service = document_service
        self.language_registry = language_registry
        self.chunk_dir = settings.chunk_dir
        self.chunk_dir.mkdir(parents=True, exist_ok=True)

    def chunk_document(
        self,
        document_id: str,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> ChunkingResponse:
        size = chunk_size or self.settings.chunk_size
        overlap = chunk_overlap if chunk_overlap is not None else self.settings.chunk_overlap
        if overlap >= size:
            raise ChunkingServiceError("chunk_overlap must be smaller than chunk_size.")

        detail = self.document_service.get_document(document_id)
        pages = self.document_service.extracted_pages(document_id)
        try:
            chunks = chunk_pages(
                pages=pages,
                chunk_size=size,
                chunk_overlap=overlap,
                language_resolver=self.language_registry.resolve_text,
            )
        except TokenizerUnavailableError as exc:
            raise ChunkingDependencyError(str(exc)) from exc
        if not chunks:
            raise ChunkingServiceError(
                "No text chunks could be created. The document may be scanned or empty."
            )

        detected_languages = sorted({chunk.language for chunk in chunks})
        self._persist_chunks(
            document_id=document_id,
            chunks=chunks,
            chunk_size=size,
            chunk_overlap=overlap,
        )
        self.document_service.mark_chunked(
            document_id=document_id,
            chunk_count=len(chunks),
            detected_languages=detected_languages,
        )

        return self._response(
            document_id=document_id,
            filename=detail.filename,
            chunks=chunks,
            chunk_size=size,
            chunk_overlap=overlap,
            message="Document text was chunked with language-aware metadata.",
        )

    def get_chunks(self, document_id: str) -> ChunkingResponse:
        detail = self.document_service.get_document(document_id)
        chunks, chunk_size, chunk_overlap = self.load_chunks(document_id)
        return self._response(
            document_id=document_id,
            filename=detail.filename,
            chunks=chunks,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            message="Loaded existing chunks for this document.",
        )

    def load_chunks(self, document_id: str) -> tuple[list[TextChunk], int, int]:
        path = self._chunk_path(document_id)
        if not path.exists():
            raise ChunksNotFoundError("Chunks have not been created for this document yet.")

        payload = json.loads(path.read_text(encoding="utf-8"))
        chunks = [
            TextChunk(
                text=str(item["text"]),
                page=int(item["page_start"]),
                chunk_index=int(item["chunk_index"]),
                language=str(item["language"]),
                tokenizer_strategy=str(item["tokenizer_strategy"]),
            )
            for item in payload.get("chunks", [])
        ]
        chunk_size = int(payload.get("chunk_size", self.settings.chunk_size))
        chunk_overlap = int(payload.get("chunk_overlap", self.settings.chunk_overlap))
        return chunks, chunk_size, chunk_overlap

    def _persist_chunks(
        self,
        document_id: str,
        chunks: list[TextChunk],
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        payload = {
            "document_id": document_id,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "chunks": [
                {
                    "chunk_id": self._chunk_id(document_id, chunk),
                    "chunk_index": chunk.chunk_index,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "language": chunk.language,
                    "tokenizer_strategy": chunk.tokenizer_strategy,
                    "character_count": chunk.character_count,
                    "text": chunk.text,
                }
                for chunk in chunks
            ],
        }
        self._chunk_path(document_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _response(
        self,
        document_id: str,
        filename: str,
        chunks: list[TextChunk],
        chunk_size: int,
        chunk_overlap: int,
        message: str,
    ) -> ChunkingResponse:
        detected_languages = sorted({chunk.language for chunk in chunks})
        strategies = sorted({chunk.tokenizer_strategy for chunk in chunks})
        return ChunkingResponse(
            document_id=document_id,
            filename=filename,
            chunk_count=len(chunks),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            detected_languages=detected_languages,
            tokenizer_strategies=strategies,
            chunks=[
                ChunkPreview(
                    chunk_id=self._chunk_id(document_id, chunk),
                    chunk_index=chunk.chunk_index,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    language=chunk.language,
                    tokenizer_strategy=chunk.tokenizer_strategy,
                    character_count=chunk.character_count,
                    preview=self._preview(chunk.text),
                )
                for chunk in chunks
            ],
            message=message,
        )

    def _chunk_path(self, document_id: str):
        return self.chunk_dir / f"{document_id}.json"

    @staticmethod
    def _chunk_id(document_id: str, chunk: TextChunk) -> str:
        return f"{document_id}:{chunk.chunk_index}"

    @staticmethod
    def _preview(text: str, limit: int = 450) -> str:
        normalized = re.sub(r"\s+", " ", text).strip()
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[:limit].rstrip()}..."
