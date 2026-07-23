from pathlib import Path

from backend.app.services.embedding_comparison import EmbeddingComparisonService
from backend.app.services.embeddings import (
    EmbeddingModelRegistry,
    EmbeddingService,
    cosine_similarity,
)


class FakeVectorBatch(list):
    def tolist(self):
        return list(self)


class FakeModel:
    def __init__(self):
        self.encoded = []

    def encode(self, texts, normalize_embeddings=True):
        self.encoded.append(texts)
        vectors = []
        for text in texts:
            if "query:" in text:
                vectors.append([1.0, 0.0])
            elif "relevant" in text:
                vectors.append([1.0, 0.0])
            else:
                vectors.append([0.0, 1.0])
        return FakeVectorBatch(vectors)


def test_embedding_registry_loads_configured_models():
    registry = EmbeddingModelRegistry(Path("config/embedding_models.json"))

    ids = {model.id for model in registry.models}

    assert "multilingual-mpnet" in ids
    assert "multilingual-e5-large" in ids
    assert registry.get("multilingual-e5-large").strategy == "e5"


def test_embedding_service_formats_e5_inputs():
    registry = EmbeddingModelRegistry(Path("config/embedding_models.json"))
    fake_model = FakeModel()
    service = EmbeddingService(
        "multilingual-e5-large",
        registry=registry,
        model_loader=lambda model_name: fake_model,
    )

    service.embed_query("What is the paper about?")
    service.embed_documents(["This is a relevant passage."])

    assert fake_model.encoded[0][0].startswith("query: ")
    assert fake_model.encoded[1][0].startswith("passage: ")


def test_cosine_similarity_scores_identical_vectors_highest():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_embedding_comparison_ranks_positive_first(monkeypatch):
    registry = EmbeddingModelRegistry(Path("config/embedding_models.json"))

    class FakeEmbeddingService:
        def __init__(self, model_id, registry):
            model = registry.get(model_id)
            self.model_id = model.id
            self.model_name = model.model_name
            self.strategy = model.strategy

        def embed_query(self, query):
            return [1.0, 0.0]

        def embed_documents(self, texts):
            return [
                [1.0, 0.0] if "relevant" in text else [0.0, 1.0]
                for text in texts
            ]

    monkeypatch.setattr(
        "backend.app.services.embedding_comparison.EmbeddingService",
        FakeEmbeddingService,
    )
    service = EmbeddingComparisonService(registry)

    result = service.compare(
        query="main contribution",
        positive_text="relevant passage",
        negative_texts=["unrelated passage"],
        model_ids=["multilingual-minilm"],
    )

    assert result.comparisons[0].best_label == "positive"
    assert result.comparisons[0].positive_rank == 1
