from backend.app.services.text_cleanup import clean_pdf_text
from backend.app.services.llm import _best_source_sentence


def test_clean_pdf_text_repairs_compacted_sql_notes():
    text = (
        "SQL(NotesbyApnaCollege) What isDatabase?"
        "Databaseisacollectionofinterrelateddata."
    )

    cleaned = clean_pdf_text(text)

    assert "what is database?" in cleaned.lower()
    assert "Database is a collection of interrelated data." in cleaned


def test_clean_pdf_text_repairs_compacted_sql_note_and_datatype_sentence():
    note = "*Note-SQLkeywordsareNOTcasesensitive.Eg:selectisthesameasSELECTinSQL."
    datatype = (
        "SQLDataTypesInSQL,"
        "datatypesdefinethekindofdatathatcanbestoredinacolumnorvariable."
    )

    cleaned_note = clean_pdf_text(note)
    cleaned_datatype = clean_pdf_text(datatype)

    assert "sql keywords are not case sensitive." in cleaned_note.lower()
    assert "select is the same as select in sql." in cleaned_note.lower()
    assert "sql data types in sql" in cleaned_datatype.lower()
    assert "datatypes define the kind of data that can be stored in a column or variable." in cleaned_datatype


def test_clean_pdf_text_repairs_short_acronym_and_common_compacted_terms():
    assert clean_pdf_text("What isDBMS?") == "What is DBMS?"
    assert clean_pdf_text("Toreaddatapresentinthedatabase.") == "To read data present in the database."
    assert (
        clean_pdf_text("responsiblefordefiningandmanagingthestructureofdatabasesandtheirobjects")
        == "responsible for defining and managing the structure of databases and their objects"
    )
    assert clean_pdf_text("DataDefinitionLanguage") == "Data Definition Language"


def test_best_source_sentence_prefers_definition_over_question_heading():
    text = "SQL(NotesbyApnaCollege) What isDatabase?Databaseisacollectionofinterrelateddata."

    sentence = _best_source_sentence(text, "What is database?", limit=200)

    assert sentence == "Database is a collection of interrelated data."


def test_clean_pdf_text_preserves_common_ai_tool_names():
    text = "LangChain TensorFlow PyTorch NumPy GitHub LabelGuard OpenAI OpenCV FastAPI"

    cleaned = clean_pdf_text(text)

    assert cleaned == text
