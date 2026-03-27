#!/usr/bin/env bash
set -euo pipefail

PIDFILE="${SUPERVISORD_PIDFILE:-/tmp/supervisord.pid}"
SOCKET_FILE="${SUPERVISOR_SOCKET_PATH:-/tmp/supervisor.sock}"
SUPERVISORCTL_BIN="${SUPERVISORCTL_BIN:-$(command -v supervisorctl || true)}"

read_pid() {
  if [[ -f "${PIDFILE}" ]]; then
    tr -d '\r\n' < "${PIDFILE}" 2>/dev/null || true
  fi
}

pid="$(read_pid)"
if [[ -n "${SUPERVISORCTL_BIN}" && -S "${SOCKET_FILE}" ]]; then
  "${SUPERVISORCTL_BIN}" shutdown >/dev/null 2>&1 || true
fi

for _ in $(seq 1 15); do
  if [[ -z "${pid}" ]] || ! kill -0 "${pid}" 2>/dev/null; then
    exit 0
  fi
  sleep 1
done

if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
  kill -TERM "${pid}" 2>/dev/null || true
fi

for _ in $(seq 1 10); do
  if [[ -z "${pid}" ]] || ! kill -0 "${pid}" 2>/dev/null; then
    exit 0
  fi
  sleep 1
done

if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
  kill -KILL "${pid}" 2>/dev/null || true
fi
