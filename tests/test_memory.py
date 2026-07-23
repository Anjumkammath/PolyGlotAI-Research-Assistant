from backend.app.services.memory import MemoryStore


def test_memory_store_returns_session_messages_with_metadata(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")

    store.add_message(
        session_id="session-1",
        role="user",
        content="Explain the paper",
        language="hi",
        document_id="doc-1",
        metadata={"top_k": 5},
    )
    store.add_message(
        session_id="session-1",
        role="assistant",
        content="The paper studies multilingual retrieval.",
        language="hi",
        document_id="doc-1",
        metadata={"retrieved_chunks": 2},
    )

    messages = store.session_messages("session-1")

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["document_id"] == "doc-1"
    assert messages[0]["metadata"] == {"top_k": 5}
    assert messages[1]["metadata"] == {"retrieved_chunks": 2}
    assert messages[0]["created_at"].endswith("+00:00")


def test_memory_store_recent_messages_are_chronological(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")

    for index in range(4):
        store.add_message(
            session_id="session-1",
            role="user",
            content=f"message {index}",
            language="en",
            document_id=f"doc-{index}",
        )

    messages = store.recent_messages("session-1", limit=2)

    assert [message["content"] for message in messages] == ["message 2", "message 3"]
    assert messages[-1]["document_id"] == "doc-3"


def test_memory_store_lists_sessions_with_latest_language_and_document(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")

    store.add_message("session-1", "user", "hello", language="en", document_id="doc-1")
    store.add_message("session-1", "assistant", "hi", language="ja", document_id="doc-2")
    store.add_message("session-2", "user", "namaste", language="hi", document_id=None)

    sessions = store.list_sessions(limit=10)
    session_by_id = {session["session_id"]: session for session in sessions}

    assert session_by_id["session-1"]["message_count"] == 2
    assert session_by_id["session-1"]["preferred_language"] == "ja"
    assert session_by_id["session-1"]["last_document_id"] == "doc-2"
    assert session_by_id["session-2"]["preferred_language"] == "hi"
    assert session_by_id["session-2"]["last_document_id"] is None


def test_memory_store_deletes_single_session_and_can_clear_all(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")

    store.add_message("session-1", "user", "one")
    store.add_message("session-1", "assistant", "two")
    store.add_message("session-2", "user", "three")

    deleted = store.delete_session("session-1")

    assert deleted == 2
    assert store.session_messages("session-1") == []
    assert len(store.session_messages("session-2")) == 1
    assert store.clear_all() == 1
    assert store.list_sessions() == []
