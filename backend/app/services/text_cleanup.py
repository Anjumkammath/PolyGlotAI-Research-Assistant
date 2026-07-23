import re


ACRONYMS = {
    "api": "API",
    "ats": "ATS",
    "blob": "BLOB",
    "boolean": "BOOLEAN",
    "char": "CHAR",
    "crud": "CRUD",
    "db": "DB",
    "dbms": "DBMS",
    "dcl": "DCL",
    "ddl": "DDL",
    "dml": "DML",
    "dql": "DQL",
    "drl": "DRL",
    "float": "FLOAT",
    "int": "INT",
    "mysql": "MySQL",
    "opencv": "OpenCV",
    "nlp": "NLP",
    "pdf": "PDF",
    "rdbms": "RDBMS",
    "sql": "SQL",
    "tcl": "TCL",
    "varchar": "VARCHAR",
}

COMPACT_PREFIX_TERMS = (
    "POSTGRESQL",
    "RDBMS",
    "DBMS",
    "SELECT",
    "UPDATE",
    "INSERT",
    "DELETE",
    "CREATE",
    "ALTER",
    "DROP",
    "GRANT",
    "REVOKE",
    "SQLITE",
    "MYSQL",
    "FASTAPI",
    "DQL",
    "DDL",
    "DML",
    "DCL",
    "TCL",
    "CRUD",
    "API",
    "SQL",
    "NOT",
)


COMMON_WORDS = {
    "a",
    "about",
    "access",
    "accuracy",
    "add",
    "adds",
    "already",
    "also",
    "alter",
    "an",
    "analyse",
    "and",
    "apna",
    "are",
    "as",
    "attribute",
    "attributes",
    "authorised",
    "average",
    "based",
    "be",
    "between",
    "by",
    "called",
    "can",
    "case",
    "cases",
    "college",
    "collection",
    "column",
    "columns",
    "command",
    "commands",
    "concept",
    "condition",
    "consistency",
    "constraints",
    "control",
    "create",
    "created",
    "currency",
    "data",
    "database",
    "databases",
    "datatype",
    "datatypes",
    "date",
    "define",
    "defining",
    "delete",
    "deleted",
    "description",
    "display",
    "drop",
    "eg",
    "enable",
    "enables",
    "ensuring",
    "equal",
    "etc",
    "existing",
    "fixed",
    "for",
    "from",
    "generally",
    "grant",
    "group",
    "have",
    "here",
    "in",
    "index",
    "insert",
    "inserted",
    "integer",
    "integrity",
    "interact",
    "interrelated",
    "is",
    "it",
    "joins",
    "kind",
    "keyword",
    "keywords",
    "language",
    "length",
    "like",
    "management",
    "manage",
    "managing",
    "manipulate",
    "modify",
    "more",
    "new",
    "note",
    "notes",
    "not",
    "object",
    "objects",
    "of",
    "on",
    "only",
    "operations",
    "operator",
    "operators",
    "or",
    "organized",
    "permissions",
    "positive",
    "present",
    "primary",
    "query",
    "range",
    "read",
    "record",
    "records",
    "relation",
    "relational",
    "relations",
    "retrieve",
    "retrieved",
    "retrieving",
    "revoke",
    "responsible",
    "rows",
    "same",
    "select",
    "sensitive",
    "software",
    "specific",
    "statement",
    "statements",
    "store",
    "stored",
    "string",
    "structured",
    "structure",
    "subset",
    "syntax",
    "system",
    "table",
    "tables",
    "that",
    "the",
    "their",
    "this",
    "to",
    "transaction",
    "transactions",
    "types",
    "unsigned",
    "update",
    "usage",
    "use",
    "used",
    "user",
    "values",
    "variable",
    "visit",
    "we",
    "what",
    "when",
    "where",
    "while",
    "with",
    "within",
}

MAX_WORD_LENGTH = max(len(word) for word in COMMON_WORDS | set(ACRONYMS))


