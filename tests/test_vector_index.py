from types import SimpleNamespace

from backend.app.services.chunker import TextChunk
from backend.app.services.vector_index import VectorIndexService
from backend.app.services.vector_store import VectorSearchHit


class FakeDocumentService:
    def __init__(self):
        self.indexed = []

    def get_document(self, document_id):
        return SimpleNamespace(document_id=document_id, filename="paper.pdf")

    def mark_indexed(self, document_id):
        self.indexed.append(document_id)


class FakeChunkingService:
    def load_chunks(self, document_id):
        return (
            [
                TextChunk(
                    text="multilingual retrieval",
                    page=1,
                    chunk_index=0,
                    language="en",
                    tokenizer_strategy="whitespace",
                )
            ],
            900,
            180,
        )


class FakeVectorStore:
    collection_name = "documents"

    def __init__(self):
        self.indexed = []
        self.embedding_service = SimpleNamespace(embed_query=lambda query: [0.1, 0.2])

    def add_chunks(self, document_id, filename, chunks):
        self.indexed.append((document_id, filename, chunks))

    def search_by_vector(self, query_embedding, top_k, document_id=None):
        return [
            VectorSearchHit(
                chunk_id="doc-1:0",
                document_id="doc-1",
                source_name="paper.pdf",
                page=1,
                text="multilingual retrieval",
                score=0.8,
                language="en",
                tokenizer_strategy="whitespace",
            )
        ]


def make_settings():
    return SimpleNamespace(
        embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        vector_db_provider="qdrant",
    )


def test_vector_index_service_indexes_document_chunks():
    document_service = FakeDocumentService()
    vector_store = FakeVectorStore()
    service = VectorIndexService(
        settings=make_settings(),
        document_service=document_service,
        chunking_service=FakeChunkingService(),
        vector_store=vector_store,
    )

    result = service.index_document("doc-1")

    assert result.collection_name == "documents"
    assert result.chunks_indexed == 1
    assert vector_store.indexed[0][0] == "doc-1"
    assert document_service.indexed == ["doc-1"]


def test_vector_index_service_search_returns_excerpts():
    service = VectorIndexService(
        settings=make_settings(),
        document_service=FakeDocumentService(),
        chunking_service=FakeChunkingService(),
        vector_store=FakeVectorStore(),
    )

    result = service.search("retrieval", top_k=1)

    assert result.collection_name == "documents"
    assert result.results[0].excerpt == "multilingual retrieval"
