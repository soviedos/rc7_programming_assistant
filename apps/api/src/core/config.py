from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER = "replace_me"
_WEAK_PASSWORDS = {"postgres", "minioadmin", _PLACEHOLDER, ""}


class Settings(BaseSettings):
    project_name: str = "RC7 Programming Assistant API"
    app_env: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    bootstrap_admin_name: str = "Administrador RC7"
    session_cookie_name: str = "rc7_session"
    session_ttl_minutes: int = 720
    jwt_secret: str = _PLACEHOLDER
    jwt_algorithm: str = "HS256"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "rc7_assistant"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    redis_host: str = "redis"
    redis_port: int = 6379
    minio_endpoint: str = "http://minio:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket_manuals: str = "rc7-manuals"
    gemini_api_key: str = _PLACEHOLDER
    gemini_timeout_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _reject_placeholder_secrets(self) -> "Settings":
        if self.app_env == "development":
            return self
        errors: list[str] = []
        if self.jwt_secret == _PLACEHOLDER:
            errors.append("JWT_SECRET must be set to a secure value")
        if self.gemini_api_key == _PLACEHOLDER:
            errors.append("GEMINI_API_KEY must be set")
        if self.postgres_password in _WEAK_PASSWORDS:
            errors.append("POSTGRES_PASSWORD must not use a default/weak value")
        if self.minio_root_password in _WEAK_PASSWORDS:
            errors.append("MINIO_ROOT_PASSWORD must not use a default/weak value")
        if self.bootstrap_admin_password in _WEAK_PASSWORDS:
            errors.append("BOOTSTRAP_ADMIN_PASSWORD must not be empty or a default value")
        if any("localhost" in o or "127.0.0.1" in o for o in self.cors_origins):
            errors.append("CORS_ORIGINS must not contain localhost in production")
        if errors:
            raise ValueError(
                "Production configuration errors:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self

    @property
    def sqlalchemy_database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def session_cookie_secure(self) -> bool:
        return self.app_env.lower() not in {"development", "local", "test"}


settings = Settings()
