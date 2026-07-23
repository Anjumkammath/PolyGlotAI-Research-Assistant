from __future__ import annotations

from backend.app.models.schemas import (
    EmbeddingCandidateScore,
    EmbeddingCompareResponse,
    EmbeddingModelComparison,
)
from backend.app.services.embeddings import (
    EmbeddingModelRegistry,
    EmbeddingService,
    cosine_similarity,
)


class EmbeddingComparisonService:
    def __init__(self, registry: EmbeddingModelRegistry | None = None) -> None:
        self.registry = registry or EmbeddingModelRegistry()

    def compare(
        self,
        query: str,
        positive_text: str,
        negative_texts: list[str],
        model_ids: list[str] | None = None,
    ) -> EmbeddingCompareResponse:
        candidates = [("positive", positive_text)] + [
            (f"negative_{index}", text)
            for index, text in enumerate(negative_texts, start=1)
            if text.strip()
        ]
        selected_models = self._selected_models(model_ids or [])
        comparisons = [
            self._compare_one_model(
                model_id=model.id,
                query=query,
                candidates=candidates,
            )
            for model in selected_models
        ]
        return EmbeddingCompareResponse(query=query, comparisons=comparisons)

    def _compare_one_model(
        self,
        model_id: str,
        query: str,
        candidates: list[tuple[str, str]],
    ) -> EmbeddingModelComparison:
        service = EmbeddingService(model_id, registry=self.registry)
        query_vector = service.embed_query(query)
        document_vectors = service.embed_documents([text for _, text in candidates])
        scores = [
            EmbeddingCandidateScore(
                label=label,
                text=text,
                score=cosine_similarity(query_vector, vector),
            )
            for (label, text), vector in zip(candidates, document_vectors, strict=False)
        ]
        ranked_scores = sorted(scores, key=lambda score: score.score, reverse=True)
        positive_rank = next(
            (
                index
                for index, score in enumerate(ranked_scores, start=1)
                if score.label == "positive"
            ),
            len(ranked_scores),
        )
        return EmbeddingModelComparison(
            model_id=service.model_id,
            model_name=service.model_name,
            strategy=service.strategy,
            best_label=ranked_scores[0].label if ranked_scores else "",
            positive_rank=positive_rank,
            scores=ranked_scores,
        )

    def _selected_models(self, model_ids: list[str]):
        if not model_ids:
            return self.registry.models
        requested = set(model_ids)
        return [model for model in self.registry.models if model.id in requested]
