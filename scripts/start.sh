#!/usr/bin/env bash
set -euo pipefail

# Keep persisted settings loaded by bootstrap in the Supervisor environment.
source /opt/pilot/bootstrap.sh
exec /usr/bin/supervisord -n -c "$SUPERVISOR_CONFIG_PATH"
