import pytest

from app.core.config import Settings
from app.services.storage import (
    ObjectStorage,
    PhotoValidationError,
    detect_image_type,
    validate_photo,
)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (b"\xff\xd8\xff\xe0rest", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\nrest", "image/png"),
        (b"RIFF\x00\x00\x00\x00WEBPrest", "image/webp"),
        (b"\x00\x00\x00\x18ftypheicrest", "image/heic"),
        (b"\x00\x00\x00\x18ftypmif1rest", "image/heif"),
    ],
)
def test_detect_image_type(data: bytes, expected: str) -> None:
    assert detect_image_type(data) == expected


def test_rejects_mime_signature_mismatch() -> None:
    with pytest.raises(PhotoValidationError, match="не соответствует"):
        validate_photo(b"\xff\xd8\xff\xe0rest", "image/png", 100)


def test_rejects_oversized_photo() -> None:
    with pytest.raises(PhotoValidationError, match="превышает"):
        validate_photo(b"\xff\xd8\xff\xe0rest", "image/jpeg", 4)


async def test_presigned_url_uses_client_visible_endpoint_without_network_request() -> None:
    storage = ObjectStorage(
        Settings(
            minio_endpoint="minio:9000",
            minio_presign_endpoint="storage.example.test",
            minio_presign_secure=True,
            minio_region="us-east-1",
        )
    )

    url = await storage.public_url("stopcards/01TEST/photo.png")

    assert url.startswith("https://storage.example.test/stopcard/stopcards/01TEST/photo.png?")
    assert "X-Amz-Signature=" in url
