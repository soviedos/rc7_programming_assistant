from src.utils.logging import log


def test_log_includes_scope_and_message(capsys) -> None:
    log("worker", "mensaje de prueba")

    captured = capsys.readouterr()

    assert "[worker] mensaje de prueba" in captured.out
