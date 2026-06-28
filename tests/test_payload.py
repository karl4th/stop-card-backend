import pytest
from pydantic import ValidationError

from app.schemas.stopcard import StopCardPayload


def valid_payload() -> dict:
    return {
        "author": {"lastName": " Нурланов ", "firstName": "Асет", "patronymic": ""},
        "worker": {
            "fullName": "Ахметов Бауыржан Серікұлы",
            "department": "Цех №3",
            "object": "БУ-5000",
        },
        "reason": {"reason": "accident"},
        "circumstances": {"selected": ["w1", "t2"]},
        "description": {"text": "Описание нарушения"},
        "hazards": {"selected": ["chemical"]},
        "corrective": {"text": "Корректирующие действия"},
    }


def test_payload_trims_text_and_normalizes_empty_patronymic() -> None:
    payload = StopCardPayload.model_validate(valid_payload())

    assert payload.author.last_name == "Нурланов"
    assert payload.author.patronymic is None


def test_duplicate_selection_is_rejected() -> None:
    data = valid_payload()
    data["circumstances"]["selected"] = ["w1", "w1"]

    with pytest.raises(ValidationError, match="не должны повторяться"):
        StopCardPayload.model_validate(data)


def test_other_hazard_requires_text() -> None:
    data = valid_payload()
    data["hazards"] = {"selected": ["other"], "otherText": "  "}

    with pytest.raises(ValidationError, match="обязательно"):
        StopCardPayload.model_validate(data)
