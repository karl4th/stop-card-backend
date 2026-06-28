import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qsl


class TelegramAuthError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TelegramIdentity:
    user_id: int
    username: str | None
    auth_date: datetime
    user: dict[str, object]


def validate_telegram_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int,
    future_skew_seconds: int = 30,
    now: datetime | None = None,
) -> TelegramIdentity:
    if not bot_token:
        raise TelegramAuthError("Telegram authentication is not configured")

    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError as exc:
        raise TelegramAuthError("Некорректные Telegram initData") from exc

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise TelegramAuthError("В Telegram initData отсутствует hash")

    data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise TelegramAuthError("Недействительная подпись Telegram initData")

    try:
        auth_date = datetime.fromtimestamp(int(pairs["auth_date"]), tz=UTC)
        user = json.loads(pairs["user"])
        user_id = int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError) as exc:
        raise TelegramAuthError("Telegram initData не содержит данные пользователя") from exc

    current_time = now or datetime.now(UTC)
    age = (current_time - auth_date).total_seconds()
    if age > max_age_seconds:
        raise TelegramAuthError("Срок действия Telegram initData истёк")
    if age < -future_skew_seconds:
        raise TelegramAuthError("Некорректное время Telegram initData")

    username = user.get("username")
    return TelegramIdentity(
        user_id=user_id,
        username=username if isinstance(username, str) else None,
        auth_date=auth_date,
        user=user,
    )
