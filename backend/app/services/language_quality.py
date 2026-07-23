from __future__ import annotations

import json
from pathlib import Path

from backend.app.core.config import Settings, get_settings
from backend.app.models.schemas import (
    LanguageQualityCase,
    LanguageQualityLanguage,
    LanguageQualityReport,
)
from backend.app.services.chunker import tokenizer_setup_issues
from backend.app.services.languages import LanguageRegistry, get_language_registry


class LanguageQualityService:
    def __init__(
        self,
        settings: Settings | None = None,
        language_registry: LanguageRegistry | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.language_registry = language_registry or get_language_registry()

    def report(self) -> LanguageQualityReport:
        config = self._load_config()
        translation_codes = self._load_translation_codes()
        priority_entries = config.get("priority_languages", [])
        cases = [LanguageQualityCase(**item) for item in config.get("cases", [])]

        languages = [
            self._language_status(
                code=str(item["code"]),
                priority_reason=str(item.get("priority_reason", "")),
                translation_codes=translation_codes,
            )
            for item in priority_entries
        ]
        missing_items = self._missing_items(languages, cases)
        readiness_score = _readiness_score(languages, missing_items)
        notes = [
            "This is a readiness and manual evaluation plan, not an automatic BLEU/COMET score.",
            "Use these cases to compare Google, LLM, and NLLB translation outputs for technical meaning.",
            "For RAG cases, verify that retrieved source passages match the question intent and citations stay visible.",
        ]

        return LanguageQualityReport(
            priority_languages=languages,
            cases=cases,
            readiness_score=readiness_score,
            missing_items=missing_items,
            notes=notes,
        )

    def _language_status(
        self,
        code: str,
        priority_reason: str,
        translation_codes: dict[str, dict[str, str]],
    ) -> LanguageQualityLanguage:
        language = self.language_registry.get(code)
        code_entry = translation_codes.get(code, {})
        if language is None:
            return LanguageQualityLanguage(
                code=code,
                name=code,
                family="unknown",
                script_direction="unknown",
                tokenizer_strategy="unknown",
                priority_reason=priority_reason,
                configured=False,
                google_translation=False,
                nllb_translation=False,
                embedding_supported=False,
            )

        return LanguageQualityLanguage(
            code=language.code,
            name=language.name,
            family=language.family,
            script_direction=language.script_direction,
            tokenizer_strategy=language.tokenizer_strategy,
            priority_reason=priority_reason,
            configured=True,
            google_translation=bool(code_entry.get("google")),
            nllb_translation=bool(code_entry.get("nllb")),
            embedding_supported=language.embedding_supported,
        )

    def _missing_items(
        self,
        languages: list[LanguageQualityLanguage],
        cases: list[LanguageQualityCase],
    ) -> list[str]:
        missing: list[str] = []
        configured_codes = self.language_registry.codes()
        case_codes = {case.target_language for case in cases} | {case.source_language for case in cases}
        priority_codes = {language.code for language in languages}

        for language in languages:
            if not language.configured:
                missing.append(f"{language.code}: missing language config")
            if not language.google_translation:
                missing.append(f"{language.code}: missing Google translation code")
            if not language.nllb_translation:
                missing.append(f"{language.code}: missing NLLB translation code")
            if not language.embedding_supported:
                missing.append(f"{language.code}: embedding support disabled")
            if language.code not in case_codes:
                missing.append(f"{language.code}: no evaluation case")

        for case in cases:
            if case.source_language != "auto" and case.source_language not in configured_codes:
                missing.append(f"{case.id}: source language {case.source_language} is not configured")
            if case.target_language not in configured_codes:
                missing.append(f"{case.id}: target language {case.target_language} is not configured")
            if case.target_language not in priority_codes and case.source_language not in priority_codes:
                missing.append(f"{case.id}: case does not cover a priority language")

        tokenizer_issues = tokenizer_setup_issues(
            {language.tokenizer_strategy for language in self.language_registry.languages}
        )
        missing.extend(tokenizer_issues)
        return missing

    def _load_config(self) -> dict:
        path: Path = self.settings.language_quality_config_path
        if not path.exists():
            return {"priority_languages": [], "cases": []}
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_translation_codes(self) -> dict[str, dict[str, str]]:
        path: Path = self.settings.translation_language_codes_path
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))


def _readiness_score(
    languages: list[LanguageQualityLanguage],
    missing_items: list[str],
) -> float:
    if not languages:
        return 0.0
    total_checks = len(languages) * 5
    passed_checks = max(0, total_checks - len(missing_items))
    return round(passed_checks / total_checks, 3)
