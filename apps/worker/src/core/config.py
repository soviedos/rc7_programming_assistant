from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "rc7_assistant"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    minio_endpoint: str = "http://minio:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket_manuals: str = "rc7-manuals"
    worker_poll_interval_seconds: int = 5
    gemini_api_key: str = "replace_me"
    gemini_model: str = "gemini-2.0-flash"
    gemini_timeout_seconds: int = 8
    semantic_review_enabled: bool = True
    semantic_review_sample_rate: float = 0.1
    semantic_review_min_chars: int = 250
    semantic_review_max_chars: int = 2200
    semantic_review_autofix_enabled: bool = True
    semantic_review_merge_boundary_max: float = 0.6
    semantic_review_split_max_coherence: float = 0.65
    semantic_review_split_min_chars: int = 1800
    semantic_review_enabled_languages: str = "es,en"
    semantic_review_title_include_terms: str = ""
    semantic_review_cost_input_per_1k_tokens: float = 0.00025
    semantic_review_cost_output_per_1k_tokens: float = 0.00075
    semantic_review_estimated_output_tokens: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
