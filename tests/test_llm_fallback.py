from types import SimpleNamespace

from backend.app.services.llm import LLMService
from backend.app.services.vector_store import VectorSearchHit


def _hit(text: str, index: int = 0) -> VectorSearchHit:
    return VectorSearchHit(
        chunk_id=f"doc-1:{index}",
        document_id="doc-1",
        source_name="Anti_CV.pdf",
        page=1,
        page_start=1,
        page_end=1,
        text=text,
        score=1.0,
        language="en",
        tokenizer_strategy="whitespace",
    )


def test_fallback_answer_explains_resume_overview_questions():
    service = LLMService(SimpleNamespace(llm_provider="fallback"))
    hits = [
        _hit(
            "Anju M Kammath anju@example.com Professional Summary Entry-level AI "
            "and Data Science professional with experience in ML data operations, "
            "NLP dataset validation, error analysis, and applied AI projects. "
            "Technical Skills Python SQL machine learning NLP FastAPI LangChain. "
            "Work Experience ML Data Associate at Amazon Alexa Data Services.",
            index=0,
        ),
        _hit(
            "Projects AI Resume Builder and ATS Analyzer. Solar Nova AI - Computer "
            "Vision and IoT. Education B.Tech in Artificial Intelligence and Data Science.",
            index=1,
        ),
    ]

    answer = service.answer(
        question="what is the paper about what does it explain",
        context_hits=hits,
        memory_messages=[],
        target_language="en",
    )

    assert "resume/CV" in answer
    assert "AI and Data Science" in answer
    assert "Skills highlighted" in answer
    assert "Projects" in answer
    assert "Strengthened production NLP" not in answer


def test_fallback_answer_keeps_definition_questions_concise():
    service = LLMService(SimpleNamespace(llm_provider="fallback"))
    hits = [
        _hit(
            "SQL(NotesbyApnaCollege) What isDatabase?"
            "Databaseisacollectionofinterrelateddata.",
            index=0,
        ),
        _hit("SQLDataTypesInSQL,datatypesdefinethekindofdatathatcanbestoredinacolumnorvariable.", index=1),
    ]

    answer = service.answer(
        question="What is database?",
        context_hits=hits,
        memory_messages=[],
        target_language="en",
    )

    assert "Database is a collection of interrelated data. [C1]" in answer
    assert "[C2]" not in answer


def test_fallback_beginner_definition_questions_stay_focused():
    service = LLMService(SimpleNamespace(llm_provider="fallback"))
    hits = [
        _hit(
            "SQL(NotesbyApnaCollege) What isDatabase?"
            "Databaseisacollectionofinterrelateddata.",
            index=0,
        ),
        _hit(
            "DataDefinitionLanguage (DDL) is responsiblefordefiningandmanagingthestructureofdatabasesandtheirobjects.",
            index=1,
        ),
    ]

    answer = service.answer(
        question="What is database?",
        context_hits=hits,
        memory_messages=[],
        target_language="en",
        answer_style="beginner",
    )

    assert "Database is a collection of interrelated data. [C1]" in answer
    assert "[C2]" not in answer


def test_fallback_answer_supports_detailed_answer_style():
    service = LLMService(SimpleNamespace(llm_provider="fallback"))
    hits = [
        _hit(
            "The paper discusses multilingual retrieval for research documents and uses citations to ground answers.",
            index=0,
        ),
        _hit(
            "The assistant retrieves relevant chunks before generating an answer for the user.",
            index=1,
        ),
    ]

    answer = service.answer(
        question="What does the assistant explain?",
        context_hits=hits,
        memory_messages=[],
        target_language="en",
        answer_style="detailed",
    )

    assert answer.startswith("Detailed answer:")
    assert "[C1]" in answer
    assert "[C2]" in answer
