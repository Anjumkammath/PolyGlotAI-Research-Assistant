from types import SimpleNamespace

from backend.app.models.schemas import ChatRequest
from backend.app.services.chunker import TextChunk
from backend.app.services.rag import RAGService
from backend.app.services.vector_store import VectorSearchHit


class FakeLanguageRegistry:
    def is_supported(self, code):
        return code in {"en", "hi", "ja"}


class FakeVectorStore:
    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def query(self, question, top_k, document_id=None):
        self.calls.append(
            {
                "question": question,
                "top_k": top_k,
                "document_id": document_id,
            }
        )
        return self.hits[:top_k]


class FailingVectorStore:
    def query(self, question, top_k, document_id=None):
        raise RuntimeError("Vector database unavailable")


class FakeLLMService:
    def __init__(self):
        self.calls = []

    def answer(self, question, context_hits, memory_messages, target_language, answer_style="auto"):
        self.calls.append(
            {
                "question": question,
                "context_hits": context_hits,
                "memory_messages": memory_messages,
                "target_language": target_language,
                "answer_style": answer_style,
            }
        )
        if not context_hits:
            return "No context found."
        return "The paper discusses multilingual retrieval [C1]."


class NoCitationLLMService(FakeLLMService):
    def answer(self, question, context_hits, memory_messages, target_language, answer_style="auto"):
        self.calls.append(
            {
                "question": question,
                "context_hits": context_hits,
                "memory_messages": memory_messages,
                "target_language": target_language,
                "answer_style": answer_style,
            }
        )
        return "The paper discusses multilingual retrieval."


class FakeTranslationService:
    def translate(self, text, source_language, target_language):
        return f"{target_language}: {text}"


class FakeMemoryStore:
    def __init__(self):
        self.messages = []

    def add_message(
        self,
        session_id,
        role,
        content,
        language=None,
        document_id=None,
        metadata=None,
    ):
        self.messages.append(
            {
                "session_id": session_id,
                "role": role,
                "content": content,
                "language": language,
                "document_id": document_id,
                "metadata": metadata or {},
            }
        )

    def recent_messages(self, session_id):
        return [
            {
                "role": message["role"],
                "content": message["content"],
                "language": message["language"] or "",
                "document_id": message["document_id"] or "",
            }
            for message in self.messages
            if message["session_id"] == session_id
        ]


class FakeDocumentService:
    def get_document(self, document_id):
        return SimpleNamespace(document_id=document_id, filename="paper.pdf", indexed=True)

    def list_documents(self):
        return [self.get_document("doc-1")]


class FakeChunkingService:
    def load_chunks(self, document_id):
        return (
            [
                TextChunk(
                    text="This paper explains multilingual retrieval and citation grounded answers.",
                    page=2,
                    chunk_index=0,
                    language="en",
                    tokenizer_strategy="whitespace",
                )
            ],
            900,
            180,
        )


def make_settings(llm_provider="openai"):
    return SimpleNamespace(
        max_context_chunks=5,
        default_answer_language="en",
        llm_provider=llm_provider,
    )


def test_rag_answer_returns_citations_and_uses_document_filter():
    hit = VectorSearchHit(
        chunk_id="doc-1:0",
        document_id="doc-1",
        source_name="paper.pdf",
        page=4,
        page_start=4,
        page_end=4,
        text="The paper discusses multilingual retrieval for research documents.",
        score=0.93,
        language="en",
        tokenizer_strategy="whitespace",
    )
    vector_store = FakeVectorStore([hit])
    llm_service = FakeLLMService()
    memory_store = FakeMemoryStore()
    service = RAGService(
        settings=make_settings(),
        vector_store=vector_store,
        llm_service=llm_service,
        translation_service=FakeTranslationService(),
        memory_store=memory_store,
        language_registry=FakeLanguageRegistry(),
    )

    response = service.answer(
        ChatRequest(
            question=" What does the paper discuss? ",
            session_id="session-1",
            document_id="doc-1",
            target_language="en",
            top_k=3,
        )
    )

    assert vector_store.calls[0]["question"] == "What does the paper discuss?"
    assert vector_store.calls[0]["document_id"] == "doc-1"
    assert response.context_available is True
    assert response.retrieved_chunks == 1
    assert response.cited_chunks == 1
    assert response.retrieval_mode == "vector"
    assert response.grounding_verified is True
    assert response.citation_confidence == "high"
    assert response.answer_style == "auto"
    assert response.document_type == "document"
    assert response.citations[0].citation_id == "C1"
    assert response.citations[0].score == 0.93
    assert response.citations[0].language == "en"
    assert memory_store.messages[-1]["role"] == "assistant"


