import io
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import quote

from anyio import to_thread
from minio import Minio
from minio.error import S3Error

from app.core.config import Settings


class PhotoValidationError(ValueError):
    pass


SUPPORTED_IMAGES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}


def detect_image_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in {b"heic", b"heix", b"hevc", b"hevx"}:
            return "image/heic"
        if brand in {b"mif1", b"msf1", b"heif"}:
            return "image/heif"
    return None


@dataclass(frozen=True, slots=True)
class ValidatedPhoto:
    data: bytes
    content_type: str
    extension: str


def validate_photo(data: bytes, declared_type: str | None, max_bytes: int) -> ValidatedPhoto:
    if not data:
        raise PhotoValidationError("Файл фотографии пуст")
    if len(data) > max_bytes:
        raise PhotoValidationError(f"Размер фотографии превышает {max_bytes} байт")

    detected_type = detect_image_type(data)
    if detected_type is None:
        raise PhotoValidationError("Неподдерживаемый формат фотографии")
    normalized_declared = (declared_type or "").lower().split(";", maxsplit=1)[0].strip()
    if normalized_declared not in SUPPORTED_IMAGES:
        raise PhotoValidationError("Неподдерживаемый MIME type фотографии")
    if normalized_declared != detected_type:
        raise PhotoValidationError("MIME type не соответствует содержимому фотографии")

    return ValidatedPhoto(data, detected_type, SUPPORTED_IMAGES[detected_type])


class ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
            region=settings.minio_region,
        )
        self.presign_client = Minio(
            settings.minio_presign_endpoint or settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=(
                settings.minio_presign_secure
                if settings.minio_presign_secure is not None
                else settings.minio_secure
            ),
            region=settings.minio_region,
        )

    async def ensure_bucket(self) -> None:
        exists = await to_thread.run_sync(self.client.bucket_exists, self.settings.minio_bucket)
        if not exists:
            try:
                await to_thread.run_sync(self.client.make_bucket, self.settings.minio_bucket)
            except S3Error as exc:
                if exc.code not in {"BucketAlreadyExists", "BucketAlreadyOwnedByYou"}:
                    raise

    async def upload(self, key: str, photo: ValidatedPhoto) -> None:
        stream = io.BytesIO(photo.data)
        await to_thread.run_sync(
            lambda: self.client.put_object(
                self.settings.minio_bucket,
                key,
                stream,
                len(photo.data),
                content_type=photo.content_type,
            )
        )

    async def delete(self, key: str) -> None:
        await to_thread.run_sync(self.client.remove_object, self.settings.minio_bucket, key)

    async def public_url(self, key: str) -> str:
        if self.settings.minio_public_url:
            return f"{self.settings.minio_public_url.rstrip('/')}/{quote(key)}"
        return await to_thread.run_sync(
            lambda: self.presign_client.presigned_get_object(
                self.settings.minio_bucket,
                key,
                expires=timedelta(seconds=self.settings.photo_url_expires_seconds),
            )
        )
