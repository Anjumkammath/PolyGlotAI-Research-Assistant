from __future__ import annotations

import json
from pathlib import Path

from backend.app.core.config import Settings, get_settings
from backend.app.models.schemas import (
    TranslateResponse,
    TranslationCompareResponse,
    TranslationMethod,
    TranslationMethodInfo,
)
from backend.app.services.languages import LanguageRegistry, get_language_registry
from backend.app.services.llm import LLMService


class TranslationServiceError(Exception):
    status_code = 400


class TranslationMethodUnavailableError(TranslationServiceError):
    status_code = 501


class TranslationService:
    def __init__(
        self,
        settings: Settings | None = None,
        language_registry: LanguageRegistry | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.language_registry = language_registry or get_language_registry()
        self.llm_service = llm_service
        self._methods = self._load_methods()
        self._language_codes = self._load_language_codes()
        self._nllb_tokenizer = None
        self._nllb_model = None

    @property
    def provider_name(self) -> str:
        return self.method_info(self.settings.default_translation_method).provider

    @property
    def methods(self) -> list[TranslationMethodInfo]:
        return [method for method in self._methods if method.enabled]

    def method_info(self, method: str) -> TranslationMethodInfo:
        for method_info in self.methods:
            if method_info.id == method:
                return method_info
        raise TranslationServiceError(f"Unsupported translation method: {method}")

    def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
        method: TranslationMethod | None = None,
    ) -> str:
        return self.translate_with_metadata(
            text=text,
            target_language=target_language,
            source_language=source_language,
            method=method,
        ).translated_text

    def translate_with_metadata(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
        method: TranslationMethod | None = None,
    ) -> TranslateResponse:
        clean_text = text.strip()
        selected_method = method or self.settings.default_translation_method
        method_info = self.method_info(selected_method)
        resolved_source = self._resolve_source_language(clean_text, source_language)
        self._validate_language(target_language)
        if resolved_source != "auto" and resolved_source == target_language:
            translated = clean_text
            quality_notes = "Source and target languages are the same; text was returned unchanged."
        elif selected_method == "google":
            translated = self._translate_with_google(
                text=clean_text,
                source_language=source_language,
                target_language=target_language,
            )
            quality_notes = "Fast general-purpose translation. Review technical terminology for important work."
        elif selected_method == "llm":
            translated = self._translate_with_llm(
                text=clean_text,
                source_language=resolved_source,
                target_language=target_language,
            )
            quality_notes = "Context-aware LLM translation. Good for technical explanations, but verify exact wording."
        elif selected_method == "nllb":
            translated = self._translate_with_nllb(
                text=clean_text,
                source_language=resolved_source,
                target_language=target_language,
            )
            quality_notes = "Dedicated NLLB machine translation output. Compare with LLM output for technical nuance."
        else:
            raise TranslationServiceError(f"Unsupported translation method: {selected_method}")

        return TranslateResponse(
            source_language=resolved_source,
            target_language=target_language,
            translated_text=translated,
            provider=method_info.provider,
            method=selected_method,
            quality_notes=quality_notes,
        )

    def compare(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
        methods: list[TranslationMethod] | None = None,
    ) -> TranslationCompareResponse:
        selected_methods = methods or [method.id for method in self.methods]
        results: list[TranslateResponse] = []
        last_error: Exception | None = None
        for method in selected_methods:
            try:
                results.append(
                    self.translate_with_metadata(
                        text=text,
                        target_language=target_language,
                        source_language=source_language,
                        method=method,
                    )
                )
            except Exception as exc:
                last_error = exc
                continue

        if not results and last_error is not None:
            raise last_error

        resolved_source = self._resolve_source_language(text, source_language)
        return TranslationCompareResponse(
            source_language=resolved_source,
            target_language=target_language,
            results=results,
        )

    def _translate_with_google(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        from deep_translator import GoogleTranslator

        source_code = "auto" if source_language == "auto" else self._code_for(source_language, "google")
        target_code = self._code_for(target_language, "google")
        translator = GoogleTranslator(source=source_code, target=target_code)
        return translator.translate(text)

    def _translate_with_llm(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        if self.llm_service is None:
            raise TranslationMethodUnavailableError(
                "LLM translation is unavailable because no LLM service is configured."
            )
        try:
            return self.llm_service.translate_text(
                text=text,
                source_language=source_language,
                target_language=target_language,
            )
        except ValueError as exc:
            raise TranslationMethodUnavailableError(str(exc)) from exc

    def _translate_with_nllb(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        if source_language == "auto":
            source_language = self.language_registry.detect_language(text)
        source_code = self._code_for(source_language, "nllb")
        target_code = self._code_for(target_language, "nllb")
        tokenizer, model = self._load_nllb()
        tokenizer.src_lang = source_code
        inputs = tokenizer(text, return_tensors="pt", truncation=True)
        generated_tokens = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids(target_code),
            max_length=512,
        )
        return tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]

    def _load_nllb(self):
        if self._nllb_tokenizer is None or self._nllb_model is None:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            self._nllb_tokenizer = AutoTokenizer.from_pretrained(self.settings.nllb_model_name)
            self._nllb_model = AutoModelForSeq2SeqLM.from_pretrained(self.settings.nllb_model_name)
        return self._nllb_tokenizer, self._nllb_model

    def _resolve_source_language(self, text: str, source_language: str) -> str:
        if source_language == "auto":
            return self.language_registry.detect_language(text)
        self._validate_language(source_language)
        return source_language

    def _validate_language(self, language_code: str) -> None:
        if not self.language_registry.is_supported(language_code):
            raise TranslationServiceError(f"Unsupported language: {language_code}")

    def _code_for(self, language_code: str, method: str) -> str:
        language_entry = self._language_codes.get(language_code, {})
        code = language_entry.get(method)
        if not code:
            raise TranslationServiceError(
                f"Language {language_code} is not configured for {method} translation."
            )
        return code

    def _load_methods(self) -> list[TranslationMethodInfo]:
        path = self.settings.translation_methods_config_path
        if not path.exists():
            return [
                TranslationMethodInfo(
                    id="google",
                    display_name="Google Translate",
                    provider="deep-translator",
                )
            ]
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [TranslationMethodInfo(**item) for item in raw]

    def _load_language_codes(self) -> dict[str, dict[str, str]]:
        path: Path = self.settings.translation_language_codes_path
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
