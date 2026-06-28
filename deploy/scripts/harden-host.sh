#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this script as root." >&2
    exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEPLOY_KEYS="/home/deploy/.ssh/authorized_keys"

if [[ ! -s "$DEPLOY_KEYS" ]]; then
    echo "$DEPLOY_KEYS is missing or empty; refusing to disable password login." >&2
    exit 1
fi

install -m 0644 \
    "$ROOT_DIR/deploy/ssh/99-stopcard-hardening.conf" \
    /etc/ssh/sshd_config.d/99-stopcard-hardening.conf

sshd -t
systemctl reload ssh

ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "SSH password authentication disabled; deploy key access preserved."
