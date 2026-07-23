from pathlib import Path
from types import SimpleNamespace

from backend.app.services.language_quality import LanguageQualityService
from backend.app.services.languages import LanguageRegistry


def make_settings():
    return SimpleNamespace(
        language_quality_config_path=Path("config/language_quality_evaluation.json"),
        translation_language_codes_path=Path("config/translation_language_codes.json"),
    )


def test_language_quality_report_covers_priority_languages(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.language_quality.tokenizer_setup_issues",
        lambda strategies: [],
    )
    service = LanguageQualityService(
        settings=make_settings(),
        language_registry=LanguageRegistry(Path("config/languages.json")),
    )

    report = service.report()
    priority_codes = {language.code for language in report.priority_languages}

    assert priority_codes == {"ml", "hi", "ta", "kn", "ja", "ko", "fr", "es"}
    assert report.readiness_score == 1.0
    assert report.missing_items == []


def test_language_quality_report_includes_tokenizer_dependency_warnings(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.language_quality.tokenizer_setup_issues",
        lambda strategies: ["Japanese tokenizer strategy 'sudachipy' is enabled, but missing packages: sudachipy."],
    )
    service = LanguageQualityService(
        settings=make_settings(),
        language_registry=LanguageRegistry(Path("config/languages.json")),
    )

    report = service.report()

    assert report.readiness_score < 1.0
    assert any("sudachipy" in item for item in report.missing_items)


def test_language_quality_report_includes_cases_for_each_priority_language():
    service = LanguageQualityService(
        settings=make_settings(),
        language_registry=LanguageRegistry(Path("config/languages.json")),
    )

    report = service.report()
    covered_codes = {
        case.target_language
        for case in report.cases
    } | {
        case.source_language
        for case in report.cases
    }

    assert {"ml", "hi", "ta", "kn", "ja", "ko", "fr", "es"}.issubset(covered_codes)
    assert {case.category for case in report.cases} >= {
        "translation",
        "rag",
        "chunking",
        "answer_quality",
        "citation",
    }
