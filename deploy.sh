#!/usr/bin/env bash
set -Eeuo pipefail

# One-command deployment for nplus_project.
# Steps:
# 1) git pull --ff-only
# 2) python manage.py migrate
# 3) restart gunicorn and nginx
# 4) health checks (local socket + external URL)

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRANCH="${DEPLOY_BRANCH:-master}"
GUNICORN_SERVICE="${GUNICORN_SERVICE:-gunicorn}"
NGINX_SERVICE="${NGINX_SERVICE:-nginx}"
SOCKET_PATH="${SOCKET_PATH:-/run/nplus_project/nplus_project.sock}"
HEALTH_URL="${HEALTH_URL:-https://npbpm.cn/}"
PYTHON_BIN="${PYTHON_BIN:-python}"

log() {
  printf "\n[%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

run() {
  log "$*"
  "$@"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: missing command: $1" >&2
    exit 1
  fi
}

require_cmd git
require_cmd "$PYTHON_BIN"
require_cmd systemctl

if [[ ! -f "$APP_DIR/manage.py" ]]; then
  echo "ERROR: manage.py not found in $APP_DIR" >&2
  exit 1
fi

cd "$APP_DIR"

log "Deploy started in $APP_DIR"

run git rev-parse --short HEAD
run git fetch origin "$BRANCH"
run git pull --ff-only origin "$BRANCH"
run git rev-parse --short HEAD

run "$PYTHON_BIN" manage.py migrate --noinput

# Optional: collectstatic when you need static refresh.
# run "$PYTHON_BIN" manage.py collectstatic --noinput

run sudo systemctl daemon-reload
run sudo systemctl restart "$GUNICORN_SERVICE"
run sudo systemctl restart "$NGINX_SERVICE"

run sudo systemctl status "$GUNICORN_SERVICE" --no-pager -l
run sudo systemctl status "$NGINX_SERVICE" --no-pager -l

if [[ -S "$SOCKET_PATH" ]]; then
  run ls -lah "$SOCKET_PATH"
else
  echo "ERROR: socket not found: $SOCKET_PATH" >&2
  exit 1
fi

if command -v curl >/dev/null 2>&1; then
  run curl --unix-socket "$SOCKET_PATH" -I http://localhost/
  run curl -I "$HEALTH_URL"
fi

log "Deploy finished successfully"
