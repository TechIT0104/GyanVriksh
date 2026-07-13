"""Application settings loaded from environment variables (.env)."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    llm_fallback: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    # Preferred Ollama model. If it isn't installed, the code auto-picks the
    # first model returned by `ollama list` (see llm_service._resolve_ollama_model).
    ollama_model: str = "llama3:8b-instruct-q8_0"

    # Databases
    postgres_url: str = "postgresql://gyanvriksh:gyanvriksh123@localhost:5432/gyanvriksh"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "gyanvriksh123"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    redis_url: str = "redis://localhost:6379/0"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_raw_docs: str = "raw-documents"
    kafka_topic_ocr_complete: str = "ocr-complete"
    kafka_topic_entities_raw: str = "entities-raw"
    kafka_topic_entities_tagged: str = "entities-tagged"

    # Object storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_docs: str = "gyanvriksh-docs"
    minio_bucket_audio: str = "gyanvriksh-audio"

    # Auth
    jwt_secret: str = "dev-secret-change-me-minimum-32-characters!"
    jwt_expire_hours: int = 24

    # Models
    ner_model_path: str = "./models/ner_model"
    embedding_model: str = "BAAI/bge-m3"
    whisper_model: str = "large-v3"
    ner_backend: str = "gpt4o"  # "bert" or "gpt4o"
    # Embedding backend: "bge" = BGE-M3 hybrid dense+sparse, 1024-d (~2.2GB download).
    # "minilm" = all-MiniLM-L6-v2 dense-only, 384-d (~90MB) — lighter, works offline.
    embedding_backend: str = "minilm"  # "bge" or "minilm"

    @property
    def embedding_dim(self) -> int:
        return 1024 if self.embedding_backend == "bge" else 384

    # App
    environment: str = "development"
    log_level: str = "INFO"
    frontend_url: str = "http://localhost:5173"
    max_upload_size_mb: int = 100
    chunk_size: int = 512
    chunk_overlap: int = 80


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