def test_rag_answer_passes_answer_style_to_llm():
    hit = VectorSearchHit(
        chunk_id="doc-1:0",
        document_id="doc-1",
        source_name="paper.pdf",
        page=4,
        page_start=4,
        page_end=4,
        text="The paper discusses multilingual retrieval for research documents.",
        score=0.93,
        language="en",
        tokenizer_strategy="whitespace",
    )
    vector_store = FakeVectorStore([hit])
    llm_service = FakeLLMService()
    service = RAGService(
        settings=make_settings(),
        vector_store=vector_store,
        llm_service=llm_service,
        translation_service=FakeTranslationService(),
        memory_store=FakeMemoryStore(),
        language_registry=FakeLanguageRegistry(),
    )

    response = service.answer(
        ChatRequest(
            question="Explain this in detail",
            session_id="session-1",
            document_id="doc-1",
            target_language="en",
            answer_style="detailed",
        )
    )

    assert response.answer_style == "detailed"
    assert llm_service.calls[0]["answer_style"] == "detailed"


def test_rag_answer_returns_only_referenced_citations():
    hits = [
        VectorSearchHit(
            chunk_id="doc-1:0",
            document_id="doc-1",
            source_name="paper.pdf",
            page=1,
            page_start=1,
            page_end=1,
            text="The first retrieved passage supports the answer.",
            score=0.93,
            language="en",
            tokenizer_strategy="whitespace",
        ),
        VectorSearchHit(
            chunk_id="doc-1:1",
            document_id="doc-1",
            source_name="paper.pdf",
            page=2,
            page_start=2,
            page_end=2,
            text="The second passage was retrieved but not cited.",
            score=0.72,
            language="en",
            tokenizer_strategy="whitespace",
        ),
    ]
    service = RAGService(
        settings=make_settings(),
        vector_store=FakeVectorStore(hits),
        llm_service=FakeLLMService(),
        translation_service=FakeTranslationService(),
        memory_store=FakeMemoryStore(),
        language_registry=FakeLanguageRegistry(),
    )

    response = service.answer(
        ChatRequest(
            question="What does the paper discuss?",
            session_id="session-1",
            document_id="doc-1",
            target_language="en",
            top_k=2,
        )
    )

    assert response.retrieved_chunks == 2
    assert response.cited_chunks == 1
    assert [citation.citation_id for citation in response.citations] == ["C1"]
    assert [context.citation_id for context in response.retrieved_context] == ["C1", "C2"]


def test_rag_answer_does_not_convert_uncited_context_into_citations():
    hits = [
        VectorSearchHit(
            chunk_id="doc-1:0",
            document_id="doc-1",
            source_name="paper.pdf",
            page=1,
            page_start=1,
            page_end=1,
            text="The first retrieved passage is relevant context.",
            score=0.93,
            language="en",
            tokenizer_strategy="whitespace",
        ),
        VectorSearchHit(
            chunk_id="doc-1:1",
            document_id="doc-1",
            source_name="paper.pdf",
            page=2,
            page_start=2,
            page_end=2,
            text="The second passage is also retrieved context.",
            score=0.72,
            language="en",
            tokenizer_strategy="whitespace",
        ),
    ]
    service = RAGService(
        settings=make_settings(),
        vector_store=FakeVectorStore(hits),
        llm_service=NoCitationLLMService(),
        translation_service=FakeTranslationService(),
        memory_store=FakeMemoryStore(),
        language_registry=FakeLanguageRegistry(),
    )

    response = service.answer(
        ChatRequest(
            question="What does the paper discuss?",
            session_id="session-1",
            document_id="doc-1",
            target_language="en",
            top_k=2,
        )
    )

    assert response.retrieved_chunks == 2
    assert response.cited_chunks == 0
    assert response.citations == []
    assert len(response.retrieved_context) == 2
    assert response.grounding_verified is False
    assert response.citation_confidence == "none"
    assert "did not include valid inline citation" in response.citation_warning


