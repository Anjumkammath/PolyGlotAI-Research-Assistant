import os
import html
import re
from uuid import uuid4

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def api_get(path: str):
    response = requests.get(f"{API_BASE_URL}{path}", timeout=20)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict):
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def api_post_empty(path: str):
    response = requests.post(f"{API_BASE_URL}{path}", timeout=300)
    response.raise_for_status()
    return response.json()


def api_delete(path: str):
    response = requests.delete(f"{API_BASE_URL}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def clean_display_text(text: str) -> str:
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00e2\u0080\u00a2": "-",
        "\u2022": "-",
        "\u00e2\u0080\u0093": "-",
        "\u00e2\u0080\u0094": "-",
        "\u00e2\u0080\u0099": "'",
        "\u00e2\u0080\u009c": '"',
        "\u00e2\u0080\u009d": '"',
        "\u00c2": "",
    }
    cleaned = str(text)
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    cleaned = re.sub(r"\bA\s+TS\b", "ATS", cleaned)
    cleaned = re.sub(r"\bGen\s*AI\b", "GenAI", cleaned)
    cleaned = re.sub(r"\bOpen\s*CV\b", "OpenCV", cleaned)
    cleaned = re.sub(r"\bT\s+ools\b", "Tools", cleaned)
    cleaned = re.sub(r"([A-Za-z])-\s+([a-z])", r"\1\2", cleaned)
    cleaned = re.sub(r"([.!?:;,])(?=[A-Za-z])", r"\1 ", cleaned)
    return " ".join(cleaned.split())


ANSWER_STYLE_OPTIONS = {
    "Auto": "auto",
    "Short": "short",
    "Detailed": "detailed",
    "Beginner-friendly": "beginner",
    "Technical": "technical",
}

DOCUMENT_TYPE_LABELS = {
    "research_paper": "Research paper",
    "resume_cv": "Resume / CV",
    "study_notes": "Study notes",
    "document": "Document",
}

RETRIEVAL_MODE_LABELS = {
    "vector": "Vector search",
    "lexical_fallback": "Fallback search",
    "overview_bypass": "Overview mode",
    "unknown": "Unknown",
}


def display_answer_style(style: str | None) -> str:
    for label, value in ANSWER_STYLE_OPTIONS.items():
        if value == style:
            return label
    return "Auto"


def display_document_type(document_type: str | None) -> str:
    return DOCUMENT_TYPE_LABELS.get(document_type or "", "Document")


def display_retrieval_mode(retrieval_mode: str | None) -> str:
    return RETRIEVAL_MODE_LABELS.get(retrieval_mode or "unknown", retrieval_mode or "Unknown")


