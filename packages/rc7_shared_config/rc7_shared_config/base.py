from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER = "replace_me"
WEAK_PASSWORDS = {"postgres", "minioadmin", PLACEHOLDER, ""}


class SharedSettings(BaseSettings):
    """Settings both services need, plus the production secret checks.

    Subclasses declare their own fields and extend ``production_errors`` to add
    checks for them.
    """

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

    gemini_api_key: str = PLACEHOLDER
    gemini_gen_model: str = "gemini-3.5-flash"
    gemini_embed_model: str = "gemini-embedding-2"
    gemini_embed_dim: int = 3072  # must match the vector(N) column
    gemini_timeout_seconds: int = 300

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

    def production_errors(self) -> list[str]:
        """Misconfigurations that must abort startup outside development."""
        errors: list[str] = []
        if self.gemini_api_key == PLACEHOLDER:
            errors.append("GEMINI_API_KEY must be set")
        if self.postgres_password in WEAK_PASSWORDS:
            errors.append("POSTGRES_PASSWORD must not use a default/weak value")
        if self.minio_root_password in WEAK_PASSWORDS:
            errors.append("MINIO_ROOT_PASSWORD must not use a default/weak value")
        return errors

    @model_validator(mode="after")
    def _reject_placeholder_secrets(self) -> "SharedSettings":
        if self.app_env == "development":
            return self
        errors = self.production_errors()
        if errors:
            raise ValueError(
                "Production configuration errors:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self