def clean_pdf_text(text: str, *, repair_compacted: bool = True) -> str:
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00e2\u0080\u00a2": " - ",
        "\u2022": " - ",
        "\u25cf": " - ",
        "\u25cb": " - ",
        "\u00e2\u0080\u0093": "-",
        "\u00e2\u0080\u0094": "-",
        "\u00e2\u0080\u0099": "'",
        "\u00e2\u0080\u009c": '"',
        "\u00e2\u0080\u009d": '"',
        "\u00c2": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\bA\s+TS\b", "ATS", text)
    text = re.sub(r"\bGen\s*AI\b", "GenAI", text)
    text = re.sub(r"\bOpen\s*CV\b", "OpenCV", text)
    text = re.sub(r"\bT\s+ools\b", "Tools", text)

    protected_terms = {
        "__ATS__": "ATS",
        "__GENAI__": "GenAI",
        "__GITHUB__": "GitHub",
        "__LABELGUARD__": "LabelGuard",
        "__LANGCHAIN__": "LangChain",
        "__MYSQL__": "MySQL",
        "__NUMPY__": "NumPy",
        "__OPENCV__": "OpenCV",
        "__OPENAI__": "OpenAI",
        "__POSTGRESQL__": "PostgreSQL",
        "__PYTORCH__": "PyTorch",
        "__TENSORFLOW__": "TensorFlow",
        "__SQLITE__": "SQLite",
        "__FASTAPI__": "FastAPI",
    }
    for placeholder, term in protected_terms.items():
        text = text.replace(term, placeholder)

    text = re.sub(r"([A-Za-z])-\s+([a-z])", r"\1\2", text)
    text = re.sub(r"(?<=[A-Za-z])\(", " (", text)
    text = re.sub(r"\)(?=[A-Za-z])", ") ", text)
    text = re.sub(r"([a-z])([A-Z]{2,})", r"\1 \2", text)
    for term in COMPACT_PREFIX_TERMS:
        text = re.sub(fr"(?<![A-Za-z]){term}(?=[A-Z]?[a-z])", f"{term} ", text)
    text = re.sub(r"(?<=[a-z])(?=[A-Z][a-z])", " ", text)
    text = re.sub(r"([.!?:;,])(?=[A-Za-z])", r"\1 ", text)
    for placeholder, term in protected_terms.items():
        text = text.replace(placeholder, term)
    text = re.sub(r"\s+", " ", text).strip()

    if repair_compacted:
        text = re.sub(r"[A-Za-z]{7,}", _repair_token, text)
        text = re.sub(r"\s+", " ", text).strip()
    return text


def _repair_token(match: re.Match[str]) -> str:
    token = match.group(0)
    pieces = _segment_token(token)
    if not pieces or len(pieces) <= 1:
        return token
    return " ".join(_format_piece(piece, token, index) for index, piece in enumerate(pieces))


def _segment_token(token: str) -> list[str] | None:
    lower_token = token.lower()
    length = len(lower_token)
    best: list[tuple[float, list[str]] | None] = [None] * (length + 1)
    best[0] = (0.0, [])

    for start in range(length):
        if best[start] is None:
            continue
        current_score, current_parts = best[start]
        for end in range(start + 1, min(length, start + MAX_WORD_LENGTH) + 1):
            piece = lower_token[start:end]
            if piece not in COMMON_WORDS and piece not in ACRONYMS:
                continue
            word_score = 1.0 - min(len(piece), 12) * 0.06
            next_score = current_score + word_score
            candidate = current_parts + [piece]
            if best[end] is None or next_score < best[end][0]:
                best[end] = (next_score, candidate)

    if best[length] is None:
        return None
    return best[length][1]


def _format_piece(piece: str, original: str, index: int) -> str:
    if piece in ACRONYMS:
        return ACRONYMS[piece]
    if index == 0 and original[0].isupper():
        return piece.capitalize()
    return piece
