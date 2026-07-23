from types import SimpleNamespace

from backend.app.models.schemas import SummaryRequest
from backend.app.services.chunker import TextChunk
from backend.app.services.summarization import SummarizationService


class FakeDocumentService:
    def get_document(self, document_id):
        return SimpleNamespace(document_id=document_id, filename="paper.pdf")


class FakeChunkingService:
    def __init__(self, chunks):
        self.chunks = chunks

    def load_chunks(self, document_id):
        return self.chunks, 900, 180


class FakeLLMService:
    def __init__(self):
        self.calls = []

    def summarize(self, document_name, summary_type, context_hits, target_language):
        self.calls.append(
            {
                "document_name": document_name,
                "summary_type": summary_type,
                "context_hits": context_hits,
                "target_language": target_language,
            }
        )
        return "This paper studies multilingual retrieval [C1]."


class FakeTranslationService:
    def translate(self, text, source_language, target_language):
        return f"{target_language}: {text}"


class FakeLanguageRegistry:
    def is_supported(self, code):
        return code in {"en", "hi", "ja"}


def make_settings(llm_provider="openai"):
    return SimpleNamespace(
        default_answer_language="en",
        llm_provider=llm_provider,
    )


def make_chunks(count=4):
    return [
        TextChunk(
            text=f"Chunk {index} discusses multilingual retrieval.",
            page=index + 1,
            chunk_index=index,
            language="en",
            tokenizer_strategy="whitespace",
        )
        for index in range(count)
    ]


def test_summarization_returns_cited_summary():
    llm_service = FakeLLMService()
    service = SummarizationService(
        settings=make_settings(),
        document_service=FakeDocumentService(),
        chunking_service=FakeChunkingService(make_chunks(3)),
        llm_service=llm_service,
        translation_service=FakeTranslationService(),
        language_registry=FakeLanguageRegistry(),
    )

    response = service.summarize(
        SummaryRequest(
            document_id="doc-1",
            summary_type="technical",
            target_language="en",
            max_chunks=2,
        )
    )

    assert response.filename == "paper.pdf"
    assert response.summary_type == "technical"
    assert response.chunks_used == 2
    assert response.context_available is True
    assert response.citations[0].citation_id == "C1"
    assert response.citations[0].page == 1
    assert llm_service.calls[0]["summary_type"] == "technical"


def test_summarization_falls_back_to_default_language():
    service = SummarizationService(
        settings=make_settings(),
        document_service=FakeDocumentService(),
        chunking_service=FakeChunkingService(make_chunks(1)),
        llm_service=FakeLLMService(),
        translation_service=FakeTranslationService(),
        language_registry=FakeLanguageRegistry(),
    )

    response = service.summarize(
        SummaryRequest(
            document_id="doc-1",
            target_language="unsupported",
        )
    )

    assert response.target_language == "en"


def test_summarization_translates_fallback_summary():
    service = SummarizationService(
        settings=make_settings(llm_provider="fallback"),
        document_service=FakeDocumentService(),
        chunking_service=FakeChunkingService(make_chunks(1)),
        llm_service=FakeLLMService(),
        translation_service=FakeTranslationService(),
        language_registry=FakeLanguageRegistry(),
    )

    response = service.summarize(
        SummaryRequest(
            document_id="doc-1",
            target_language="hi",
        )
    )

    assert response.translation_applied is True
    assert response.summary.startswith("hi:")
