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
