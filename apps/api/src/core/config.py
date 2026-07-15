from rc7_shared_config import (
    PLACEHOLDER,
    WEAK_PASSWORDS,
    SharedSettings,
    is_placeholder,
)


class Settings(SharedSettings):
    project_name: str = "RC7 Programming Assistant API"
    cors_origins: list[str] = ["http://localhost:3000"]
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    bootstrap_admin_name: str = "Administrador RC7"
    session_cookie_name: str = "rc7_session"
    session_ttl_minutes: int = 720
    jwt_secret: str = PLACEHOLDER
    jwt_algorithm: str = "HS256"
    enable_streaming: bool = True

    def production_errors(self) -> list[str]:
        errors = super().production_errors()
        if is_placeholder(self.jwt_secret):
            errors.append("JWT_SECRET must be set to a secure value")
        if self.bootstrap_admin_password in WEAK_PASSWORDS or is_placeholder(
            self.bootstrap_admin_password
        ):
            errors.append(
                "BOOTSTRAP_ADMIN_PASSWORD must not be empty or a default value"
            )
        if any("localhost" in o or "127.0.0.1" in o for o in self.cors_origins):
            errors.append("CORS_ORIGINS must not contain localhost in production")
        return errors

    @property
    def session_cookie_secure(self) -> bool:
        return self.app_env.lower() not in {"development", "local", "test"}


settings = Settings()
