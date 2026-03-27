#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
SUPERVISOR_CONF="${SUPERVISOR_CONFIG_PATH:-/etc/supervisor/supervisord.conf}"
PIDFILE="${SUPERVISORD_PIDFILE:-/tmp/supervisord.pid}"
SOCKET_FILE="${SUPERVISOR_SOCKET_PATH:-/tmp/supervisor.sock}"
START_LOG="${WORKSPACE_ROOT}/logs/wsl-start.log"

mkdir -p "${WORKSPACE_ROOT}/logs"

is_supervisord_running() {
  local pid=""
  if [[ -f "${PIDFILE}" ]]; then
    pid="$(tr -d '\r\n' < "${PIDFILE}" 2>/dev/null || true)"
  fi
  [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

if is_supervisord_running; then
  echo "supervisord already running"
  exit 0
fi

/opt/pilot/bootstrap.sh >>"${START_LOG}" 2>&1

if is_supervisord_running; then
  echo "supervisord became available during bootstrap"
  exit 0
fi

nohup /usr/bin/supervisord -n -c "${SUPERVISOR_CONF}" >>"${START_LOG}" 2>&1 &

for _ in $(seq 1 20); do
  if is_supervisord_running || [[ -S "${SOCKET_FILE}" ]]; then
    echo "supervisord started"
    exit 0
  fi
  sleep 1
done

echo "supervisord failed to start; inspect ${START_LOG}" >&2
exit 1
