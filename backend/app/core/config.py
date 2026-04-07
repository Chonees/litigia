from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    app_name: str = "LITIGIA"
    debug: bool = False

    # Claude API
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_embedding_model: str = "text-embedding-3-large"

    # OpenAI (for embeddings only)
    openai_api_key: str = ""

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "jurisprudencia"

    # Embedding dimensions (text-embedding-3-large)
    embedding_dimensions: int = 3072


settings = Settings()
