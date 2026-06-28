#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.production"
COMPOSE_FILE="$ROOT_DIR/docker-compose.prod.yml"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Missing $ENV_FILE. Copy .env.production.example and replace every placeholder." >&2
    exit 1
fi

read_env() {
    local key="$1"
    sed -n "s/^${key}=//p" "$ENV_FILE" | tail -n 1
}

DOMAIN="$(read_env DOMAIN)"
EMAIL="$(read_env LETSENCRYPT_EMAIL)"
ADMIN_USERNAME="$(read_env ADMIN_USERNAME)"
MINIO_BUCKET="$(read_env MINIO_BUCKET)"
PRESIGN_ENDPOINT="$(read_env MINIO_PRESIGN_ENDPOINT)"

if [[ "$DOMAIN" != "api.stop-card.kz" ]]; then
    echo "DOMAIN must be api.stop-card.kz because the Nginx and photo contract use this host." >&2
    exit 1
fi

if [[ -z "$MINIO_BUCKET" || "$PRESIGN_ENDPOINT" != "$DOMAIN" ]]; then
    echo "MINIO_BUCKET must be set and MINIO_PRESIGN_ENDPOINT must equal DOMAIN." >&2
    exit 1
fi

if [[ -z "$EMAIL" || "$EMAIL" == replace-* ]]; then
    echo "Set a real LETSENCRYPT_EMAIL in .env.production." >&2
    exit 1
fi

if grep -q "replace-with" "$ENV_FILE"; then
    echo "Replace all placeholder secrets in .env.production before deployment." >&2
    exit 1
fi

compose() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "Building the API image..."
compose build api

echo "Starting PostgreSQL and MinIO..."
compose up -d postgres minio

echo "Applying database migrations..."
compose run --rm api alembic upgrade head

echo "Starting the API..."
compose up -d api

echo "Starting temporary HTTP-only Nginx for the ACME challenge..."
compose --profile bootstrap up -d nginx-bootstrap

CERTBOT_ARGS=(
    certonly
    --webroot
    --webroot-path /var/www/certbot
    --email "$EMAIL"
    --agree-tos
    --no-eff-email
    --non-interactive
    --keep-until-expiring
    -d "$DOMAIN"
)
if [[ "${LETSENCRYPT_STAGING:-0}" == "1" ]]; then
    CERTBOT_ARGS+=(--staging)
else
    CERTBOT_ARGS+=(--force-renewal)
fi

echo "Requesting the Let's Encrypt certificate..."
compose --profile bootstrap run --rm certbot "${CERTBOT_ARGS[@]}"

echo "Switching Nginx to HTTPS..."
compose --profile bootstrap stop nginx-bootstrap
compose --profile bootstrap rm -f nginx-bootstrap
compose up -d nginx

echo "Creating the first administrator..."
echo "Enter a password of at least 12 characters when prompted."
compose run --rm api stopcard create-admin "${ADMIN_USERNAME:-admin}"

echo "Deployment completed. Checking HTTPS..."
curl --fail --show-error --silent "https://${DOMAIN}/health/ready"
echo
compose ps
