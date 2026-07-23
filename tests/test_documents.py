from io import BytesIO
from types import SimpleNamespace

import pytest

from backend.app.services.documents import (
    DocumentService,
    DocumentTooLargeError,
    UnsupportedDocumentError,
)
from backend.app.services.pdf_loader import PageText


def make_settings(tmp_path, max_pdf_size_mb=1):
    upload_dir = tmp_path / "uploads"
    extracted_text_dir = tmp_path / "extracted"
    upload_dir.mkdir()
    extracted_text_dir.mkdir()
    return SimpleNamespace(
        upload_dir=upload_dir,
        extracted_text_dir=extracted_text_dir,
        chunk_dir=tmp_path / "chunks",
        document_index_path=tmp_path / "documents.json",
        max_pdf_size_mb=max_pdf_size_mb,
    )


def test_upload_pdf_extracts_text_and_persists_metadata(tmp_path, monkeypatch):
    service = DocumentService(make_settings(tmp_path))

    monkeypatch.setattr(
        "backend.app.services.documents.extract_pdf_pages",
        lambda path, include_empty: [
            PageText(page_number=1, text="This is page one."),
            PageText(page_number=2, text=""),
            PageText(page_number=3, text="This is page three."),
        ],
    )

    result = service.upload_pdf("sample paper.pdf", BytesIO(b"%PDF fake content"))

    assert result.filename == "sample paper.pdf"
    assert result.total_pages == 3
    assert result.pages_with_text == 2
    assert result.extraction_status == "ready"
    assert len(result.page_previews) == 3
    assert service.index_path.exists()
    assert (service.extracted_text_dir / f"{result.document_id}.json").exists()

    stored = service.get_document(result.document_id)
    assert stored.document_id == result.document_id
    assert stored.page_previews[0].preview == "This is page one."


def test_upload_rejects_non_pdf(tmp_path):
    service = DocumentService(make_settings(tmp_path))

    with pytest.raises(UnsupportedDocumentError):
        service.upload_pdf("notes.txt", BytesIO(b"hello"))


def test_upload_rejects_large_pdf(tmp_path):
    service = DocumentService(make_settings(tmp_path, max_pdf_size_mb=0))

    with pytest.raises(DocumentTooLargeError):
        service.upload_pdf("paper.pdf", BytesIO(b"%PDF fake content"))
