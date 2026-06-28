from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_invalid_payload_json_uses_contract_error_shape() -> None:
    response = client.post(
        "/api/stopcards",
        files={"payload": (None, "{not-json", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": "validation_error",
        "fields": {"payload": "Некорректный JSON"},
    }


def test_missing_payload_uses_contract_error_shape() -> None:
    response = client.post("/api/stopcards")

    assert response.status_code == 422
    assert response.json() == {
        "error": "validation_error",
        "fields": {"payload": "Поле обязательно"},
    }


def test_liveness() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_untrusted_host_is_rejected() -> None:
    response = client.get("/health/live", headers={"host": "attacker.example"})

    assert response.status_code == 400
