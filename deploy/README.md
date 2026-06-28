# Production deployment

Target: a clean Ubuntu VPS with DNS `A`/`AAAA` records for `api.stop-card.kz`.
Only TCP ports `22`, `80`, and `443` should be open in the VPS firewall.

## Prerequisites

1. Install Docker Engine with the Compose plugin from Docker's official repository.
2. Point `api.stop-card.kz` to the VPS public IP and wait until DNS resolves.
3. Clone the public GitHub repository to `/opt/stopcard`:

```bash
git clone https://github.com/karl4th/stop-card-backend.git /opt/stopcard
```

   If the repository becomes private, use a repository deploy key with read-only
   access. Never store a personal GitHub token on the VPS.

4. Generate production configuration interactively:

```bash
cd /opt/stopcard
chmod +x deploy/scripts/*.sh
./deploy/scripts/generate-production-env.sh
```

The script prompts for the Let's Encrypt email and Telegram bot token, generates
independent PostgreSQL, MinIO, and JWT secrets, and writes `.env.production` with
mode `0600`. Do not expose ports `5432`, `9000`, or `9001` from the VPS.

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

Manual update from the VPS:

```bash
git switch main
git pull --ff-only
./deploy/scripts/deploy-update.sh
```

For normal deployments use `.github/workflows/deploy.yml`. It connects to the
VPS and deploys an exact 40-character commit SHA, not a mutable branch name.
Configure the GitHub `production` environment with these secrets:

- `VPS_HOST` — VPS address;
- `VPS_USER` — unprivileged deployment user with access to Docker;
- `VPS_PORT` — SSH port, normally `22`;
- `VPS_SSH_PRIVATE_KEY` — private key used only by GitHub Actions to enter VPS;
- `VPS_KNOWN_HOSTS` — pinned output of `ssh-keyscan -H <VPS_HOST>` verified
  against the VPS host key.

The corresponding public key belongs in the VPS user's `authorized_keys`.
Enable automatic deployments from `main` only after the first successful manual
run by setting the repository variable `PRODUCTION_DEPLOY_ENABLED=true`. Automatic
deployment starts only after the `CI` workflow finishes successfully.
Protect `main`, require the CI workflow, and require pull-request review before
merge. A previous commit can be deployed from `workflow_dispatch` for application
rollback; database migrations must still be designed as forward-compatible.

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
