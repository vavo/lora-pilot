#!/usr/bin/env bash
set -euo pipefail
cd /opt/pilot/repos/kohya_ss

# kohya GUI entrypoint per upstream docs uses kohya_gui.py with --listen + --server_port  [oai_citation:4‡Hugging Face](https://huggingface.co/spaces/ABCCCYYY/kohya_ss/blob/main/README.md)
exec /opt/venvs/core/bin/python kohya_gui.py --listen 0.0.0.0 --server_port "${KOHYA_PORT:-6666}"
