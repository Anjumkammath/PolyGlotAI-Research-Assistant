from dataclasses import dataclass
import importlib.util
import re
from typing import Callable

from backend.app.services.pdf_loader import PageText


@dataclass(frozen=True)
class TextChunk:
    text: str
    page: int
    chunk_index: int
    language: str = "und"
    tokenizer_strategy: str = "character"

    @property
    def page_start(self) -> int:
        return self.page

    @property
    def page_end(self) -> int:
        return self.page

    @property
    def character_count(self) -> int:
        return len(self.text)


LanguageResolver = Callable[[str], tuple[str, str]]


class TokenizerUnavailableError(RuntimeError):
    pass


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_pages(
    pages: list[PageText],
    chunk_size: int,
    chunk_overlap: int,
    language_resolver: LanguageResolver | None = None,
) -> list[TextChunk]:
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[TextChunk] = []
    global_index = 0

    for page in pages:
        text = normalize_text(page.text)
        if not text:
            continue

        language, tokenizer_strategy = _resolve_page_language(
            text=text,
            language_resolver=language_resolver,
        )

        for chunk_body in chunk_text(
            text=text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            tokenizer_strategy=tokenizer_strategy,
        ):
            chunks.append(
                TextChunk(
                    text=chunk_body,
                    page=page.page_number,
                    chunk_index=global_index,
                    language=language,
                    tokenizer_strategy=tokenizer_strategy,
                )
            )
            global_index += 1

    return chunks


def chunk_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    tokenizer_strategy: str,
) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    units = [
        expanded_unit
        for unit in tokenize_for_chunking(normalized, tokenizer_strategy)
        for expanded_unit in _split_oversized_unit(unit, chunk_size)
    ]
    if not units:
        return []

    chunks: list[str] = []
    current_units: list[str] = []
    current_length = 0

    for unit in units:
        unit_length = len(unit)
        projected_length = current_length + unit_length + (1 if current_units else 0)
        if current_units and projected_length > chunk_size:
            chunks.append(_join_units(current_units, tokenizer_strategy))
            current_units = _overlap_units(
                current_units=current_units,
                overlap_characters=chunk_overlap,
            )
            current_length = sum(len(item) for item in current_units)

        current_units.append(unit)
        current_length += unit_length

    if current_units:
        chunk = _join_units(current_units, tokenizer_strategy)
        if not chunks or chunk != chunks[-1]:
            chunks.append(chunk)

    return chunks


def tokenize_for_chunking(text: str, tokenizer_strategy: str) -> list[str]:
    strategy = tokenizer_strategy.lower().strip()
    if strategy == "sudachipy":
        return _sudachipy_units(text)
    if strategy == "fugashi":
        return _fugashi_units(text)
    if strategy in {"cjk", "character"}:
        return _character_units(text)
    if strategy in {"indic", "whitespace"}:
        return _word_units(text)
    return _word_units(text)


def tokenizer_setup_issues(enabled_strategies: set[str]) -> list[str]:
    issues: list[str] = []
    strategies = {strategy.lower().strip() for strategy in enabled_strategies}
    if "sudachipy" in strategies:
        missing = _missing_modules(["sudachipy", "sudachidict_core"])
        if missing:
            issues.append(
                "Japanese tokenizer strategy 'sudachipy' is enabled, but missing "
                f"packages: {', '.join(missing)}."
            )
    if "fugashi" in strategies:
        missing = _missing_modules(["fugashi", "unidic_lite"])
        if missing:
            issues.append(
                "Japanese tokenizer strategy 'fugashi' is enabled, but missing "
                f"packages: {', '.join(missing)}."
            )
    return issues


def _resolve_page_language(
    text: str,
    language_resolver: LanguageResolver | None,
) -> tuple[str, str]:
    if language_resolver is None:
        return "und", "character"
    language, tokenizer_strategy = language_resolver(text)
    return language or "und", tokenizer_strategy or "character"


def _word_units(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def _character_units(text: str) -> list[str]:
    return [char for char in text if not char.isspace()]


def _sudachipy_units(text: str) -> list[str]:
    missing = _missing_modules(["sudachipy", "sudachidict_core"])
    if missing:
        raise TokenizerUnavailableError(
            "Japanese tokenizer strategy 'sudachipy' is configured, but these "
            f"Python packages are missing: {', '.join(missing)}. Install backend "
            "dependencies again with requirements-backend.txt."
        )

    from sudachipy import dictionary, tokenizer

    sudachi = dictionary.Dictionary().create()
    mode = tokenizer.Tokenizer.SplitMode.C
    return [morpheme.surface() for morpheme in sudachi.tokenize(text, mode)]


def _fugashi_units(text: str) -> list[str]:
    missing = _missing_modules(["fugashi", "unidic_lite"])
    if missing:
        raise TokenizerUnavailableError(
            "Japanese tokenizer strategy 'fugashi' is configured, but these "
            f"Python packages are missing: {', '.join(missing)}. Install backend "
            "dependencies again with requirements-backend.txt."
        )

    from fugashi import Tagger

    tagger = Tagger()
    return [word.surface for word in tagger(text)]


def _japanese_fallback_units(text: str) -> list[str]:
    units = re.findall(
        r"[\u3040-\u309F\u30A0-\u30FF\u31F0-\u31FF\u4E00-\u9FFF\u3005\u30FC]+|[A-Za-z0-9]+|[^\s]",
        text,
    )
    return units or _character_units(text)


def _missing_modules(module_names: list[str]) -> list[str]:
    return [
        module_name
        for module_name in module_names
        if importlib.util.find_spec(module_name) is None
    ]


def _overlap_units(
    current_units: list[str],
    overlap_characters: int,
) -> list[str]:
    if overlap_characters <= 0:
        return []

    overlap: list[str] = []
    total = 0
    for unit in reversed(current_units):
        overlap.insert(0, unit)
        total += len(unit)
        if total >= overlap_characters:
            break
    return overlap


def _split_oversized_unit(unit: str, max_size: int) -> list[str]:
    if len(unit) <= max_size:
        return [unit]
    return [
        unit[start : start + max_size]
        for start in range(0, len(unit), max_size)
    ]


def _join_units(units: list[str], tokenizer_strategy: str) -> str:
    strategy = tokenizer_strategy.lower().strip()
    if strategy in {"cjk", "character", "sudachipy", "fugashi"}:
        return "".join(units).strip()
    return " ".join(units).strip()
