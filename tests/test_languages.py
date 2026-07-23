from pathlib import Path

from backend.app.services.languages import LanguageRegistry


def test_language_registry_loads_from_config():
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
    assert registry.tokenizer_strategy_for("ja") == "sudachipy"
    assert registry.tokenizer_strategy_for("ta") == "indic"
    assert registry.tokenizer_strategy_for("kn") == "indic"
    assert registry.tokenizer_strategy_for("ko") == "cjk"
    assert registry.get("ur").script_direction == "rtl"
    assert registry.get("fa").script_direction == "rtl"


def test_language_detection_by_script():
    registry = LanguageRegistry(Path("config/languages.json"))

    assert registry.detect_language("This paper proposes a method.") == "en"
    assert registry.detect_language("\u092f\u0939 \u0936\u094b\u0927 \u092a\u0924\u094d\u0930 \u0939\u0948") == "hi"
    assert registry.detect_language("\u0d07\u0d24\u0d4d \u0d12\u0d30\u0d41 \u0d17\u0d35\u0d47\u0d37\u0d23 \u0d32\u0d47\u0d16\u0d28\u0d2e\u0d3e\u0d23\u0d4d") == "ml"
    assert registry.detect_language("\u3053\u308c\u306f\u7814\u7a76\u8ad6\u6587\u3067\u3059") == "ja"
    assert registry.detect_language("\u0b87\u0ba4\u0bc1 \u0b92\u0bb0\u0bc1 \u0b86\u0bb0\u0bbe\u0baf\u0bcd\u0b9a\u0bcd\u0b9a\u0bbf") == "ta"
    assert registry.detect_language("\u0c87\u0ca6\u0cc1 \u0c92\u0c82\u0ca6\u0cc1 \u0cb8\u0c82\u0cb6\u0ccb\u0ca7\u0ca8\u0cc6") == "kn"
    assert registry.detect_language("\uc774\uac83\uc740 \uc5f0\uad6c\uc785\ub2c8\ub2e4") == "ko"
    assert registry.detect_language("\u0a86 \u0a85\u0aa8\u0ac1\u0ab5\u0abe\u0aa6 \u0a9b\u0ac7") == "gu"
    assert registry.detect_language("\u0a07\u0a39 \u0a16\u0a4b\u0a1c \u0a39\u0a48") == "pa"
    assert registry.detect_language("\u0b0f\u0b39\u0b3f \u0b17\u0b2c\u0b47\u0b37\u0b23\u0b3e") == "or"
    assert registry.detect_language("\u042d\u0442\u043e \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u0435") == "ru"
