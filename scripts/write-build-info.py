"""Record image identity without relying on runtime Git or mutable image tags."""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def write_info(path):
    revision = os.environ.get('BUILD_REVISION', '')
    built = os.environ.get('BUILD_DATE', '')
    if not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', built):
        built = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    data = {'revision': revision if re.fullmatch(r'[a-f0-9]{40}', revision) else None, 'built_at': built}
    Path(path).write_text(json.dumps(data) + '\n')


if __name__ == '__main__':
    write_info(sys.argv[1] if len(sys.argv) > 1 else '/opt/pilot/build-info.json')
