from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from backend.app.services.document_chunks import DocumentChunkingService
from backend.app.services.documents import DocumentService
from backend.app.services.languages import LanguageRegistry
from backend.app.services.pdf_loader import PageText


def make_settings(tmp_path):
    upload_dir = tmp_path / "uploads"
    extracted_text_dir = tmp_path / "extracted"
    chunk_dir = extracted_text_dir / "chunks"
    upload_dir.mkdir()
    extracted_text_dir.mkdir()
    chunk_dir.mkdir()
    return SimpleNamespace(
        upload_dir=upload_dir,
        extracted_text_dir=extracted_text_dir,
        chunk_dir=chunk_dir,
        document_index_path=tmp_path / "documents.json",
        language_config_path=Path("config/languages.json"),
        max_pdf_size_mb=1,
        chunk_size=60,
        chunk_overlap=10,
    )


def test_document_chunking_service_persists_language_aware_chunks(tmp_path, monkeypatch):
    settings = make_settings(tmp_path)
    document_service = DocumentService(settings)
    registry = LanguageRegistry(settings.language_config_path)
    chunking_service = DocumentChunkingService(settings, document_service, registry)

    monkeypatch.setattr(
        "backend.app.services.documents.extract_pdf_pages",
        lambda path, include_empty: [
            PageText(page_number=1, text="This paper proposes a multilingual method. " * 5),
            PageText(page_number=2, text="यह शोध पत्र महत्वपूर्ण है। " * 5),
        ],
    )
    upload = document_service.upload_pdf("paper.pdf", BytesIO(b"%PDF fake content"))

    result = chunking_service.chunk_document(upload.document_id)

    assert result.chunk_count > 0
    assert {"en", "hi"}.issubset(set(result.detected_languages))
    assert (settings.chunk_dir / f"{upload.document_id}.json").exists()

    updated = document_service.get_document(upload.document_id)
    assert updated.chunks_ready is True
    assert updated.chunk_count == result.chunk_count
