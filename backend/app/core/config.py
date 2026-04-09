from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    app_name: str = "LITIGIA"
    debug: bool = False

    # Claude API (only external dependency)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_model_deep: str = "claude-opus-4-20250514"

    # Embeddings — 100% local, no API needed
    embedding_model: str = "BAAI/bge-m3"

    # Vector store (ChromaDB — embedded, no server needed)
    collection_name: str = "jurisprudencia"

    # Data storage — SSD D: for heavy datasets
    data_root: Path = Path("D:/litigia-data")
    data_raw: Path = Path("D:/litigia-data/raw")
    data_clean: Path = Path("D:/litigia-data/clean")
    data_embeddings: Path = Path("D:/litigia-data/embeddings")
    data_logs: Path = Path("D:/litigia-data/logs")

    # Rate limiting — Anthropic API
    # Tier 1: 50 RPM but 30K input tokens/min and 8K output tokens/min
    # With ~4K input tokens per reader, safe throughput is ~7 req/min
    anthropic_rpm: int = 7  # effective safe rate given token limits
    anthropic_max_retries: int = 5  # more retries to survive token bursts

    # Pipeline
    saij_dataset: str = "marianbasti/jurisprudencia-Argentina-SAIJ"
    jurisgpt_dataset: str = "harpomaxx/jurisgpt"
    saij_min_text_length: int = 100
    jurisgpt_min_text_length: int = 100
    embedding_batch_size: int = 256
    chunk_max_chars: int = 4000

    def ensure_dirs(self) -> None:
        """Create all data directories if they don't exist."""
        for d in [self.data_root, self.data_raw, self.data_clean, self.data_embeddings, self.data_logs]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
