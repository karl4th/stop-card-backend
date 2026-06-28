#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 1 || ! "$1" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Usage: $0 <full-40-character-commit-sha>" >&2
    exit 2
fi

TARGET_SHA="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOCK_FILE="/tmp/stopcard-production-deploy.lock"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "Another production deployment is running." >&2
    exit 1
fi

cd "$ROOT_DIR"
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    echo "Tracked files on the VPS contain local changes; deployment aborted." >&2
    exit 1
fi

git fetch --prune origin
if ! git cat-file -e "${TARGET_SHA}^{commit}"; then
    echo "Commit $TARGET_SHA is not available from origin." >&2
    exit 1
fi

git checkout --detach "$TARGET_SHA"
chmod +x deploy/scripts/*.sh
./deploy/scripts/deploy-update.sh
printf '%s\n' "$TARGET_SHA" > .git/deployed-revision
