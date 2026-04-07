from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    app_name: str = "LITIGIA"
    debug: bool = False

    # Claude API
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # OpenAI (embeddings only)
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 3072

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "jurisprudencia"

    # Data storage — SSD D: for heavy datasets
    data_root: Path = Path("D:/litigia-data")
    data_raw: Path = Path("D:/litigia-data/raw")
    data_clean: Path = Path("D:/litigia-data/clean")
    data_embeddings: Path = Path("D:/litigia-data/embeddings")
    data_logs: Path = Path("D:/litigia-data/logs")

    # Pipeline
    saij_dataset: str = "marianbasti/jurisprudencia-Argentina-SAIJ"
    jurisgpt_dataset: str = "harpomaxx/jurisgpt"
    saij_min_text_length: int = 100
    jurisgpt_min_text_length: int = 100
    embedding_batch_size: int = 50
    qdrant_upsert_batch_size: int = 100
    chunk_max_chars: int = 4000

    def ensure_dirs(self) -> None:
        """Create all data directories if they don't exist."""
        for d in [self.data_root, self.data_raw, self.data_clean, self.data_embeddings, self.data_logs]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