def test_rag_answer_handles_no_context():
    vector_store = FakeVectorStore([])
    service = RAGService(
        settings=make_settings(),
        vector_store=vector_store,
        llm_service=FakeLLMService(),
        translation_service=FakeTranslationService(),
        memory_store=FakeMemoryStore(),
        language_registry=FakeLanguageRegistry(),
    )

    response = service.answer(
        ChatRequest(
            question="Unknown question",
            session_id="session-1",
            target_language="en",
        )
    )

    assert response.context_available is False
    assert response.retrieved_chunks == 0
    assert response.citations == []
    assert "No context" in response.answer


def test_rag_answer_falls_back_to_default_language():
    vector_store = FakeVectorStore([])
    service = RAGService(
        settings=make_settings(),
        vector_store=vector_store,
        llm_service=FakeLLMService(),
        translation_service=FakeTranslationService(),
        memory_store=FakeMemoryStore(),
        language_registry=FakeLanguageRegistry(),
    )

    response = service.answer(
        ChatRequest(
            question="Hello",
            session_id="session-1",
            target_language="unsupported",
        )
    )

    assert response.target_language == "en"


def test_rag_answer_uses_local_chunks_when_vector_search_fails():
    service = RAGService(
        settings=make_settings(),
        vector_store=FailingVectorStore(),
        llm_service=FakeLLMService(),
        translation_service=FakeTranslationService(),
        memory_store=FakeMemoryStore(),
        language_registry=FakeLanguageRegistry(),
        document_service=FakeDocumentService(),
        chunking_service=FakeChunkingService(),
    )

    response = service.answer(
        ChatRequest(
            question="How is multilingual retrieval handled?",
            session_id="session-1",
            document_id="doc-1",
            target_language="en",
        )
    )

    assert response.context_available is True
    assert response.retrieved_chunks == 1
    assert response.cited_chunks == 1
    assert response.retrieval_mode == "lexical_fallback"
    assert "fallback" in response.retrieval_warning
    assert response.citations[0].source_name == "paper.pdf"
    assert response.citations[0].page == 2


def test_rag_answer_uses_local_overview_chunks_for_document_about_question():
    irrelevant_hit = VectorSearchHit(
        chunk_id="doc-1:9",
        document_id="doc-1",
        source_name="paper.pdf",
        page=9,
        page_start=9,
        page_end=9,
        text="A later unrelated sentence that should not drive the overview.",
        score=0.99,
        language="en",
        tokenizer_strategy="whitespace",
    )
    vector_store = FakeVectorStore([irrelevant_hit])
    llm_service = FakeLLMService()
    service = RAGService(
        settings=make_settings(),
        vector_store=vector_store,
        llm_service=llm_service,
        translation_service=FakeTranslationService(),
        memory_store=FakeMemoryStore(),
        language_registry=FakeLanguageRegistry(),
        document_service=FakeDocumentService(),
        chunking_service=FakeChunkingService(),
    )

    response = service.answer(
        ChatRequest(
            question="What is the paper about and what does it explain?",
            session_id="session-1",
            document_id="doc-1",
            target_language="en",
        )
    )

    assert vector_store.calls == []
    assert response.retrieval_mode == "overview_bypass"
    assert "not vector similarity retrieval" in response.retrieval_warning
    assert response.citations[0].excerpt == "This paper explains multilingual retrieval and citation grounded answers."
    assert llm_service.calls[0]["context_hits"][0].text.startswith("This paper explains")
