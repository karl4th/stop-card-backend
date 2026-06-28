import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import pytest

from app.services.telegram import TelegramAuthError, validate_telegram_init_data

BOT_TOKEN = "123456:TEST_TOKEN"


def signed_init_data(auth_date: datetime) -> str:
    fields = {
        "auth_date": str(int(auth_date.timestamp())),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(
            {"id": 123456789, "first_name": "Aset", "username": "aset"},
            separators=(",", ":"),
        ),
    }
    check = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def test_valid_init_data_returns_identity() -> None:
    now = datetime(2026, 6, 28, 12, tzinfo=UTC)

    identity = validate_telegram_init_data(
        signed_init_data(now), BOT_TOKEN, max_age_seconds=3600, now=now
    )

    assert identity.user_id == 123456789
    assert identity.username == "aset"


def test_tampered_init_data_is_rejected() -> None:
    now = datetime(2026, 6, 28, 12, tzinfo=UTC)
    tampered = signed_init_data(now).replace("aset", "attacker")

    with pytest.raises(TelegramAuthError, match="подпись"):
        validate_telegram_init_data(tampered, BOT_TOKEN, max_age_seconds=3600, now=now)


def test_expired_init_data_is_rejected() -> None:
    now = datetime(2026, 6, 28, 12, tzinfo=UTC)

    with pytest.raises(TelegramAuthError, match="истёк"):
        validate_telegram_init_data(
            signed_init_data(now - timedelta(hours=2)),
            BOT_TOKEN,
            max_age_seconds=3600,
            now=now,
        )
