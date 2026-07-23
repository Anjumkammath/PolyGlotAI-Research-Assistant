from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from backend.app.core.config import Settings
from backend.app.services.chunker import TextChunk
from backend.app.services.embeddings import EmbeddingService


@dataclass(frozen=True)
class VectorSearchHit:
    chunk_id: str
    document_id: str
    source_name: str
    page: int
    text: str
    score: float | None
    page_start: int | None = None
    page_end: int | None = None
    language: str | None = None
    tokenizer_strategy: str | None = None


class VectorStore:
    def __init__(
        self,
        settings: Settings,
        embedding_service: EmbeddingService,
        client=None,
    ) -> None:
        self.settings = settings
        self.embedding_service = embedding_service
        self.collection_name = settings.qdrant_document_collection
        self.vector_size = settings.qdrant_vector_size
        self._client = client

    @property
    def client(self):
        if self._client is None:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(
                url=self.settings.qdrant_url,
                api_key=self.settings.qdrant_api_key or None,
            )
        return self._client

    def ensure_collection(self, vector_size: int | None = None) -> None:
        size = vector_size or self.vector_size
        existing = {collection.name for collection in self.client.get_collections().collections}
        if self.collection_name in existing:
            collection_info = self.client.get_collection(collection_name=self.collection_name)
            existing_size = _collection_vector_size(collection_info)
            if existing_size is not None and existing_size != size:
                raise ValueError(
                    f"Qdrant collection '{self.collection_name}' has vector size "
                    f"{existing_size}, but the active embedding model outputs {size}. "
                    "Use a model-specific collection name or recreate this collection "
                    "before indexing/searching with the new embedding model."
                )
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=_vector_params(size),
        )

    def add_chunks(
        self,
        document_id: str,
        filename: str,
        chunks: list[TextChunk],
    ) -> None:
        if not chunks:
            return

        documents = [chunk.text for chunk in chunks]
        embeddings = self.embedding_service.embed_documents(documents)
        if embeddings:
            self.ensure_collection(vector_size=len(embeddings[0]))

        points = [
            _point_struct(
                point_id=_point_id(document_id, chunk.chunk_index),
                vector=embedding,
                payload={
                    "chunk_id": f"{document_id}:{chunk.chunk_index}",
                    "text": chunk.text,
                    "document_id": document_id,
                    "source_name": filename,
                    "page": chunk.page,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "chunk_index": chunk.chunk_index,
                    "language": chunk.language,
                    "tokenizer_strategy": chunk.tokenizer_strategy,
                },
            )
            for chunk, embedding in zip(chunks, embeddings, strict=False)
        ]

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    def query(
        self,
        question: str,
        top_k: int,
        document_id: str | None = None,
    ) -> list[VectorSearchHit]:
        query_embedding = self.embedding_service.embed_query(question)
        return self.search_by_vector(
            query_embedding=query_embedding,
            top_k=top_k,
            document_id=document_id,
        )

    def search_by_vector(
        self,
        query_embedding: list[float],
        top_k: int,
        document_id: str | None = None,
    ) -> list[VectorSearchHit]:
        self.ensure_collection(vector_size=len(query_embedding))

        query_filter = None
        if document_id:
            query_filter = _document_filter(document_id)

        if hasattr(self.client, "search"):
            points = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
        else:
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
            points = getattr(response, "points", response)
        return [_hit_from_point(point) for point in points]


def _point_id(document_id: str, chunk_index: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"{document_id}:{chunk_index}"))


def _vector_params(size: int):
    from qdrant_client.models import Distance, VectorParams

    return VectorParams(size=size, distance=Distance.COSINE)


def _point_struct(point_id: str, vector: list[float], payload: dict):
    from qdrant_client.models import PointStruct

    return PointStruct(id=point_id, vector=vector, payload=payload)


def _document_filter(document_id: str):
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    return Filter(
        must=[
            FieldCondition(
                key="document_id",
                match=MatchValue(value=document_id),
            )
        ]
    )


def _hit_from_point(point) -> VectorSearchHit:
    payload = point.payload or {}
    return VectorSearchHit(
        chunk_id=str(payload.get("chunk_id", point.id)),
        document_id=str(payload.get("document_id", "")),
        source_name=str(payload.get("source_name", "Unknown source")),
        page=int(payload.get("page", payload.get("page_start", 0)) or 0),
        page_start=_optional_int(payload.get("page_start")),
        page_end=_optional_int(payload.get("page_end")),
        text=str(payload.get("text", "")),
        score=None if point.score is None else float(point.score),
        language=_optional_str(payload.get("language")),
        tokenizer_strategy=_optional_str(payload.get("tokenizer_strategy")),
    )


def _collection_vector_size(collection_info) -> int | None:
    vectors = getattr(
        getattr(getattr(collection_info, "config", None), "params", None),
        "vectors",
        None,
    )
    if vectors is None and isinstance(collection_info, dict):
        vectors = (
            collection_info.get("config", {})
            .get("params", {})
            .get("vectors")
        )
    if vectors is None:
        return None
    if isinstance(vectors, dict):
        if "size" in vectors:
            return _optional_int(vectors.get("size"))
        for value in vectors.values():
            nested_size = _vector_size_from_object(value)
            if nested_size is not None:
                return nested_size
        return None
    return _vector_size_from_object(vectors)


def _vector_size_from_object(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return _optional_int(value.get("size")) if value.get("size") is not None else None
    size = getattr(value, "size", None)
    return _optional_int(size) if size is not None else None


def _optional_int(value) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_str(value) -> str | None:
    if value is None:
        return None
    return str(value)
