from datetime import UTC, datetime


def log(scope: str, message: str) -> None:
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    print(f"[{timestamp}] [{scope}] {message}", flush=True)
