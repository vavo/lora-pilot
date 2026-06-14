#!/usr/bin/env bash
set -euo pipefail

repo_dir="${1:-/opt/pilot/repos/ai-toolkit}"
ui_enabled="${2:-0}"

if [[ ! -d "${repo_dir}" ]]; then
  echo "AI Toolkit repo not found: ${repo_dir}" >&2
  exit 1
fi

diffusion_models_dir="${repo_dir}/extensions_built_in/diffusion_models"
init_file="${diffusion_models_dir}/__init__.py"

if [[ ! -d "${diffusion_models_dir}" ]]; then
  echo "AI Toolkit diffusion models dir not found: ${diffusion_models_dir}" >&2
  exit 1
fi

if [[ ! -f "${init_file}" ]]; then
  echo "AI Toolkit init file not found: ${init_file}" >&2
  exit 1
fi

rm -rf "${diffusion_models_dir}/ltx2"
python3 - "${init_file}" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text().splitlines()
path.write_text("\n".join(line for line in lines if ".ltx2" not in line and "LTX2Model" not in line) + "\n")
PY

if [[ "${ui_enabled}" != "1" ]]; then
  exit 0
fi

ui_dir="${repo_dir}/ui"
schema_file="${ui_dir}/prisma/schema.prisma"
next_config_file="${ui_dir}/next.config.ts"

if [[ ! -d "${ui_dir}" ]]; then
  echo "AI Toolkit UI dir not found: ${ui_dir}" >&2
  exit 1
fi

if [[ ! -f "${schema_file}" ]]; then
  echo "AI Toolkit Prisma schema not found: ${schema_file}" >&2
  exit 1
fi

python3 - "${schema_file}" "${next_config_file}" "${ui_dir}" <<'PY'
import sys
from pathlib import Path

schema_file = Path(sys.argv[1])
next_config_file = Path(sys.argv[2])
ui_dir = Path(sys.argv[3])

schema_text = schema_file.read_text()
schema_file.write_text(
    schema_text.replace('url      = "file:../../aitk_db.db"', 'url      = env("DATABASE_URL")')
)

if next_config_file.exists():
    text = next_config_file.read_text()
    next_config_file.write_text(text.replace(
    """  devIndicators: {
    buildActivity: false,
  },
""",
    "",
    ))

for path in ui_dir.rglob("*"):
    if not path.is_file():
        continue
    try:
        text = path.read_text()
    except UnicodeDecodeError:
        continue
    updated = text.replace(
        "/opt/pilot/repos/ai-toolkit/aitk_db.db",
        "/workspace/config/ai-toolkit/aitk_db.db",
    )
    if updated != text:
        path.write_text(updated)
PY
