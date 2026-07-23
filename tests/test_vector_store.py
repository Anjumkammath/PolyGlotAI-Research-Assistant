from types import SimpleNamespace

from backend.app.services.chunker import TextChunk
from backend.app.services.vector_store import VectorStore


class FakeEmbeddingService:
    def embed_documents(self, texts):
        return [[float(index), float(index + 1)] for index, _ in enumerate(texts)]

    def embed_query(self, text):
        return [0.0, 1.0]


class FakeQdrantClient:
    def __init__(self):
        self.created = []
        self.upserts = []

    def get_collections(self):
        return SimpleNamespace(collections=[])

    def get_collection(self, collection_name):
        return SimpleNamespace(
            config=SimpleNamespace(
                params=SimpleNamespace(
                    vectors=SimpleNamespace(size=2),
                )
            )
        )

    def create_collection(self, collection_name, vectors_config):
        self.created.append((collection_name, vectors_config))

    def upsert(self, collection_name, points):
        self.upserts.append((collection_name, points))

    def search(self, collection_name, query_vector, query_filter, limit, with_payload):
        return [
            SimpleNamespace(
                id="point-1",
                score=0.91,
                payload={
                    "chunk_id": "doc-1:0",
                    "document_id": "doc-1",
                    "source_name": "paper.pdf",
                    "page": 2,
                    "page_start": 2,
                    "page_end": 2,
                    "text": "retrieved passage",
                    "language": "en",
                    "tokenizer_strategy": "whitespace",
                },
            )
        ]


def make_settings():
    return SimpleNamespace(
        qdrant_document_collection="documents",
        qdrant_vector_size=2,
        qdrant_url="http://localhost:6333",
        qdrant_api_key=None,
    )


def test_vector_store_upserts_chunks_with_payload(monkeypatch):
    client = FakeQdrantClient()
    store = VectorStore(make_settings(), FakeEmbeddingService(), client=client)
    monkeypatch.setattr(
        "backend.app.services.vector_store._vector_params",
        lambda size: {"size": size, "distance": "Cosine"},
    )
    monkeypatch.setattr(
        "backend.app.services.vector_store._point_struct",
        lambda point_id, vector, payload: {
            "id": point_id,
            "vector": vector,
            "payload": payload,
        },
    )

    store.add_chunks(
        document_id="doc-1",
        filename="paper.pdf",
        chunks=[
            TextChunk(
                text="hello world",
                page=1,
                chunk_index=0,
                language="en",
                tokenizer_strategy="whitespace",
            )
        ],
    )

    assert client.created[0][0] == "documents"
    collection_name, points = client.upserts[0]
    assert collection_name == "documents"
    assert points[0]["payload"]["document_id"] == "doc-1"
    assert points[0]["payload"]["text"] == "hello world"


def test_vector_store_search_maps_qdrant_payload(monkeypatch):
    store = VectorStore(make_settings(), FakeEmbeddingService(), client=FakeQdrantClient())
    monkeypatch.setattr(
        "backend.app.services.vector_store._vector_params",
        lambda size: {"size": size, "distance": "Cosine"},
    )
    monkeypatch.setattr(
        "backend.app.services.vector_store._document_filter",
        lambda document_id: {"document_id": document_id},
    )

    results = store.search_by_vector([0.0, 1.0], top_k=1, document_id="doc-1")

    assert len(results) == 1
    assert results[0].chunk_id == "doc-1:0"
    assert results[0].score == 0.91
    assert results[0].language == "en"


def test_vector_store_rejects_existing_collection_with_wrong_dimension():
    class ExistingWrongSizeClient(FakeQdrantClient):
        def get_collections(self):
            return SimpleNamespace(collections=[SimpleNamespace(name="documents")])

        def get_collection(self, collection_name):
            return SimpleNamespace(
                config=SimpleNamespace(
                    params=SimpleNamespace(
                        vectors=SimpleNamespace(size=768),
                    )
                )
            )

    store = VectorStore(make_settings(), FakeEmbeddingService(), client=ExistingWrongSizeClient())

    try:
        store.ensure_collection(vector_size=384)
    except ValueError as exc:
        assert "vector size 768" in str(exc)
        assert "outputs 384" in str(exc)
    else:
        raise AssertionError("Expected vector dimension mismatch to raise ValueError")
