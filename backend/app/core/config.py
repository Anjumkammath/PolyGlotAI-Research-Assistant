from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PolyGlotAI Research Assistant"
    app_env: str = "development"
    backend_cors_origins: str = (
        "http://localhost:8501,http://127.0.0.1:8501,"
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    upload_dir: Path = Path("storage/uploads")
    extracted_text_dir: Path = Path("storage/extracted")
    chunk_dir: Path = Path("storage/extracted/chunks")
    document_index_path: Path = Path("storage/documents.json")
    language_config_path: Path = Path("config/languages.json")
    language_quality_config_path: Path = Path("config/language_quality_evaluation.json")
    embedding_config_path: Path = Path("config/embedding_models.json")
    translation_methods_config_path: Path = Path("config/translation_methods.json")
    translation_language_codes_path: Path = Path("config/translation_language_codes.json")
    vector_db_dir: Path = Path("storage/vector_db")
    memory_db_path: Path = Path("storage/memory.sqlite3")
    max_pdf_size_mb: int = 25

    vector_db_provider: str = "qdrant"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_document_collection: str = "documents"
    qdrant_memory_collection: str = "memory"
    qdrant_vector_size: int = 384

    embedding_model: str = "multilingual-minilm"
    chunk_size: int = 900
    chunk_overlap: int = 180
    max_context_chunks: int = 5

    llm_provider: str = "fallback"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    default_answer_language: str = "en"
    default_translation_method: str = "google"
    nllb_model_name: str = "facebook/nllb-200-distilled-600M"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]

    def ensure_storage_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.extracted_text_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_dir.mkdir(parents=True, exist_ok=True)
        self.document_index_path.parent.mkdir(parents=True, exist_ok=True)
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)
        self.memory_db_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_storage_dirs()
    return settings
