from __future__ import annotations

import json
from math import sqrt
from pathlib import Path
from typing import Callable

from backend.app.core.config import get_settings
from backend.app.models.schemas import EmbeddingModelInfo


DEFAULT_EMBEDDING_MODELS = [
    EmbeddingModelInfo(
        id="multilingual-minilm",
        display_name="Multilingual MiniLM",
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        provider="sentence-transformers",
        strategy="default",
        dimension=384,
        recommended_for="Fast local baseline and early development.",
    ),
    EmbeddingModelInfo(
        id="multilingual-mpnet",
        display_name="Multilingual MPNet",
        model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        provider="sentence-transformers",
        strategy="default",
        dimension=768,
        recommended_for="Stronger multilingual semantic similarity baseline.",
    ),
    EmbeddingModelInfo(
        id="multilingual-e5-large",
        display_name="Multilingual E5 Large",
        model_name="intfloat/multilingual-e5-large",
        provider="sentence-transformers",
        strategy="e5",
        dimension=1024,
        query_prefix="query: ",
        document_prefix="passage: ",
        recommended_for="High-quality multilingual retrieval evaluation.",
    ),
]


ModelLoader = Callable[[str], object]


class EmbeddingModelRegistry:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or get_settings().embedding_config_path
        self._models = self._load_models()

    @property
    def models(self) -> list[EmbeddingModelInfo]:
        return [model for model in self._models if model.enabled]

    def get(self, model_id_or_name: str) -> EmbeddingModelInfo:
        for model in self.models:
            if model.id == model_id_or_name or model.model_name == model_id_or_name:
                return model

        return EmbeddingModelInfo(
            id=model_id_or_name,
            display_name=model_id_or_name,
            model_name=model_id_or_name,
            provider="sentence-transformers",
            strategy="default",
            dimension=0,
            notes="Ad-hoc model not found in embedding config.",
        )

    def _load_models(self) -> list[EmbeddingModelInfo]:
        if not self.config_path.exists():
            return DEFAULT_EMBEDDING_MODELS

        raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return DEFAULT_EMBEDDING_MODELS
        return [EmbeddingModelInfo(**item) for item in raw]


class EmbeddingService:
    def __init__(
        self,
        model_name: str,
        registry: EmbeddingModelRegistry | None = None,
        model_loader: ModelLoader | None = None,
    ) -> None:
        self.registry = registry or EmbeddingModelRegistry()
        self.model_info = self.registry.get(model_name)
        self.model_name = self.model_info.model_name
        self.model_id = self.model_info.id
        self.strategy = self.model_info.strategy
        self._model = None
        self._model_loader = model_loader

    @property
    def model(self):
        if self._model is None:
            if self._model_loader is not None:
                self._model = self._model_loader(self.model_name)
            else:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            [self.format_document(text) for text in texts],
            normalize_embeddings=True,
        )
        return _to_list(vectors)

    def embed_query(self, text: str) -> list[float]:
        vectors = self.model.encode([self.format_query(text)], normalize_embeddings=True)
        return _to_list(vectors)[0]

    def format_query(self, text: str) -> str:
        if self.strategy == "e5":
            return f"{self.model_info.query_prefix or 'query: '}{text}"
        return text

    def format_document(self, text: str) -> str:
        if self.strategy == "e5":
            return f"{self.model_info.document_prefix or 'passage: '}{text}"
        return text


def cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = sqrt(sum(a * a for a in left))
    right_norm = sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _to_list(vectors) -> list[list[float]]:
    if hasattr(vectors, "tolist"):
        return vectors.tolist()
    return vectors
