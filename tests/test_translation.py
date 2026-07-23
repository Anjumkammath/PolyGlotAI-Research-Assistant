from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from backend.app.services.languages import LanguageRegistry
from backend.app.services.translator import (
    TranslationMethodUnavailableError,
    TranslationService,
)


class FakeLLMService:
    def translate_text(self, text, source_language, target_language):
        return f"llm:{source_language}->{target_language}:{text}"


def make_settings():
    return SimpleNamespace(
        translation_methods_config_path=Path("config/translation_methods.json"),
        translation_language_codes_path=Path("config/translation_language_codes.json"),
        default_translation_method="google",
        nllb_model_name="facebook/nllb-200-distilled-600M",
    )


def test_translation_methods_load_from_config():
    service = TranslationService(
        settings=make_settings(),
        language_registry=LanguageRegistry(Path("config/languages.json")),
        llm_service=FakeLLMService(),
    )

    method_ids = {method.id for method in service.methods}

    assert {"google", "llm", "nllb"}.issubset(method_ids)


def test_google_translation_returns_metadata(monkeypatch):
    service = TranslationService(
        settings=make_settings(),
        language_registry=LanguageRegistry(Path("config/languages.json")),
        llm_service=FakeLLMService(),
    )
    monkeypatch.setattr(
        service,
        "_translate_with_google",
        lambda text, source_language, target_language: f"google:{target_language}:{text}",
    )

    response = service.translate_with_metadata(
        text="hello",
        source_language="en",
        target_language="ja",
        method="google",
    )

    assert response.method == "google"
    assert response.provider == "deep-translator"
    assert response.translated_text == "google:ja:hello"
    assert response.source_language == "en"


def test_llm_translation_uses_configured_llm_service():
    service = TranslationService(
        settings=make_settings(),
        language_registry=LanguageRegistry(Path("config/languages.json")),
        llm_service=FakeLLMService(),
    )

    response = service.translate_with_metadata(
        text="Transformer models use attention.",
        source_language="en",
        target_language="hi",
        method="llm",
    )

    assert response.method == "llm"
    assert response.translated_text.startswith("llm:en->hi")


def test_llm_translation_requires_llm_service():
    service = TranslationService(
        settings=make_settings(),
        language_registry=LanguageRegistry(Path("config/languages.json")),
        llm_service=None,
    )

    with pytest.raises(TranslationMethodUnavailableError):
        service.translate_with_metadata(
            text="hello",
            source_language="en",
            target_language="hi",
            method="llm",
        )


def test_translation_language_config_contains_current_language_set():
    registry = LanguageRegistry(Path("config/languages.json"))
    expected_codes = {
        "en",
        "ml",
        "hi",
        "ja",
        "ta",
        "te",
        "kn",
        "bn",
        "mr",
        "gu",
        "pa",
        "ur",
        "or",
        "as",
        "ko",
        "zh-CN",
        "id",
        "th",
        "vi",
        "ar",
        "es",
        "fr",
        "de",
        "pt",
        "ru",
        "it",
        "tr",
        "fa",
    }

    assert expected_codes == registry.codes()


def test_translation_language_codes_cover_supported_languages():
    registry = LanguageRegistry(Path("config/languages.json"))
    language_codes = json.loads(
        Path("config/translation_language_codes.json").read_text(encoding="utf-8")
    )

    assert registry.codes() == set(language_codes)
    for code in registry.codes():
        assert language_codes[code]["google"]
        assert language_codes[code]["nllb"]
