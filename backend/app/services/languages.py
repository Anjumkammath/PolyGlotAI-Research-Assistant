from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from backend.app.core.config import get_settings
from backend.app.models.schemas import Language


class LanguageRegistry:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or get_settings().language_config_path
        self._languages = self._load_languages()

    @property
    def languages(self) -> list[Language]:
        return [language for language in self._languages if language.enabled]

    def codes(self) -> set[str]:
        return {language.code for language in self.languages}

    def get(self, code: str) -> Language | None:
        for language in self.languages:
            if language.code == code:
                return language
        return None

    def name(self, code: str) -> str:
        language = self.get(code)
        return language.name if language else code

    def is_supported(self, code: str) -> bool:
        return code in self.codes()

    def detect_language(self, text: str) -> str:
        scores = _script_scores(text)
        if not scores:
            return "en" if self.is_supported("en") else next(iter(self.codes()), "und")

        code = max(scores, key=scores.get)
        if code == "zh-CN" and scores.get("ja", 0) > 0:
            code = "ja"
        if self.is_supported(code):
            return code
        return "en" if self.is_supported("en") else code

    def tokenizer_strategy_for(self, code: str) -> str:
        language = self.get(code)
        if language is None:
            return "character"
        return language.tokenizer_strategy

    def resolve_text(self, text: str) -> tuple[str, str]:
        code = self.detect_language(text)
        return code, self.tokenizer_strategy_for(code)

    def _load_languages(self) -> list[Language]:
        if not self.config_path.exists():
            return _fallback_languages()

        raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return _fallback_languages()
        return [Language(**item) for item in raw]


def get_language_registry() -> LanguageRegistry:
    return LanguageRegistry()


def language_codes() -> set[str]:
    return get_language_registry().codes()


def language_name(code: str) -> str:
    return get_language_registry().name(code)


def is_supported_language(code: str) -> bool:
    return get_language_registry().is_supported(code)


def detect_language_code(text: str) -> str:
    return get_language_registry().detect_language(text)


SUPPORTED_LANGUAGES = get_language_registry().languages


def _script_scores(text: str) -> dict[str, int]:
    scores: dict[str, int] = {}
    for char in text:
        language_code = _language_for_codepoint(ord(char))
        if language_code is not None:
            scores[language_code] = scores.get(language_code, 0) + 1
    return scores


def _language_for_codepoint(codepoint: int) -> str | None:
    ranges: Iterable[tuple[int, int, str]] = (
        (0x0041, 0x007A, "en"),
        (0x00C0, 0x024F, "en"),
        (0x0900, 0x097F, "hi"),
        (0x0980, 0x09FF, "bn"),
        (0x0A00, 0x0A7F, "pa"),
        (0x0A80, 0x0AFF, "gu"),
        (0x0B00, 0x0B7F, "or"),
        (0x0B80, 0x0BFF, "ta"),
        (0x0C00, 0x0C7F, "te"),
        (0x0C80, 0x0CFF, "kn"),
        (0x0D00, 0x0D7F, "ml"),
        (0x3040, 0x309F, "ja"),
        (0x30A0, 0x30FF, "ja"),
        (0x31F0, 0x31FF, "ja"),
        (0x4E00, 0x9FFF, "zh-CN"),
        (0xAC00, 0xD7AF, "ko"),
        (0x0E00, 0x0E7F, "th"),
        (0x0600, 0x06FF, "ar"),
        (0x0400, 0x04FF, "ru"),
    )
    for start, end, language_code in ranges:
        if start <= codepoint <= end:
            return language_code
    return None


def _fallback_languages() -> list[Language]:
    return [
        Language(code="en", name="English", family="global"),
        Language(code="ml", name="Malayalam", family="indian", tokenizer_strategy="indic"),
        Language(code="hi", name="Hindi", family="indian", tokenizer_strategy="indic"),
        Language(code="ja", name="Japanese", family="east_asian", tokenizer_strategy="sudachipy"),
    ]
