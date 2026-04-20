from fastapi.testclient import TestClient


def test_root_route(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "RC7 Programming Assistant API",
        "docs": "/docs",
    }


def test_health_route(client: TestClient) -> None:
    response = client.get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_status_route(client: TestClient) -> None:
    response = client.get("/api/v1/admin/status")

    assert response.status_code == 200
    assert response.json() == {
        "manuals_indexed": 0,
        "active_users": 0,
        "pending_jobs": 0,
    }


def test_chat_generate_route_returns_placeholder_pac(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat/generate",
        json={
            "prompt": "Genera una rutina de pick and place",
            "robot_type": "VP-6242",
            "controller": "RC7",
            "io_profile": "cell-a",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == "Respuesta de ejemplo para robot VP-6242 con controlador RC7."
    assert "PROGRAM SAMPLE_RC7" in payload["pac_code"]
    assert payload["references"] == [{"title": "Programmer's Manual I", "page": "3-24"}]