def render_pill(label: str, value: str, tone: str = "cyan") -> None:
    safe_label = html.escape(label)
    safe_value = html.escape(value)
    st.markdown(
        f"""
        <div class="meta-pill meta-pill-{tone}">
            <span>{safe_label}</span>
            <strong>{safe_value}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_source_cards(citations: list[dict], title: str = "Sources", expanded: bool = False) -> None:
    if not citations:
        return

    with st.expander(title, expanded=expanded):
        for citation in citations:
            score = citation.get("score")
            score_text = "" if score is None else f"Relevance {score:.2f}"
            excerpt = html.escape(clean_display_text(citation.get("excerpt", "")))
            source_name = html.escape(citation.get("source_name", "Source"))
            citation_id = html.escape(citation.get("citation_id", "C?"))
            page = citation.get("page")
            meta = f"Page {page}" if page else "Source passage"
            if score_text:
                meta = f"{meta} - {score_text}"
            st.markdown(
                f"""
                <div class="source-card">
                    <div class="source-card-top">
                        <span class="source-badge">{citation_id}</span>
                        <div>
                            <div class="source-title">{source_name}</div>
                            <div class="source-meta">{html.escape(meta)}</div>
                        </div>
                    </div>
                    <p>{excerpt}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def friendly_error(error: Exception) -> str:
    detail = str(error)
    if "Connection" in detail or "Failed to establish" in detail:
        return "The assistant service is not reachable yet. Please make sure the app is running."
    if "500" in detail:
        return "I could not complete that request. Try preparing chunks for the document, then ask again."
    return detail


def language_options() -> dict[str, str]:
    try:
        languages = api_get("/languages")
    except Exception:
        return {"English": "en", "Japanese": "ja", "Hindi": "hi", "Malayalam": "ml"}
    return {f"{item['name']} ({item['code']})": item["code"] for item in languages}


def current_document_id(uploaded_documents: list[dict]) -> str | None:
    document_ids = {document["document_id"] for document in uploaded_documents}
    active_id = st.session_state.get("active_document_id")
    if active_id in document_ids:
        return active_id

    last_document = st.session_state.get("last_document")
    if last_document and last_document.get("document_id") in document_ids:
        return last_document["document_id"]

    if uploaded_documents:
        return uploaded_documents[0]["document_id"]
    return None


def render_document_detail(document: dict) -> None:
    status = document["extraction_status"]
    if status == "ready":
        st.success(document.get("message", "Text extraction ready."))
    else:
        st.warning(document.get("message", "No selectable text was found."))

    metric_col_a, metric_col_b, metric_col_c = st.columns(3)
    metric_col_a.metric("Pages", document["total_pages"])
    metric_col_b.metric("Text pages", document["pages_with_text"])
    metric_col_c.metric("Characters", document["total_characters"])

    with st.expander("Page previews", expanded=True):
        for page in document["page_previews"]:
            label = f"Page {page['page_number']} - {page['character_count']} chars"
            with st.expander(label):
                if page["has_text"]:
                    st.write(page["preview"])
                else:
                    st.caption("No selectable text found on this page.")


def render_chunk_detail(chunks: dict) -> None:
    st.success(chunks["message"])
    metric_col_a, metric_col_b, metric_col_c = st.columns(3)
    metric_col_a.metric("Chunks", chunks["chunk_count"])
    metric_col_b.metric("Size", chunks["chunk_size"])
    metric_col_c.metric("Overlap", chunks["chunk_overlap"])
    st.caption("Detected languages: " + ", ".join(chunks["detected_languages"]))

    with st.expander("Chunk previews", expanded=True):
        for chunk in chunks["chunks"][:12]:
            label = f"Chunk {chunk['chunk_index']} - page {chunk['page_start']}"
            with st.expander(label):
                st.write(clean_display_text(chunk["preview"]))


st.set_page_config(
    page_title="PolyGlotAI Research Assistant",
    page_icon="P",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    :root {
        --bg: #12141A;
        --surface: #1B1E27;
        --accent-primary: #E8A33D;
        --accent-secondary: #4FB6C4;
        --text-primary: #EDEDE6;
        --border: rgba(86, 91, 102, 0.28);
        --muted: rgba(237, 237, 230, 0.68);
        --muted-strong: rgba(237, 237, 230, 0.82);
    }

    .stApp {
        background: var(--bg) !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
    }

    header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stStatusWidget"], #MainMenu {
        display: none !important;
    }

    .block-container {
        max-width: 1280px !important;
        padding: 28px 28px 64px !important;
    }

    h1, h2, h3 {
        color: var(--text-primary) !important;
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: 0 !important;
    }

    p, li, label, span, div {
        font-family: 'Inter', sans-serif;
    }

    a {
        color: var(--accent-secondary) !important;
    }

    a:focus-visible,
    button:focus-visible,
    input:focus-visible,
    textarea:focus-visible {
        outline: 2px solid var(--accent-primary) !important;
        outline-offset: 3px !important;
        border-radius: 8px !important;
    }

    .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--muted) !important;
    }

    .poly-hero {
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(320px, 0.85fr);
        gap: 22px;
        align-items: stretch;
        margin: 4px 0 24px;
    }

    .hero-copy-panel,
    .hero-feature-panel {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        box-shadow: 0 24px 80px rgba(0, 0, 0, 0.24);
    }

    .hero-copy-panel {
        padding: 24px 28px;
    }

    .hero-eyebrow {
        color: var(--accent-primary);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        margin-bottom: 16px;
    }

    .hero-title {
        color: var(--text-primary);
        font-family: 'Space Grotesk', sans-serif;
        font-size: clamp(34px, 5vw, 48px);
        font-weight: 700;
        line-height: 1.04;
        margin: 0 0 10px;
    }

    .hero-description {
        color: var(--muted);
        font-size: 16px;
        line-height: 1.65;
        margin: 0;
        max-width: 780px;
    }

    .hero-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 22px;
    }

    .hero-tag {
        border: 1px solid rgba(79, 182, 196, 0.4);
        border-radius: 999px;
        color: var(--accent-secondary);
        display: inline-flex;
        align-items: center;
        padding: 7px 12px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        line-height: 1;
    }

    .hero-feature-panel {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px;
        padding: 20px;
    }

    .hero-feature-card {
        background: rgba(16, 19, 27, 0.72);
        border: 1px solid rgba(86, 91, 102, 0.5);
        border-radius: 8px;
        padding: 16px;
        min-height: 128px;
    }

    .feature-stat {
        color: var(--accent-primary);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .feature-title {
        color: var(--text-primary);
        font-family: 'Space Grotesk', sans-serif;
        font-size: 18px;
        font-weight: 700;
        line-height: 1.25;
        margin-bottom: 8px;
    }

    .feature-copy {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.55;
        margin: 0;
    }

    [data-testid="stSidebar"] {
        background: #0f1117 !important;
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] * {
        color: var(--text-primary) !important;
    }

    [data-testid="stSidebar"] .stButton button {
        border: 1px solid var(--border);
        background: transparent;
        color: var(--text-primary);
    }

    div.stButton > button {
        min-height: 2.7rem;
        border-radius: 8px;
        border: 1px solid var(--accent-primary);
        background: var(--accent-primary);
        color: #12141A !important;
        font-weight: 700;
        box-shadow: 0 12px 32px rgba(232, 163, 61, 0.16);
        transition: transform 160ms ease, border-color 160ms ease, filter 160ms ease;
    }

    div.stButton > button:hover {
        transform: translateY(-1px);
        border-color: var(--accent-primary);
        filter: brightness(1.05);
    }

    div[data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-left: 4px solid var(--accent-primary);
        border-radius: 8px;
        padding: 0.7rem 0.85rem;
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.18);
    }

    div[data-testid="stMetric"] * {
        color: var(--text-primary) !important;
    }

    div[data-testid="stExpander"] {
        background: var(--surface);
        border-radius: 8px;
        border: 1px solid var(--border);
        color: var(--text-primary);
        box-shadow: 0 14px 38px rgba(0, 0, 0, 0.16);
    }

    div[data-testid="stExpander"] details,
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] p {
        color: var(--text-primary) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.4rem;
        border-bottom: 1px solid var(--border);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.65rem 1rem;
        background: var(--surface);
        border: 1px solid var(--border);
        color: var(--muted) !important;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 13px;
    }

    .stTabs [aria-selected="true"] {
        color: #12141A !important;
        background: var(--accent-primary) !important;
        border-color: var(--accent-primary) !important;
    }

    [data-testid="stFileUploader"],
    [data-testid="stTextInput"],
    [data-testid="stTextArea"],
    [data-testid="stSelectbox"],
    [data-testid="stMultiSelect"],
    [data-testid="stSlider"] {
        color: var(--text-primary) !important;
    }

    input, textarea,
    [data-baseweb="select"] > div,
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea {
        background: #11141c !important;
        color: var(--text-primary) !important;
        border-color: var(--border) !important;
        border-radius: 8px !important;
    }

    [data-testid="stFileUploaderDropzone"] {
        background: var(--surface) !important;
        border: 1px dashed rgba(79, 182, 196, 0.42) !important;
        border-radius: 8px !important;
    }

    [data-testid="stAlert"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        color: var(--text-primary);
    }

    [data-testid="stChatMessage"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
    }

    .section-note {
        color: var(--muted);
        font-size: 14px;
        line-height: 1.7;
        margin-top: -0.4rem;
        margin-bottom: 1rem;
    }

    .answer-meta-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 8px 0 12px;
    }

    .meta-pill {
        align-items: center;
        background: rgba(79, 182, 196, 0.08);
        border: 1px solid rgba(79, 182, 196, 0.28);
        border-radius: 999px;
        color: var(--muted-strong);
        display: inline-flex;
        gap: 8px;
        padding: 7px 11px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        margin: 0 7px 8px 0;
    }

    .meta-pill span {
        color: var(--muted);
        font-family: 'IBM Plex Mono', monospace;
    }

    .meta-pill strong {
        color: var(--text-primary);
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
    }

    .meta-pill-amber {
        background: rgba(232, 163, 61, 0.08);
        border-color: rgba(232, 163, 61, 0.32);
    }

    .source-card {
        background: #11141c;
        border: 1px solid var(--border);
        border-radius: 8px;
        margin: 0 0 12px;
        padding: 14px;
    }

    .source-card-top {
        align-items: flex-start;
        display: flex;
        gap: 10px;
        margin-bottom: 10px;
    }

    .source-badge {
        background: var(--accent-primary);
        border-radius: 6px;
        color: #12141A;
        display: inline-flex;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        font-weight: 700;
        justify-content: center;
        min-width: 34px;
        padding: 5px 7px;
    }

    .source-title {
        color: var(--text-primary);
        font-weight: 700;
        line-height: 1.35;
    }

    .source-meta {
        color: var(--muted);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        margin-top: 2px;
    }

    .source-card p {
        color: var(--muted-strong);
        line-height: 1.65;
        margin: 0;
    }

    .stMarkdown, .stMarkdown p, .stWrite, .stText {
        color: var(--text-primary);
    }

    hr {
        border-color: var(--border) !important;
    }

    @media (max-width: 900px) {
        .poly-hero {
            grid-template-columns: 1fr;
            margin-top: 0;
        }

        .hero-copy-panel {
            padding: 20px;
        }

        .hero-feature-panel {
            grid-template-columns: 1fr;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid4())
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

hero_language_count = len(language_options())

st.markdown(
    f"""
    <section class="poly-hero">
        <div class="hero-copy-panel">
            <div class="hero-eyebrow">Multilingual Research AI Bot</div>
            <h1 class="hero-title">PolyGlotAI Research Assistant</h1>
            <p class="hero-description">
                A multilingual research assistant that reads your papers, answers in your language, and always shows its work.
            </p>
            <div class="hero-actions">
                <span class="hero-tag">RAG</span>
                <span class="hero-tag">Citations</span>
                <span class="hero-tag">Translation</span>
                <span class="hero-tag">Memory</span>
                <span class="hero-tag">FastAPI</span>
            </div>
        </div>
        <div class="hero-feature-panel" aria-label="Assistant capabilities">
            <div class="hero-feature-card">
                <div class="feature-stat">Ready</div>
                <div class="feature-title">Ask papers</div>
                <p class="feature-copy">Upload PDFs and get answers grounded in source passages.</p>
            </div>
            <div class="hero-feature-card">
                <div class="feature-stat">{hero_language_count} languages</div>
                <div class="feature-title">Multilingual support</div>
                <p class="feature-copy">Work across English, Indian languages, Japanese, Korean, French, Spanish, and more.</p>
            </div>
            <div class="hero-feature-card">
                <div class="feature-stat">Cited</div>
                <div class="feature-title">Shows its work</div>
                <p class="feature-copy">Every answer can include source labels, page numbers, and excerpts.</p>
            </div>
            <div class="hero-feature-card">
                <div class="feature-stat">Research tools</div>
                <div class="feature-title">Summarize and translate</div>
                <p class="feature-copy">Create summaries and translate technical text without leaving the workspace.</p>
            </div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Workspace")
    st.text_input("Session ID", value=st.session_state.session_id, disabled=True)
    if st.button("Start new session", use_container_width=True):
        st.session_state.session_id = str(uuid4())
        st.session_state.chat_history = []
        st.rerun()

    if st.button("Clear current memory", use_container_width=True):
        try:
            api_delete(f"/sessions/{st.session_state.session_id}")
            st.session_state.chat_history = []
            st.success("Current session memory cleared.")
        except Exception as exc:
            st.error(f"Could not clear memory: {exc}")

    st.divider()
    st.header("Status")
    try:
        health = api_get("/health")
        st.success("Assistant is ready")
    except Exception:
        st.error("Assistant is offline.")

    st.divider()
    st.header("Conversation")
    try:
        current_session = api_get(f"/sessions/{st.session_state.session_id}")
        st.caption(f"Saved messages: {current_session['message_count']}")
        with st.expander("Current session"):
            if not current_session["messages"]:
                st.caption("No stored messages yet.")
            for message in current_session["messages"][-6:]:
                st.markdown(f"**{message['role']}**")
                st.caption(message["created_at"])
                st.write(clean_display_text(message["content"]))

        recent_sessions = api_get("/sessions?limit=5")
        with st.expander("Recent sessions"):
            if not recent_sessions:
                st.caption("No sessions stored yet.")
            for session in recent_sessions:
                st.caption(
                    f"{session['session_id'][:8]} | "
                    f"{session['message_count']} messages"
                )
    except Exception:
        st.caption("Conversation details are unavailable.")

languages = language_options()
ask_tab, summarize_tab, translate_tab, embeddings_tab, language_qa_tab = st.tabs(
    ["Ask papers", "Summarize", "Translate text", "Embeddings", "Language QA"]
)

with ask_tab:
    upload_col, chat_col = st.columns([0.34, 0.66], gap="large")
    uploaded_documents = []

    with upload_col:
        st.subheader("Papers")
        uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
        if uploaded_file and st.button("Upload and read", type="primary", use_container_width=True):
            with st.spinner("Reading the paper..."):
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        "application/pdf",
                    )
                }
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/documents/upload",
                        files=files,
                        timeout=300,
                    )
                    response.raise_for_status()
                    result = response.json()
                    st.session_state.last_document = result
                    st.session_state.active_document_id = result["document_id"]
                except Exception as exc:
                    st.error(f"Upload failed: {exc}")

        if "last_document" in st.session_state:
            render_document_detail(st.session_state.last_document)
            if st.button(
                "Prepare for questions",
                key=f"chunk-last-{st.session_state.last_document['document_id']}",
                use_container_width=True,
            ):
                with st.spinner("Preparing document sections..."):
                    try:
                        st.session_state.last_chunks = api_post_empty(
                            f"/documents/{st.session_state.last_document['document_id']}/chunks"
                        )
                        st.session_state.active_document_id = st.session_state.last_document[
                            "document_id"
                        ]
                    except Exception as exc:
                        st.error(f"Chunking failed: {exc}")

        if "last_chunks" in st.session_state:
            render_chunk_detail(st.session_state.last_chunks)

        st.divider()
        st.subheader("Uploaded")
        try:
            uploaded_documents = api_get("/documents")
            if not uploaded_documents:
                st.caption("No PDFs uploaded yet.")
            for document in uploaded_documents[:5]:
                with st.expander(document["filename"]):
                    st.caption(
                        f"{document['total_pages']} pages, "
                        f"{document['pages_with_text']} with text, "
                        f"status: {document['extraction_status']}"
                    )
                    if document.get("chunks_ready"):
                        st.info(
                            f"{document.get('chunk_count', 0)} chunks ready; "
                            f"languages: {', '.join(document.get('detected_languages', []))}"
                        )
                        if st.button(
                            "View chunks",
                            key=f"view-chunks-{document['document_id']}",
                            use_container_width=True,
                        ):
                            try:
                                st.session_state.active_document_id = document["document_id"]
                                st.session_state.last_chunks = api_get(
                                    f"/documents/{document['document_id']}/chunks"
                                )
                            except Exception as exc:
                                st.error(f"Could not load chunks: {exc}")
                    elif st.button(
                        "Prepare for questions",
                        key=f"chunk-{document['document_id']}",
                        use_container_width=True,
                    ):
                        with st.spinner("Preparing document sections..."):
                            try:
                                st.session_state.active_document_id = document["document_id"]
                                st.session_state.last_chunks = api_post_empty(
                                    f"/documents/{document['document_id']}/chunks"
                                )
                                st.success(
                                    f"Prepared {st.session_state.last_chunks['chunk_count']} chunks."
                                )
                            except Exception as exc:
                                st.error(f"Chunking failed: {exc}")
                    if document["indexed"]:
                        st.success("Enhanced search ready")
                    elif st.button(
                        "Improve search",
                        key=f"index-{document['document_id']}",
                        use_container_width=True,
                    ):
                        with st.spinner("Improving source search..."):
                            try:
                                st.session_state.active_document_id = document["document_id"]
                                result = api_post_empty(
                                    f"/documents/{document['document_id']}/index"
                                )
                                st.success(
                                    f"Prepared {result['chunks_indexed']} searchable sections."
                                )
                            except Exception as exc:
                                st.error(f"Could not improve search: {friendly_error(exc)}")
        except Exception:
            st.caption("Uploaded document list is unavailable.")

        st.divider()
        with st.expander("Advanced source search"):
            vector_query = st.text_input(
                "Search passages",
                placeholder="Example: main contribution of the paper",
            )
            vector_top_k = st.slider("Results", min_value=1, max_value=8, value=3)
            if st.button("Search sources", use_container_width=True) and vector_query.strip():
                with st.spinner("Searching sources..."):
                    try:
                        result = api_post(
                        "/vectors/search",
                        {
                            "query": vector_query.strip(),
                            "top_k": vector_top_k,
                            "document_id": current_document_id(uploaded_documents),
                        },
                    )
                        if not result["results"]:
                            st.info("No matching passages found yet. Try improving search for a document first.")
                        for item in result["results"]:
                            score = item["score"]
                            score_text = "" if score is None else f" score {score:.3f}"
                            with st.expander(
                                f"{item['source_name']} - page {item['page']}{score_text}"
                            ):
                                st.write(clean_display_text(item["excerpt"]))
                    except Exception as exc:
                        st.error(f"Source search failed: {friendly_error(exc)}")

    with chat_col:
        st.subheader("Assistant")
        active_document_id = current_document_id(uploaded_documents)
        document_labels = {}
        default_scope_index = 0
        if uploaded_documents:
            for document in uploaded_documents:
                label_prefix = (
                    "Current PDF: "
                    if document["document_id"] == active_document_id
                    else ""
                )
                label = f"{label_prefix}{document['filename']} ({document['document_id'][:8]})"
                document_labels[label] = document["document_id"]
            document_labels["All uploaded PDFs"] = None
            default_scope_index = next(
                (
                    index
                    for index, document_id in enumerate(document_labels.values())
                    if document_id == active_document_id
                ),
                0,
            )
        else:
            document_labels["Upload a PDF first"] = None
        selected_document_label = st.selectbox(
            "Search scope",
            options=list(document_labels.keys()),
            index=default_scope_index,
        )
        selected_document_id = document_labels[selected_document_label]
        if selected_document_id:
            st.session_state.active_document_id = selected_document_id
            st.caption(f"Answering from: {selected_document_label.replace('Current PDF: ', '')}")
        settings_col_a, settings_col_b = st.columns(2)
        with settings_col_a:
            selected_language = st.selectbox(
                "Answer language",
                options=list(languages.keys()),
                index=0,
            )
        with settings_col_b:
            selected_answer_style = st.selectbox(
                "Answer style",
                options=list(ANSWER_STYLE_OPTIONS.keys()),
                index=0,
            )
        source_depth = st.slider(
            "Sources to inspect",
            min_value=3,
            max_value=8,
            value=5,
            help="Use fewer sources for faster answers and more sources for broader explanations.",
        )
        question = st.text_area(
            "Ask a question about the uploaded papers",
            height=120,
            placeholder="Example: What is this document about? Explain the main contribution.",
        )
        ask_clicked = st.button("Ask", type="primary", use_container_width=True)

        if ask_clicked and question.strip():
            payload = {
                "question": question.strip(),
                "session_id": st.session_state.session_id,
                "document_id": selected_document_id,
                "target_language": languages[selected_language],
                "translate_answer": True,
                "top_k": source_depth,
                "answer_style": ANSWER_STYLE_OPTIONS[selected_answer_style],
            }
            with st.spinner("Searching the papers and preparing an answer..."):
                try:
                    result = api_post("/chat", payload)
                    st.session_state.chat_history.append(
                        {
                            "question": question.strip(),
                            "answer": result["answer"],
                            "citations": result["citations"],
                            "retrieved_context": result.get("retrieved_context", []),
                            "retrieved_chunks": result.get("retrieved_chunks", 0),
                            "cited_chunks": result.get("cited_chunks", len(result.get("citations", []))),
                            "context_available": result.get("context_available", False),
                            "target_language": result.get("target_language"),
                            "answer_style": result.get("answer_style", "auto"),
                            "document_type": result.get("document_type"),
                            "retrieval_mode": result.get("retrieval_mode", "unknown"),
                            "retrieval_warning": result.get("retrieval_warning"),
                            "grounding_verified": result.get("grounding_verified", False),
                            "citation_confidence": result.get("citation_confidence", "none"),
                            "citation_warning": result.get("citation_warning"),
                        }
                    )
                except Exception as exc:
                    st.error(f"Could not answer that yet: {friendly_error(exc)}")

        for turn in reversed(st.session_state.chat_history):
            with st.chat_message("user"):
                st.write(turn["question"])
            with st.chat_message("assistant"):
                st.write(turn["answer"])
                if turn.get("retrieved_chunks", 0):
                    render_pill("Mode", display_answer_style(turn.get("answer_style")), tone="amber")
                    render_pill("Type", display_document_type(turn.get("document_type")), tone="cyan")
                    render_pill("Search", display_retrieval_mode(turn.get("retrieval_mode")), tone="cyan")
                    render_pill("Retrieved", str(turn.get("retrieved_chunks", 0)), tone="cyan")
                    render_pill("Cited", str(turn.get("cited_chunks", 0)), tone="amber")
                else:
                    st.warning("No matching source was found for this question.")
                if turn.get("retrieval_warning"):
                    st.warning(turn["retrieval_warning"])
                if turn.get("citation_warning"):
                    st.warning(turn["citation_warning"])
                if turn["citations"]:
                    render_source_cards(turn["citations"], title="Cited sources", expanded=False)
                elif turn.get("retrieved_context"):
                    render_source_cards(
                        turn["retrieved_context"],
                        title="Retrieved context (not verified citations)",
                        expanded=False,
                    )

with summarize_tab:
    st.subheader("Document summaries")
    try:
        summary_documents = api_get("/documents")
    except Exception:
        summary_documents = []

    if not summary_documents:
        st.info("Upload a PDF first, then come back here to summarize it.")
    else:
        summary_document_labels = {
            f"{document['filename']} ({document['document_id'][:8]})": document[
                "document_id"
            ]
            for document in summary_documents
        }
        active_summary_document_id = current_document_id(summary_documents)
        summary_default_index = next(
            (
                index
                for index, document_id in enumerate(summary_document_labels.values())
                if document_id == active_summary_document_id
            ),
            0,
        )
        selected_summary_document = st.selectbox(
            "Document",
            options=list(summary_document_labels.keys()),
            index=summary_default_index,
        )
        summary_col_a, summary_col_b, summary_col_c = st.columns(3)
        with summary_col_a:
            summary_type = st.selectbox(
                "Summary type",
                options=["short", "detailed", "technical", "bilingual"],
            )
        with summary_col_b:
            summary_language_label = st.selectbox(
                "Summary language",
                options=list(languages.keys()),
            )
        with summary_col_c:
            summary_max_chunks = st.slider(
                "Source chunks",
                min_value=3,
                max_value=20,
                value=8,
            )

        if st.button("Generate summary", type="primary", use_container_width=True):
            payload = {
                "document_id": summary_document_labels[selected_summary_document],
                "summary_type": summary_type,
                "target_language": languages[summary_language_label],
                "max_chunks": summary_max_chunks,
                "translate_summary": True,
            }
            with st.spinner("Creating a cited summary..."):
                try:
                    result = api_post("/summarize", payload)
                    st.session_state.last_summary = result
                except Exception as exc:
                    st.error(f"Could not create the summary: {friendly_error(exc)}")

    if "last_summary" in st.session_state:
        summary = st.session_state.last_summary
        st.markdown(summary["summary"])
        st.caption(
            f"{summary['summary_type']} summary | "
            f"{summary['chunks_used']} sources used"
        )
        if summary["citations"]:
            render_source_cards(summary["citations"], title="Sources used", expanded=True)

with translate_tab:
    st.subheader("Translation")
    try:
        translation_methods = api_get("/translation/methods")
    except Exception:
        translation_methods = [
            {
                "id": "google",
                "display_name": "Google Translate",
                "provider": "deep-translator",
                "notes": "Default translation method.",
            }
        ]
    method_labels = {
        f"{method['display_name']} ({method['id']})": method["id"]
        for method in translation_methods
    }
    translate_col_a, translate_col_b = st.columns(2)
    with translate_col_a:
        source_language = st.selectbox(
            "Source language",
            options=["auto"] + list(languages.values()),
            index=0,
        )
    with translate_col_b:
        target_language_label = st.selectbox(
            "Target language",
            options=list(languages.keys()),
            index=1 if len(languages) > 1 else 0,
        )
    selected_method_label = st.selectbox(
        "Translation method",
        options=list(method_labels.keys()),
        index=0,
    )
    compare_method_labels = st.multiselect(
        "Methods to compare",
        options=list(method_labels.keys()),
        default=[selected_method_label],
    )
    text_to_translate = st.text_area("Text", height=180)
    translate_action_col, compare_action_col = st.columns(2)
    with translate_action_col:
        translate_clicked = st.button("Translate", type="primary", use_container_width=True)
    with compare_action_col:
        compare_clicked = st.button("Compare methods", use_container_width=True)

    if translate_clicked and text_to_translate.strip():
        with st.spinner("Translating..."):
            try:
                result = api_post(
                    "/translate",
                    {
                        "text": text_to_translate.strip(),
                        "source_language": source_language,
                        "target_language": languages[target_language_label],
                        "method": method_labels[selected_method_label],
                    },
                )
                st.text_area("Translated text", value=result["translated_text"], height=180)
                st.caption(
                    f"{result['method']} | {result['provider']} | "
                    f"{result.get('quality_notes') or ''}"
                )
            except Exception as exc:
                st.error(f"Translation failed: {exc}")

    if compare_clicked and text_to_translate.strip():
        with st.spinner("Comparing translation methods..."):
            try:
                result = api_post(
                    "/translate/compare",
                    {
                        "text": text_to_translate.strip(),
                        "source_language": source_language,
                        "target_language": languages[target_language_label],
                        "methods": [
                            method_labels[label]
                            for label in compare_method_labels
                        ],
                    },
                )
                if not result["results"]:
                    st.info("No translation method returned a result.")
                for item in result["results"]:
                    with st.expander(f"{item['method']} - {item['provider']}", expanded=True):
                        st.write(item["translated_text"])
                        st.caption(item.get("quality_notes") or "")
            except Exception as exc:
                st.error(f"Translation comparison failed: {exc}")

with embeddings_tab:
    st.subheader("Embedding model comparison")
    try:
        models = api_get("/embeddings/models")
    except Exception:
        models = []

    if models:
        st.caption("Configured multilingual embedding models")
        for model in models:
            with st.expander(f"{model['display_name']} - {model['id']}"):
                st.write(model["model_name"])
                st.caption(
                    f"Strategy: {model['strategy']} | Dimension: {model['dimension']}"
                )
                if model.get("recommended_for"):
                    st.write(model["recommended_for"])
                if model.get("notes"):
                    st.caption(model["notes"])
    else:
        st.warning("Embedding model configuration is unavailable.")

    model_labels = {
        f"{model['display_name']} ({model['id']})": model["id"]
        for model in models
    }
    default_model_labels = list(model_labels.keys())[:1]
    selected_model_labels = st.multiselect(
        "Models to compare",
        options=list(model_labels.keys()),
        default=default_model_labels,
    )
    compare_query = st.text_area(
        "Query",
        height=80,
        placeholder="Example: What is the main contribution of the paper?",
    )
    positive_text = st.text_area(
        "Relevant passage",
        height=120,
        placeholder="Paste the passage that should rank highest.",
    )
    negative_texts_raw = st.text_area(
        "Distractor passages",
        height=140,
        placeholder="Paste one unrelated passage per line.",
    )
    if st.button("Compare embeddings", type="primary", use_container_width=True):
        if not compare_query.strip() or not positive_text.strip():
            st.warning("Add a query and relevant passage first.")
        else:
            payload = {
                "query": compare_query.strip(),
                "positive_text": positive_text.strip(),
                "negative_texts": [
                    line.strip()
                    for line in negative_texts_raw.splitlines()
                    if line.strip()
                ],
                "model_ids": [
                    model_labels[label]
                    for label in selected_model_labels
                ],
            }
            with st.spinner("Comparing embedding similarities..."):
                try:
                    result = api_post("/embeddings/compare", payload)
                    for comparison in result["comparisons"]:
                        with st.expander(
                            f"{comparison['model_id']} - positive rank {comparison['positive_rank']}",
                            expanded=True,
                        ):
                            st.caption(
                                f"{comparison['model_name']} | {comparison['strategy']}"
                            )
                            for score in comparison["scores"]:
                                st.write(
                                    f"**{score['label']}** - {score['score']:.4f}"
                                )
                                st.caption(score["text"])
                except Exception as exc:
                    st.error(f"Embedding comparison failed: {exc}")

with language_qa_tab:
    st.subheader("Language quality evaluation")
    st.caption(
        "Use this as the manual QA checklist for multilingual translation, RAG retrieval, "
        "chunking, answer style, and citation integrity."
    )

    try:
        quality_report = api_get("/evaluation/language-quality")
    except Exception as exc:
        quality_report = None
        st.error(f"Could not load language QA report: {friendly_error(exc)}")

    if quality_report:
        metric_a, metric_b, metric_c = st.columns(3)
        metric_a.metric("Priority languages", len(quality_report["priority_languages"]))
        metric_b.metric("Evaluation cases", len(quality_report["cases"]))
        metric_c.metric("Readiness", f"{quality_report['readiness_score'] * 100:.0f}%")

        if quality_report["missing_items"]:
            st.warning("Some language QA requirements still need attention.")
            for item in quality_report["missing_items"]:
                st.caption(item)
        else:
            st.success("Priority language readiness checks passed.")

        st.markdown("### Priority language matrix")
        language_rows = [
            {
                "Code": language["code"],
                "Language": language["name"],
                "Family": language["family"],
                "Direction": language["script_direction"],
                "Tokenizer": language["tokenizer_strategy"],
                "Google": "yes" if language["google_translation"] else "no",
                "NLLB": "yes" if language["nllb_translation"] else "no",
                "Embeddings": "yes" if language["embedding_supported"] else "no",
            }
            for language in quality_report["priority_languages"]
        ]
        st.table(language_rows)

        with st.expander("Why these languages?", expanded=False):
            for language in quality_report["priority_languages"]:
                st.markdown(f"**{language['name']} ({language['code']})**")
                st.caption(language["priority_reason"])

        st.markdown("### Evaluation cases")
        categories = sorted({case["category"] for case in quality_report["cases"]})
        selected_category = st.selectbox(
            "Filter by category",
            options=["all"] + categories,
            index=0,
        )
        visible_cases = [
            case
            for case in quality_report["cases"]
            if selected_category == "all" or case["category"] == selected_category
        ]

        for case in visible_cases:
            with st.expander(f"{case['category']} - {case['id']}", expanded=False):
                case_col_a, case_col_b = st.columns(2)
                with case_col_a:
                    render_pill("Source", case["source_language"], tone="cyan")
                    render_pill("Target", case["target_language"], tone="amber")
                with case_col_b:
                    render_pill("Expected", ", ".join(case["expected_terms"]), tone="cyan")
                st.markdown("**Prompt**")
                st.write(case["prompt"])
                st.markdown("**Test text**")
                st.code(case["source_text"], language="text")
                if case.get("notes"):
                    st.caption(case["notes"])

        with st.expander("How to use this QA tab", expanded=False):
            st.markdown(
                """
                1. Pick one evaluation case.
                2. Run it in Ask papers, Translate text, or Embeddings.
                3. Check whether the answer keeps technical terms, retrieves relevant passages, and preserves citations.
                4. Record weak languages for later improvement with better prompts, translation method choice, or tokenizer tuning.
                """
            )

        if quality_report.get("notes"):
            with st.expander("Evaluation notes", expanded=False):
                for note in quality_report["notes"]:
                    st.caption(note)
