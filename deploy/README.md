# Production deployment

Target: a clean Ubuntu VPS with DNS `A`/`AAAA` records for `api.stop-card.kz`.
Only TCP ports `22`, `80`, and `443` should be open in the VPS firewall.

## Prerequisites

1. Install Docker Engine with the Compose plugin from Docker's official repository.
2. Point `api.stop-card.kz` to the VPS public IP and wait until DNS resolves.
3. Clone the repository to `/opt/stopcard`.
4. Create production configuration:

```bash
cd /opt/stopcard
cp .env.production.example .env.production
chmod 600 .env.production
```

Replace every placeholder. Generate secrets, for example:

```bash
openssl rand -hex 32
```

`POSTGRES_PASSWORD` must also be inserted into `DATABASE_URL` with URL encoding
when it contains reserved URL characters. Do not expose ports `5432`, `9000`,
or `9001` from the VPS.

Configure the firewall before enabling it, adapting the SSH rule if the server
uses a non-standard SSH port:

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

## First deployment

```bash
chmod +x deploy/scripts/*.sh
./deploy/scripts/init-production.sh
```

The script builds the image, starts PostgreSQL and MinIO, applies migrations,
obtains the Let's Encrypt certificate through an HTTP challenge, enables HTTPS,
and creates the first administrator interactively.

To test the ACME flow without hitting Let's Encrypt production limits:

```bash
LETSENCRYPT_STAGING=1 ./deploy/scripts/init-production.sh
```

Do not use the staging certificate for the real site.

## Updates

After pulling reviewed changes:

```bash
./deploy/scripts/deploy-update.sh
```

The migration runs before the new API container replaces the existing one.
Database migrations therefore need to remain backward-compatible during a
rolling update.

## Certificate renewal

Run twice daily from root's cron:

```cron
17 2,14 * * * cd /opt/stopcard && ./deploy/scripts/renew-certificates.sh >> /var/log/stopcard-certbot.log 2>&1
```

Certbot renews only certificates close to expiry; Nginx is reloaded afterward.

## Operations

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f api nginx
docker compose --env-file .env.production -f docker-compose.prod.yml exec postgres \
  pg_isready -U stopcard -d stopcard
```

Required external checks:

```bash
curl -i https://api.stop-card.kz/health/ready
curl -i https://api.stop-card.kz/api/reference/reason
```

For every photo, the API returns a signed URL on `api.stop-card.kz`. Nginx accepts
only `GET`/`HEAD` under `/${MINIO_BUCKET}/stopcards/` and proxies the request to
private MinIO while preserving the signed host and query parameters. Both the
domain and bucket path are rendered from `.env.production` when Nginx starts.

Back up both PostgreSQL and the MinIO data volume. A backup is not valid until a
restore has been tested on a separate host.
