#!/usr/bin/env bash
set -euo pipefail

mkdir -p /opt/pilot/runtime

python3 - <<'PY'
import json
import os
from pathlib import Path

payload = {
    "app_version": os.environ.get("APP_VERSION", "dev"),
    "runtime_version": os.environ.get("RUNTIME_VERSION", os.environ.get("APP_VERSION", "dev")),
    "vcs_ref": os.environ.get("VCS_REF", "unknown"),
    "build_date": os.environ.get("BUILD_DATE", "unknown"),
    "build_platform": os.environ.get("BUILDPLATFORM", "unknown"),
    "target_platform": os.environ.get("TARGETPLATFORM", "unknown"),
}

Path("/opt/pilot/runtime/version.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY
