from __future__ import annotations

from datetime import UTC, datetime
from io import BufferedIOBase
import json
from pathlib import Path
import re
from uuid import uuid4

from backend.app.core.config import Settings
from backend.app.models.schemas import (
    DocumentDetail,
    DocumentSummary,
    DocumentUploadResponse,
    PagePreview,
)
from backend.app.services.pdf_loader import PageText, extract_pdf_pages


class DocumentServiceError(Exception):
    status_code = 400


class UnsupportedDocumentError(DocumentServiceError):
    status_code = 400


class DocumentTooLargeError(DocumentServiceError):
    status_code = 413


class DocumentNotFoundError(DocumentServiceError):
    status_code = 404


class DocumentExtractionError(DocumentServiceError):
    status_code = 422


class DocumentService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.index_path = settings.document_index_path
        self.upload_dir = settings.upload_dir
        self.extracted_text_dir = settings.extracted_text_dir
        self.max_pdf_size_bytes = settings.max_pdf_size_mb * 1024 * 1024

    def upload_pdf(self, filename: str, stream: BufferedIOBase) -> DocumentUploadResponse:
        original_filename = self._safe_display_filename(filename)
        if not original_filename.lower().endswith(".pdf"):
            raise UnsupportedDocumentError("Only PDF files are supported in this phase.")

        document_id = str(uuid4())
        stored_filename = f"{document_id}.pdf"
        stored_path = self.upload_dir / stored_filename

        self._save_stream_with_limit(stream=stream, destination=stored_path)
        pages = self._extract_pages(stored_path)
        self._persist_extracted_text(document_id=document_id, pages=pages)

        now = self._utc_now()
        detail = DocumentDetail(
            document_id=document_id,
            filename=original_filename,
            stored_filename=stored_filename,
            total_pages=len(pages),
            pages_with_text=sum(1 for page in pages if page.text.strip()),
            total_characters=sum(page.character_count for page in pages),
            extraction_status=self._extraction_status(pages),
            indexed=False,
            created_at=now,
            updated_at=now,
            page_previews=self._build_page_previews(pages),
        )
        self._upsert_document(detail)

        message = "PDF uploaded and text extracted successfully."
        if detail.extraction_status == "no_text":
            message = (
                "PDF uploaded, but no selectable text was found. "
                "Scanned PDFs will need OCR in a later phase."
            )

        return DocumentUploadResponse(**detail.model_dump(), message=message)

    def list_documents(self) -> list[DocumentSummary]:
        documents = [
            DocumentSummary(**document)
            for document in self._load_index().values()
        ]
        return sorted(documents, key=lambda item: item.created_at, reverse=True)

    def get_document(self, document_id: str) -> DocumentDetail:
        data = self._load_index().get(document_id)
        if data is None:
            raise DocumentNotFoundError("Document not found.")
        return DocumentDetail(**data)

    def mark_indexed(self, document_id: str) -> None:
        index = self._load_index()
        data = index.get(document_id)
        if data is None:
            raise DocumentNotFoundError("Document not found.")
        data["indexed"] = True
        data["updated_at"] = self._utc_now()
        self._save_index(index)

    def mark_chunked(
        self,
        document_id: str,
        chunk_count: int,
        detected_languages: list[str],
    ) -> None:
        index = self._load_index()
        data = index.get(document_id)
        if data is None:
            raise DocumentNotFoundError("Document not found.")
        data["chunks_ready"] = True
        data["chunk_count"] = chunk_count
        data["detected_languages"] = detected_languages
        data["updated_at"] = self._utc_now()
        self._save_index(index)

    def pdf_path(self, document_id: str) -> Path:
        detail = self.get_document(document_id)
        return self.upload_dir / detail.stored_filename

    def extracted_pages(self, document_id: str) -> list[PageText]:
        self.get_document(document_id)
        path = self.extracted_text_dir / f"{document_id}.json"
        if not path.exists():
            raise DocumentNotFoundError("Extracted text for this document was not found.")

        payload = json.loads(path.read_text(encoding="utf-8"))
        pages = payload.get("pages", [])
        return [
            PageText(
                page_number=int(page["page_number"]),
                text=str(page.get("text", "")),
            )
            for page in pages
        ]

    def _extract_pages(self, stored_path: Path) -> list[PageText]:
        try:
            pages = extract_pdf_pages(stored_path, include_empty=True)
        except Exception as exc:
            raise DocumentExtractionError(f"Could not extract text from PDF: {exc}") from exc

        if not pages:
            raise DocumentExtractionError("The PDF did not contain any readable pages.")
        return pages

    def _save_stream_with_limit(self, stream: BufferedIOBase, destination: Path) -> None:
        total_bytes = 0
        chunk_size = 1024 * 1024

        try:
            stream.seek(0)
        except Exception:
            pass

        with destination.open("wb") as output:
            while True:
                chunk = stream.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > self.max_pdf_size_bytes:
                    output.close()
                    destination.unlink(missing_ok=True)
                    raise DocumentTooLargeError(
                        f"PDF is larger than the {self.settings.max_pdf_size_mb} MB limit."
                    )
                output.write(chunk)

        if total_bytes == 0:
            destination.unlink(missing_ok=True)
            raise UnsupportedDocumentError("Uploaded file is empty.")

    def _persist_extracted_text(self, document_id: str, pages: list[PageText]) -> None:
        payload = {
            "document_id": document_id,
            "pages": [
                {
                    "page_number": page.page_number,
                    "character_count": page.character_count,
                    "text": page.text,
                }
                for page in pages
            ],
        }
        path = self.extracted_text_dir / f"{document_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_page_previews(self, pages: list[PageText]) -> list[PagePreview]:
        return [
            PagePreview(
                page_number=page.page_number,
                character_count=page.character_count,
                has_text=bool(page.text.strip()),
                preview=self._preview_text(page.text),
            )
            for page in pages
        ]

    def _upsert_document(self, detail: DocumentDetail) -> None:
        index = self._load_index()
        index[detail.document_id] = detail.model_dump()
        self._save_index(index)

    def _load_index(self) -> dict[str, dict]:
        if not self.index_path.exists():
            return {}

        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

        documents = payload.get("documents", {})
        if not isinstance(documents, dict):
            return {}
        return documents

    def _save_index(self, documents: dict[str, dict]) -> None:
        payload = {"documents": documents}
        self.index_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _safe_display_filename(filename: str) -> str:
        safe_name = Path(filename or "document.pdf").name
        safe_name = re.sub(r"\s+", " ", safe_name).strip()
        return safe_name or "document.pdf"

    @staticmethod
    def _preview_text(text: str, limit: int = 700) -> str:
        normalized = re.sub(r"\s+", " ", text).strip()
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[:limit].rstrip()}..."

    @staticmethod
    def _extraction_status(pages: list[PageText]) -> str:
        return "ready" if any(page.text.strip() for page in pages) else "no_text"

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(UTC).isoformat()
