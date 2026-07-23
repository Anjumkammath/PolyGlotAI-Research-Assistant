from types import ModuleType, SimpleNamespace

from backend.app.services.chunker import (
    TokenizerUnavailableError,
    chunk_pages,
    tokenize_for_chunking,
)
from backend.app.services.pdf_loader import PageText


JAPANESE_TEXT = (
    "\u3053\u308c\u306f\u7814\u7a76\u8ad6\u6587\u3067\u3059\u3002"
    "\u624b\u6cd5\u3092\u8aac\u660e\u3057\u307e\u3059\u3002"
    "\u7d50\u679c\u3068\u9650\u754c\u3082\u8ff0\u3079\u307e\u3059\u3002"
)


def test_chunk_pages_keeps_page_number():
    pages = [PageText(page_number=3, text="alpha beta gamma " * 80)]

    chunks = chunk_pages(pages, chunk_size=80, chunk_overlap=20)

    assert chunks
    assert {chunk.page for chunk in chunks} == {3}


def test_chunk_overlap_must_be_smaller_than_size():
    pages = [PageText(page_number=1, text="hello")]

    try:
        chunk_pages(pages, chunk_size=10, chunk_overlap=10)
    except ValueError as exc:
        assert "chunk_overlap" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_chunk_pages_uses_language_resolver_metadata(monkeypatch):
    _install_fake_sudachipy(monkeypatch)
    pages = [PageText(page_number=1, text=JAPANESE_TEXT * 20)]

    chunks = chunk_pages(
        pages,
        chunk_size=40,
        chunk_overlap=5,
        language_resolver=lambda text: ("ja", "sudachipy"),
    )

    assert chunks
    assert chunks[0].language == "ja"
    assert chunks[0].tokenizer_strategy == "sudachipy"
    assert all(chunk.character_count <= 45 for chunk in chunks)
    assert "\u7814\u7a76\u8ad6\u6587" in "".join(chunk.text for chunk in chunks[:2])


def test_sudachipy_strategy_raises_clear_error_when_missing(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.chunker._missing_modules",
        lambda modules: ["sudachipy", "sudachidict_core"],
    )

    try:
        tokenize_for_chunking(JAPANESE_TEXT, "sudachipy")
    except TokenizerUnavailableError as exc:
        assert "sudachipy" in str(exc)
        assert "requirements-backend.txt" in str(exc)
    else:
        raise AssertionError("Expected TokenizerUnavailableError")


def test_sudachipy_strategy_segments_real_japanese_text(monkeypatch):
    _install_fake_sudachipy(monkeypatch)

    tokens = tokenize_for_chunking(JAPANESE_TEXT, "sudachipy")

    assert tokens[:4] == [
        "\u3053\u308c",
        "\u306f",
        "\u7814\u7a76\u8ad6\u6587",
        "\u3067\u3059",
    ]
    assert "\u624b\u6cd5" in tokens
    assert "\u9650\u754c" in tokens


def _install_fake_sudachipy(monkeypatch):
    class FakeMorpheme:
        def __init__(self, surface: str) -> None:
            self._surface = surface

        def surface(self) -> str:
            return self._surface

    class FakeSudachiTokenizer:
        def tokenize(self, text: str, mode):
            tokens = [
                "\u3053\u308c",
                "\u306f",
                "\u7814\u7a76\u8ad6\u6587",
                "\u3067\u3059",
                "\u3002",
                "\u624b\u6cd5",
                "\u3092",
                "\u8aac\u660e",
                "\u3057\u307e\u3059",
                "\u3002",
                "\u7d50\u679c",
                "\u3068",
                "\u9650\u754c",
                "\u3082",
                "\u8ff0\u3079\u307e\u3059",
                "\u3002",
            ]
            repeated = (tokens * ((len(text) // max(len(JAPANESE_TEXT), 1)) + 1))[: max(len(tokens), 1)]
            return [FakeMorpheme(token) for token in repeated]

    class FakeDictionary:
        def create(self):
            return FakeSudachiTokenizer()

    sudachipy = ModuleType("sudachipy")
    sudachipy.dictionary = SimpleNamespace(Dictionary=FakeDictionary)
    sudachipy.tokenizer = SimpleNamespace(
        Tokenizer=SimpleNamespace(SplitMode=SimpleNamespace(C="C"))
    )

    monkeypatch.setitem(__import__("sys").modules, "sudachipy", sudachipy)
    monkeypatch.setitem(__import__("sys").modules, "sudachidict_core", ModuleType("sudachidict_core"))
    monkeypatch.setattr("backend.app.services.chunker._missing_modules", lambda modules: [])
