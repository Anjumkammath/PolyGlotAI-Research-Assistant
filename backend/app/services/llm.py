import re

from backend.app.core.config import Settings
from backend.app.services.languages import language_name
from backend.app.services.text_cleanup import clean_pdf_text
from backend.app.services.vector_store import VectorSearchHit


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def answer(
        self,
        question: str,
        context_hits: list[VectorSearchHit],
        memory_messages: list[dict[str, str]],
        target_language: str,
        answer_style: str = "auto",
    ) -> str:
        provider = self.settings.llm_provider.lower().strip()
        if provider == "openai" and self.settings.openai_api_key:
            return self._answer_with_openai(
                question=question,
                context_hits=context_hits,
                memory_messages=memory_messages,
                target_language=target_language,
                answer_style=answer_style,
            )
        if provider == "ollama":
            return self._answer_with_ollama(
                question=question,
                context_hits=context_hits,
                memory_messages=memory_messages,
                target_language=target_language,
                answer_style=answer_style,
            )
        return self._fallback_answer(question, context_hits, answer_style=answer_style)

    def summarize(
        self,
        document_name: str,
        summary_type: str,
        context_hits: list[VectorSearchHit],
        target_language: str,
    ) -> str:
        provider = self.settings.llm_provider.lower().strip()
        messages = self._summary_messages(
            document_name=document_name,
            summary_type=summary_type,
            context_hits=context_hits,
            target_language=target_language,
        )
        if provider == "openai" and self.settings.openai_api_key:
            return self._complete_with_openai(messages)
        if provider == "ollama":
            return self._complete_with_ollama(messages)
        return self._fallback_summary(
            document_name=document_name,
            summary_type=summary_type,
            context_hits=context_hits,
        )

    def translate_text(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        provider = self.settings.llm_provider.lower().strip()
        target_name = language_name(target_language)
        source_name = "auto-detected language" if source_language == "auto" else language_name(source_language)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are PolyGlotAI Research Assistant's translation module. "
                    "Translate faithfully, preserve technical meaning, keep important "
                    "AI/NLP terms accurate, and do not add commentary unless needed "
                    "to preserve meaning."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Translate from {source_name} to {target_name}.\n\n"
                    f"Text:\n{text}"
                ),
            },
        ]
        if provider == "openai" and self.settings.openai_api_key:
            return self._complete_with_openai(messages)
        if provider == "ollama":
            return self._complete_with_ollama(messages)
        raise ValueError("LLM translation requires LLM_PROVIDER=openai or LLM_PROVIDER=ollama.")

    def _messages(
        self,
        question: str,
        context_hits: list[VectorSearchHit],
        memory_messages: list[dict[str, str]],
        target_language: str,
        answer_style: str,
    ) -> list[dict[str, str]]:
        context = "\n\n".join(
            (
                f"[C{index}] {hit.source_name}, page {hit.page}, "
                f"score {hit.score if hit.score is not None else 'n/a'}:\n"
                f"{_clean_pdf_text(hit.text)}"
            )
            for index, hit in enumerate(context_hits, start=1)
        )
        memory = "\n".join(
            f"{message['role']}: {message['content']}"
            for message in memory_messages[-6:]
        )
        answer_language = language_name(target_language)
        style_instruction = _answer_style_instruction(answer_style)

        system = (
            "You are PolyGlotAI Research Assistant, a multilingual research helper. "
            "Answer using only the provided retrieved research context. "
            "Do not use outside knowledge for document-specific claims. "
            "If the context is insufficient, say exactly what is missing and suggest a better question. "
            "Every factual claim from the document must include inline source citations such as [C1] or [C2]. "
            "Use only citation IDs that appear in the retrieved context. "
            "Do not invent citations, page numbers, datasets, results, methods, employers, skills, or claims. "
            "If the uploaded file is a resume/CV, study note, report, or syllabus instead of a research paper, say that clearly. "
            f"{style_instruction} "
            f"Write the final answer in {answer_language}."
        )
        user = (
            f"Recent conversation:\n{memory or 'No previous conversation.'}\n\n"
            f"Retrieved research context:\n{context or 'No context retrieved.'}\n\n"
            f"Answer style: {answer_style}\n\n"
            f"Question: {question}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _answer_with_openai(
        self,
        question: str,
        context_hits: list[VectorSearchHit],
        memory_messages: list[dict[str, str]],
        target_language: str,
        answer_style: str,
    ) -> str:
        answer = self._complete_with_openai(
            self._messages(
                question=question,
                context_hits=context_hits,
                memory_messages=memory_messages,
                target_language=target_language,
                answer_style=answer_style,
            ),
        )
        return _guard_citations(answer, len(context_hits))

    def _answer_with_ollama(
        self,
        question: str,
        context_hits: list[VectorSearchHit],
        memory_messages: list[dict[str, str]],
        target_language: str,
        answer_style: str,
    ) -> str:
        answer = self._complete_with_ollama(
            self._messages(
                question=question,
                context_hits=context_hits,
                memory_messages=memory_messages,
                target_language=target_language,
                answer_style=answer_style,
            )
        )
        return _guard_citations(answer, len(context_hits))

    def _complete_with_openai(self, messages: list[dict[str, str]]) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.settings.openai_api_key)
        response = client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def _complete_with_ollama(self, messages: list[dict[str, str]]) -> str:
        import requests

        response = requests.post(
            f"{self.settings.ollama_base_url.rstrip('/')}/api/chat",
            json={
                "model": self.settings.ollama_model,
                "messages": messages,
                "stream": False,
            },
            timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("message", {}).get("content", "")

    def _summary_messages(
        self,
        document_name: str,
        summary_type: str,
        context_hits: list[VectorSearchHit],
        target_language: str,
    ) -> list[dict[str, str]]:
        context = "\n\n".join(
            f"[C{index}] {hit.source_name}, page {hit.page}:\n{hit.text}"
            for index, hit in enumerate(context_hits, start=1)
        )
        answer_language = language_name(target_language)
        summary_instruction = _summary_instruction(summary_type)
        system = (
            "You are PolyGlotAI Research Assistant. Summarize only from the provided "
            "source passages. Do not invent methods, datasets, results, or limitations. "
            "Cite source blocks inline using [C1], [C2], and so on. "
            f"Write the summary in {answer_language}."
        )
        user = (
            f"Document: {document_name}\n"
            f"Summary type: {summary_type}\n"
            f"Instructions: {summary_instruction}\n\n"
            f"Source passages:\n{context or 'No source passages available.'}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _fallback_answer(
        self,
        question: str,
        context_hits: list[VectorSearchHit],
        answer_style: str = "auto",
    ) -> str:
        if not context_hits:
            return (
                "I could not find relevant passages yet. Upload one or more PDFs, "
                "then ask a question about their content."
            )

        skills_answer = _skills_answer(question, context_hits)
        if skills_answer:
            return skills_answer

        overview_answer = _document_overview_answer(question, context_hits)
        if overview_answer:
            return overview_answer

        concise_question = re.search(
            r"\b(what\s+is|what\s+are|define|meaning\s+of)\b",
            question.lower(),
        )
        max_points = 1 if concise_question else 3

        return _fallback_general_answer(
            question=question,
            context_hits=context_hits[:max_points],
            answer_style=answer_style,
        )

    def _fallback_summary(
        self,
        document_name: str,
        summary_type: str,
        context_hits: list[VectorSearchHit],
    ) -> str:
        if not context_hits:
            return "I could not summarize this document because no readable chunks are available."

        profile_summary = _profile_summary(document_name, context_hits)
        if profile_summary:
            return profile_summary

        lines = [f"Summary for {document_name}:", ""]
        for index, hit in enumerate(context_hits[:6], start=1):
            point = _best_source_sentence(hit.text, document_name, limit=240)
            lines.append(f"- {point} [C{index}]")
        return "\n".join(lines)


def _summary_instruction(summary_type: str) -> str:
    instructions = {
        "short": "Produce 5-8 concise bullet points covering objective, method, findings, and limitations when present.",
        "detailed": "Produce a structured section-wise summary with enough detail for a student reading the paper.",
        "technical": "Focus on problem, model/method, dataset, metrics, results, assumptions, and limitations.",
        "bilingual": "Produce a clear summary in the target language while preserving important technical terms in English where useful.",
    }
    return instructions.get(summary_type, instructions["short"])


def _answer_style_instruction(answer_style: str) -> str:
    instructions = {
        "short": "Keep the answer concise: 1-3 bullets or a short paragraph.",
        "detailed": "Give a clear explained answer with the main point, supporting details, and caveats when present.",
        "beginner": "Explain in simple language, define technical terms briefly, and avoid unexplained jargon.",
        "technical": "Use a technical research-oriented style with methods, data, metrics, assumptions, and limitations when present.",
        "auto": "Choose a natural level of detail for the question; overview questions should be explained, definition questions should be concise.",
    }
    return instructions.get(answer_style, instructions["auto"])


def _guard_citations(answer: str, citation_count: int) -> str:
    if citation_count <= 0:
        return answer.strip()

    allowed = {str(index) for index in range(1, citation_count + 1)}

    def replace(match: re.Match[str]) -> str:
        citation_number = match.group(1)
        if citation_number in allowed:
            return match.group(0)
        return ""

    guarded = re.sub(r"\[C(\d+)\]", replace, answer).strip()
    return guarded


def _fallback_general_answer(
    question: str,
    context_hits: list[VectorSearchHit],
    answer_style: str,
) -> str:
    points = [
        _best_source_sentence(hit.text, question, limit=300 if answer_style != "short" else 220)
        for hit in context_hits
    ]

    if answer_style == "beginner":
        lines = ["Simple explanation:", ""]
        for index, point in enumerate(points, start=1):
            lines.append(f"- {point} [C{index}]")
        lines.append("")
        lines.append("The citations show exactly where this information came from in the uploaded PDF.")
        return "\n".join(lines)

    if answer_style == "technical":
        lines = ["Technical answer:", ""]
        for index, point in enumerate(points, start=1):
            lines.append(f"- Source-backed detail {index}: {point} [C{index}]")
        return "\n".join(lines)

    if answer_style == "detailed":
        lines = ["Detailed answer:", ""]
        for index, point in enumerate(points, start=1):
            lines.append(f"- {point} [C{index}]")
        lines.append("")
        lines.append("This answer is limited to the retrieved source passages above.")
        return "\n".join(lines)

    heading = "Short answer:" if answer_style == "short" else "Based on the selected PDF:"
    lines = [heading, ""]
    for index, point in enumerate(points, start=1):
        lines.append(f"- {point} [C{index}]")
    return "\n".join(lines)


def _clean_excerpt(text: str, limit: int) -> str:
    normalized = _clean_pdf_text(text)
    normalized = re.sub(r"([A-Za-z])-\s+([a-z])", r"\1\2", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def _best_source_sentence(text: str, query: str, limit: int) -> str:
    normalized = _clean_pdf_text(text)
    normalized = re.sub(r"([A-Za-z])-\s+([a-z])", r"\1\2", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    sentences = [
        sentence.strip(" -")
        for sentence in re.split(r"(?<=[.!?])\s+|\s+-\s+", normalized)
        if len(sentence.strip()) > 24
    ]
    if not sentences:
        return _clean_excerpt(text, limit=limit)

    terms = {
        term
        for term in re.findall(r"[\w]+", query.lower(), flags=re.UNICODE)
        if len(term) > 2
    }
    subject_terms = terms - {"what", "where", "when", "which", "define", "explain"}

    def score(sentence: str) -> int:
        lowered = sentence.lower()
        value = sum(1 for term in terms if term in lowered)
        if sentence.rstrip().endswith("?"):
            value -= 3
        if subject_terms and any(term in lowered for term in subject_terms):
            if re.search(r"\b(is|are|means|refers|defines)\b", lowered):
                value += 2
        return value

    ranked = sorted(
        sentences,
        key=score,
        reverse=True,
    )
    chosen = ranked[0]
    if len(chosen) <= limit:
        return chosen
    return f"{chosen[:limit].rstrip()}..."


def _profile_summary(document_name: str, context_hits: list[VectorSearchHit]) -> str | None:
    ordered_hits = _document_order_hits(context_hits)
    combined = _combine_hit_text(ordered_hits[:8])
    combined = re.sub(r"([A-Za-z])-\s+([a-z])", r"\1\2", combined)
    combined = re.sub(r"\bT\s+ools\b", "Tools", combined)
    combined = re.sub(r"\s+", " ", combined).strip()
    profile_markers = [
        "professional summary",
        "technical skills",
        "work experience",
        "projects",
        "education",
    ]
    if sum(1 for marker in profile_markers if marker in combined.lower()) < 2:
        return None

    name_match = re.search(
        r"^([A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*){1,4})\s+[A-Za-z0-9._%+-]+@",
        combined,
    )
    name = name_match.group(1) if name_match else "the candidate"
    summary = _section_after(combined, "Professional Summary", ["Technical Skills", "Work Experience"], 320)
    skills = _section_after(combined, "Technical Skills", ["Work Experience"], 420)
    experience = _section_after(combined, "Work Experience", ["Projects", "Education"], 360)
    projects = _section_after(combined, "Projects", ["Education", "Certifications"], 360)

    citation_count = max(1, len(context_hits))

    def citation(index: int) -> str:
        return f"[C{min(index, citation_count)}]"

    lines = [f"Overview of {document_name}:", ""]
    lines.append(f"- This uploaded document is a resume/CV for {name}, not a research paper. {citation(1)}")
    if summary:
        lines.append(f"- Profile: {summary} {citation(1)}")
    if skills:
        lines.append(f"- Skills highlighted: {skills} {citation(1)}")
    if experience:
        lines.append(f"- Experience: {experience} {citation(2)}")
    if projects:
        lines.append(f"- Projects: {projects} {citation(3)}")
    return "\n".join(lines)


def _document_overview_answer(
    question: str,
    context_hits: list[VectorSearchHit],
) -> str | None:
    if not _is_document_overview_question(question) or not context_hits:
        return None

    document_name = context_hits[0].source_name or "the selected PDF"
    profile_summary = _profile_summary(document_name, context_hits)
    if profile_summary:
        return profile_summary

    lines = [f"Overview of {document_name}:", ""]
    lines.append(
        "- This document appears to focus on "
        f"{_best_source_sentence(context_hits[0].text, 'main topic objective abstract introduction', limit=260)} [C1]"
    )

    for index, hit in enumerate(context_hits[1:3], start=2):
        point = _best_source_sentence(hit.text, "explain discuss method findings contribution", limit=240)
        lines.append(f"- It also explains or discusses: {point} [C{index}]")

    return "\n".join(lines)


def _is_document_overview_question(question: str) -> bool:
    normalized = question.lower().strip()
    if re.search(r"\b(summary|summarize|overview|main idea)\b", normalized):
        return True
    if re.search(r"\bwhat\s+is\s+(this|it)\s+about\b", normalized):
        return True
    if re.search(r"\bwhat\s+does\s+(this|it)\s+(explain|discuss|cover)\b", normalized):
        return True
    if re.search(
        r"\b(what|tell\s+me).*\b(paper|document|pdf|file|resume|cv)\b.*\b(about|explain|discuss|cover)\b",
        normalized,
    ):
        return True
    if re.search(
        r"\b(paper|document|pdf|file|resume|cv)\b.*\b(about|explain|discuss|cover)\b",
        normalized,
    ):
        return True
    return False


def _skills_answer(question: str, context_hits: list[VectorSearchHit]) -> str | None:
    if "skill" not in question.lower():
        return None

    combined = _combine_hit_text(_document_order_hits(context_hits)[:5])
    combined = re.sub(r"([A-Za-z])-\s+([a-z])", r"\1\2", combined)
    combined = re.sub(r"\bT\s+ools\b", "Tools", combined)
    combined = re.sub(r"\s+", " ", combined).strip()
    skills = _section_after(combined, "Technical Skills", ["Work Experience", "Projects"], 520)
    if not skills:
        skills = _best_source_sentence(combined, "skills", limit=360)
    if not skills:
        return None

    return (
        "Based on the selected PDF:\n\n"
        f"- The document mentions these skills: {skills} [C1]"
    )


def _document_order_hits(context_hits: list[VectorSearchHit]) -> list[VectorSearchHit]:
    return sorted(
        context_hits,
        key=lambda hit: (
            hit.page_start if hit.page_start is not None else hit.page,
            _chunk_number(hit.chunk_id),
        ),
    )


def _chunk_number(chunk_id: str) -> int:
    try:
        return int(chunk_id.rsplit(":", maxsplit=1)[-1])
    except ValueError:
        return 0


def _combine_hit_text(context_hits: list[VectorSearchHit]) -> str:
    combined = ""
    for hit in context_hits:
        text = _clean_pdf_text(hit.text)
        if not text:
            continue
        if not combined:
            combined = text
            continue
        combined = _append_without_overlap(combined, text)
    return re.sub(r"\s+", " ", combined).strip()


def _append_without_overlap(existing: str, text: str) -> str:
    max_overlap = min(len(existing), len(text), 600)
    for size in range(max_overlap, 39, -1):
        if existing[-size:] == text[:size]:
            return f"{existing}{text[size:]}"
    return f"{existing} {text}"


def _section_after(
    text: str,
    heading: str,
    stop_headings: list[str],
    limit: int,
) -> str:
    pattern = re.compile(re.escape(heading))
    match = pattern.search(text)
    if not match:
        return ""

    start = match.end()
    end = len(text)
    for stop_heading in stop_headings:
        stop_match = re.search(re.escape(stop_heading), text[start:])
        if stop_match:
            end = min(end, start + stop_match.start())

    section = text[start:end].strip(" :-")
    section = re.sub(r"\s+", " ", section)
    if len(section) <= limit:
        return section
    return f"{_truncate_at_word(section, limit)}..."


def _truncate_at_word(text: str, limit: int) -> str:
    truncated = text[:limit].rsplit(" ", maxsplit=1)[0]
    return truncated.rstrip(" ,;:-") or text[:limit].rstrip()


def _clean_pdf_text(text: str) -> str:
    return clean_pdf_text(text)
