from __future__ import annotations

import re

from backend.app.core.config import Settings
from backend.app.models.schemas import (
    VectorIndexResponse,
    VectorSearchResponse,
    VectorSearchResult,
)
from backend.app.services.document_chunks import ChunksNotFoundError, DocumentChunkingService
from backend.app.services.documents import DocumentService
from backend.app.services.vector_store import VectorStore


class VectorIndexService:
    def __init__(
        self,
        settings: Settings,
        document_service: DocumentService,
        chunking_service: DocumentChunkingService,
        vector_store: VectorStore,
    ) -> None:
        self.settings = settings
        self.document_service = document_service
        self.chunking_service = chunking_service
        self.vector_store = vector_store

    def index_document(self, document_id: str) -> VectorIndexResponse:
        detail = self.document_service.get_document(document_id)
        try:
            chunks, _, _ = self.chunking_service.load_chunks(document_id)
        except ChunksNotFoundError:
            chunking_response = self.chunking_service.chunk_document(document_id)
            chunks, _, _ = self.chunking_service.load_chunks(chunking_response.document_id)

        self.vector_store.add_chunks(
            document_id=document_id,
            filename=detail.filename,
            chunks=chunks,
        )
        self.document_service.mark_indexed(document_id)

        return VectorIndexResponse(
            document_id=document_id,
            filename=detail.filename,
            collection_name=self.vector_store.collection_name,
            chunks_indexed=len(chunks),
            embedding_model=getattr(
                self.vector_store.embedding_service,
                "model_id",
                self.settings.embedding_model,
            ),
            vector_db_provider=self.settings.vector_db_provider,
            message="Document chunks were embedded and stored in Qdrant.",
        )

    def search(
        self,
        query: str,
        top_k: int,
        document_id: str | None = None,
    ) -> VectorSearchResponse:
        query_embedding = self.vector_store.embedding_service.embed_query(query)
        hits = self.vector_store.search_by_vector(
            query_embedding=query_embedding,
            top_k=top_k,
            document_id=document_id,
        )
        return VectorSearchResponse(
            query=query,
            collection_name=self.vector_store.collection_name,
            results=[
                VectorSearchResult(
                    chunk_id=hit.chunk_id,
                    document_id=hit.document_id,
                    source_name=hit.source_name,
                    page=hit.page,
                    score=hit.score,
                    language=hit.language,
                    tokenizer_strategy=hit.tokenizer_strategy,
                    excerpt=_preview(hit.text),
                )
                for hit in hits
            ],
        )


def _preview(text: str, limit: int = 500) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."
