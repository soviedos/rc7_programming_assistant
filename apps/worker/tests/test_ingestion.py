import pytest

from src.jobs.ingestion import run_worker_loop


def test_run_worker_loop_emits_startup_and_heartbeat(monkeypatch) -> None:
    log_messages: list[tuple[str, str]] = []
    sleep_calls = {"count": 0}

    def fake_log(scope: str, message: str) -> None:
        log_messages.append((scope, message))

    def fake_sleep(seconds: int) -> None:
        sleep_calls["count"] += 1
        if sleep_calls["count"] >= 2:
            raise RuntimeError("stop-loop")

    monkeypatch.setattr("src.jobs.ingestion.log", fake_log)
    monkeypatch.setattr("src.jobs.ingestion.sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="stop-loop"):
        run_worker_loop()

    assert log_messages == [
        ("worker", "Worker RC7 iniciado. Esperando trabajos de ingesta..."),
        ("worker", "Heartbeat: worker activo."),
    ]
