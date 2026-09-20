"""Small, allowlisted support snapshots; never include settings, logs or URLs."""
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

BUILD_INFO = Path('/opt/pilot/build-info.json')
STATES = {'RUNNING', 'STOPPED', 'STARTING', 'STOPPING', 'BACKOFF', 'EXITED', 'FATAL', 'UNKNOWN'}


def build_identity(path=BUILD_INFO):
    try:
        data = json.loads(path.read_text())
        revision = data.get('revision', '')
        built = data.get('built_at', '')
        return {
            'revision': revision if re.fullmatch(r'[a-f0-9]{40}', str(revision)) else None,
            'built_at': built if re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', str(built)) else None,
        }
    except (OSError, ValueError, AttributeError):
        return {'revision': None, 'built_at': None}


def command(args, status=False):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=5)
        return result.stdout.strip() if result.returncode == 0 or status else ''
    except (OSError, subprocess.TimeoutExpired):
        return ''


def installed_version(spec):
    if spec.get('kind') == 'code-server':
        value = command(['code-server', '--version']).split()
        return value[0] if value and re.fullmatch(r'\d+\.\d+\.\d+', value[0]) else None
    if spec.get('kind') == 'git':
        value = command(['git', '-C', spec['repo_dir'], 'rev-parse', 'HEAD'])
        return value if re.fullmatch(r'[a-f0-9]{40}', value) else None
    if spec.get('kind') == 'pip':
        value = command([spec['python_bin'], '-c',
                         f'import importlib.metadata; print(importlib.metadata.version({spec["package"]!r}))'])
        return value if re.fullmatch(r'\d[0-9A-Za-z.+_-]{0,79}', value) else None
    return None


def snapshot(gpu_reader, service_specs, supervisor, identity):
    # No generic serialization: raw service descriptions and exception strings can contain secrets.
    states = {}
    output = command([supervisor, 'status'], status=True)
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] in service_specs and parts[1] in STATES:
            states[parts[0]] = parts[1]
    with ThreadPoolExecutor(max_workers=4) as pool:
        versions = list(pool.map(installed_version, service_specs.values()))
    build = identity()
    services = [dict(name=name, state=states.get(name, 'UNKNOWN'),
                     version=build['revision'] if service_specs[name].get('kind') == 'build' else version)
                for name, version in zip(service_specs, versions)]
    try:
        gpus = []
        for gpu in gpu_reader():
            value = gpu.model_dump() if hasattr(gpu, 'model_dump') else gpu
            name = str(value.get('name', ''))
            # Hardware names only; no arbitrary text, control characters, host IDs or driver logs.
            if not re.fullmatch(r'[A-Za-z0-9 ()+._-]{1,100}', name):
                name = 'Unknown GPU'
            memory = value.get('mem_total')
            gpus.append({'name': name, 'memory_mib': memory if type(memory) is int and memory >= 0 else None})
    except Exception:
        gpus = []
    data = dict(build=build, gpus=gpus, services=services,
                collected_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
    lines = ['LoRA Pilot diagnostics', f'Commit: {data["build"]["revision"] or "unknown"}',
             f'Build date: {data["build"]["built_at"] or "unknown"}', f'Collected: {data["collected_at"]}']
    lines.extend(f'GPU: {gpu["name"]} ({gpu["memory_mib"] if gpu["memory_mib"] is not None else "unknown"} MiB)' for gpu in gpus)
    if not gpus:
        lines.append('GPU: unavailable')
    lines.extend(f'{item["name"]}: {item["state"]}; version {item["version"] or "unknown"}' for item in services)
    data['summary'] = '\n'.join(lines)
    return data


def create_router(gpu_reader, service_specs, supervisor, identity=build_identity):
    router = APIRouter()

    @router.get('/api/build')
    def build():
        return identity()

    @router.get('/api/diagnostics')
    def diagnostics():
        return snapshot(gpu_reader, service_specs, supervisor, identity)

    return router
