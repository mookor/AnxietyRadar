#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="anxietyradar-planes"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_TEMPLATE="$REPO_ROOT/deploy/anxietyradar-planes.service.in"
ENV_FILE="$REPO_ROOT/.env"
CLIENT_IP="${1:-}"

if [[ $EUID -ne 0 ]]; then
  echo "Запустите с sudo: sudo $0 [IP_клиента]"
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Создайте $ENV_FILE (скопируйте из .env.example) и настройте зону поиска."
  exit 1
fi

if [[ ! -x "$REPO_ROOT/venv/bin/python" ]]; then
  echo "Не найден venv: $REPO_ROOT/venv/bin/python"
  exit 1
fi

if [[ ! -f "$SERVICE_TEMPLATE" ]]; then
  echo "Не найден шаблон: $SERVICE_TEMPLATE"
  exit 1
fi

SERVICE_USER="$(stat -c '%U' "$REPO_ROOT")"
SERVICE_GROUP="$(stat -c '%G' "$REPO_ROOT")"

sed \
  -e "s|@REPO_ROOT@|${REPO_ROOT}|g" \
  -e "s|@SERVICE_USER@|${SERVICE_USER}|g" \
  -e "s|@SERVICE_GROUP@|${SERVICE_GROUP}|g" \
  "$SERVICE_TEMPLATE" > "/etc/systemd/system/${SERVICE_NAME}.service"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

API_PORT="$(grep -E '^API_PORT=' "$ENV_FILE" | tail -1 | cut -d= -f2 | tr -d '[:space:]')"
API_PORT="${API_PORT:-8001}"

if [[ -n "$CLIENT_IP" ]]; then
  if command -v ufw >/dev/null 2>&1; then
    ufw allow from "$CLIENT_IP" to any port "$API_PORT" proto tcp comment "AnxietyRadar client"
    echo "UFW: разрешён TCP $API_PORT с $CLIENT_IP"
  else
    echo "ufw не найден — настройте firewall вручную для порта $API_PORT с $CLIENT_IP"
  fi
fi

echo "Сервис $SERVICE_NAME установлен."
systemctl status "$SERVICE_NAME" --no-pager || true
