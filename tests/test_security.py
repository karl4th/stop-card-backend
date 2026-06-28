from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    encoded = hash_password("a-secure-password")

    assert encoded != "a-secure-password"
    assert verify_password("a-secure-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_access_token_round_trip() -> None:
    settings = Settings(jwt_secret="x" * 32)
    token = create_access_token("admin-id", settings)

    assert decode_access_token(token, settings) == "admin-id"
