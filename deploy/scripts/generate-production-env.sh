#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.production"

if [[ -e "$ENV_FILE" && "${1:-}" != "--force" ]]; then
    echo "$ENV_FILE already exists. Use --force only when intentionally rotating all secrets." >&2
    exit 1
fi

if [[ -z "${LETSENCRYPT_EMAIL:-}" ]]; then
    read -r -p "Let's Encrypt email: " LETSENCRYPT_EMAIL
fi
if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
    read -r -s -p "Telegram bot token: " TELEGRAM_BOT_TOKEN
    echo
fi

if [[ ! "$LETSENCRYPT_EMAIL" =~ ^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$ ]]; then
    echo "Invalid Let's Encrypt email." >&2
    exit 1
fi
if [[ ! "$TELEGRAM_BOT_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
    echo "Invalid Telegram bot token format." >&2
    exit 1
fi

POSTGRES_PASSWORD="$(openssl rand -hex 32)"
MINIO_ACCESS_KEY="$(openssl rand -hex 16)"
MINIO_SECRET_KEY="$(openssl rand -hex 32)"
JWT_SECRET="$(openssl rand -hex 48)"

umask 077
{
    printf 'ENVIRONMENT=production\n'
    printf 'DEBUG=false\n'
    printf 'POSTGRES_DB=stopcard\n'
    printf 'POSTGRES_USER=stopcard\n'
    printf 'POSTGRES_PASSWORD=%s\n' "$POSTGRES_PASSWORD"
    printf 'DATABASE_URL=postgresql+asyncpg://stopcard:%s@postgres:5432/stopcard\n' "$POSTGRES_PASSWORD"
    printf 'TELEGRAM_BOT_TOKEN=%s\n' "$TELEGRAM_BOT_TOKEN"
    printf 'TELEGRAM_AUTH_MAX_AGE_SECONDS=3600\n'
    printf 'MINIO_ENDPOINT=minio:9000\n'
    printf 'MINIO_ACCESS_KEY=%s\n' "$MINIO_ACCESS_KEY"
    printf 'MINIO_SECRET_KEY=%s\n' "$MINIO_SECRET_KEY"
    printf 'MINIO_SECURE=false\n'
    printf 'MINIO_BUCKET=stopcard\n'
    printf 'MINIO_REGION=us-east-1\n'
    printf 'MINIO_PUBLIC_URL=\n'
    printf 'MINIO_PRESIGN_ENDPOINT=api.stop-card.kz\n'
    printf 'MINIO_PRESIGN_SECURE=true\n'
    printf 'PHOTO_MAX_BYTES=10485760\n'
    printf 'PHOTO_URL_EXPIRES_SECONDS=3600\n'
    printf 'JWT_SECRET=%s\n' "$JWT_SECRET"
    printf 'JWT_ACCESS_TOKEN_MINUTES=60\n'
    printf 'CORS_ORIGINS=["https://stop-card.kz","https://www.stop-card.kz"]\n'
    printf 'TRUSTED_HOSTS=["api.stop-card.kz","api","127.0.0.1","localhost"]\n'
    printf 'DOMAIN=api.stop-card.kz\n'
    printf 'LETSENCRYPT_EMAIL=%s\n' "$LETSENCRYPT_EMAIL"
    printf 'ADMIN_USERNAME=admin\n'
} > "$ENV_FILE"

chmod 600 "$ENV_FILE"
echo "Created $ENV_FILE with mode 0600. Keep it outside Git and back it up securely."
