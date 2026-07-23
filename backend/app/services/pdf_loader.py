from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str

    @property
    def character_count(self) -> int:
        return len(self.text.strip())


def extract_pdf_pages(pdf_path: Path, include_empty: bool = False) -> list[PageText]:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    if reader.is_encrypted:
        raise ValueError("Password-protected PDFs are not supported yet.")

    pages: list[PageText] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if include_empty or text.strip():
            pages.append(PageText(page_number=index, text=text))
    return pages
