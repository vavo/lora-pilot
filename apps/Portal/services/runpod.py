"""RunPod v2 access and small browser-safe projections of the current pod."""
import hashlib
import math
import os
import re
import threading
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter

BASE_URL = 'https://api.runpod.io/v2'


class RunpodError(Exception):
    def __init__(self, code, message, status=503):
        super().__init__(message)
        self.code = code
        self.status = status


def resource_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise RunpodError('invalid_id', 'RunPod resource ID is invalid.', 422)
    return value


def pod_id():
    return os.environ.get('RUNPOD_POD_ID', '').strip()


def api_key():
    key = os.environ.get('RUNPOD_API_KEY', '').strip()
    if key:
        return key
    # RunPod injects a pod-scoped credential through runpodctl's configuration.
    try:
        data = tomllib.loads((Path.home() / '.runpod/config.toml').read_text())
        key = data.get('apiKey') or data.get('apikey', '')
        if isinstance(key, str) and key.strip():
            return key.strip()
    except (OSError, ValueError):
        pass
    raise RunpodError('no_credentials', 'RunPod credentials are unavailable. Configure RUNPOD_API_KEY on the backend.')


class RunpodClient:
    def __init__(self, transport=None):
        self.transport = transport
        self.cache = {}
        self.lock = threading.Lock()

    def request(self, method, path, *, params=None, body=None, ttl=0):
        key = api_key()
        cache_key = (hashlib.sha256(key.encode()).digest(), path, tuple(sorted((params or {}).items())))
        # Serialize cache misses to avoid multiplying polling across browser tabs.
        with self.lock:
            cached = self.cache.get(cache_key) if ttl else None
            if cached and cached[0] > time.monotonic():
                if isinstance(cached[1], RunpodError):
                    raise cached[1]
                return cached[1]
            try:
                with httpx.Client(transport=self.transport, timeout=8, trust_env=False, follow_redirects=False) as client:
                    response = client.request(method, BASE_URL + path, params=params, json=body,
                                              headers={'Authorization': 'Bearer ' + key})
                retry_after = response.headers.get('Retry-After', '')
                errors = {
                    401: ('unauthorized', 'RunPod rejected the API credential.'),
                    403: ('forbidden', 'The RunPod credential does not permit this feature.'),
                    404: ('not_found', 'The RunPod resource is unavailable.'),
                    409: ('conflict', 'The pod state does not permit this action. Refresh its status.'),
                    422: ('invalid_request', 'RunPod rejected the request.'),
                    429: ('rate_limited', 'RunPod rate limit reached. Try again later.'),
                }
                if response.status_code not in {200, 204}:
                    code, message = errors.get(response.status_code, ('unavailable', 'RunPod is temporarily unavailable.'))
                    raise RunpodError(code, message, response.status_code if response.status_code in errors else 503)
                data = {} if response.status_code == 204 else response.json()
                if not isinstance(data, dict):
                    raise ValueError('Expected object')
            except (httpx.HTTPError, ValueError):
                # Never expose upstream bodies, URLs, environment or request headers.
                error = RunpodError('unavailable', 'RunPod could not be reached or returned an invalid response. Check pod status before retrying an action.')
                if ttl:
                    self.cache[cache_key] = (time.monotonic() + 30, error)
                raise error from None
            except RunpodError as error:
                if ttl:
                    delay = min(900, max(30, int(retry_after))) if error.code == 'rate_limited' and retry_after.isdigit() else 30
                    self.cache[cache_key] = (time.monotonic() + delay, error)
                raise
            if ttl:
                # Only current-pod reads are cached, and expired entries are discarded.
                now = time.monotonic()
                self.cache = {k: v for k, v in self.cache.items() if v[0] > now}
                self.cache[cache_key] = (now + ttl, data)
            elif method != 'GET':
                self.cache.clear()
            return data

    def pod(self, identifier, fresh=False):
        data = self.request('GET', '/pods/' + resource_id(identifier), ttl=0 if fresh else 60)
        if data.get('id') != identifier:
            raise RunpodError('invalid_response', 'RunPod returned an unexpected pod.')
        return data

    def action(self, identifier, action):
        if action not in {'stop', 'terminate'}:
            raise RunpodError('invalid_action', 'Unsupported shutdown action.', 422)
        data = self.request('POST', '/pods/' + resource_id(identifier) + '/action', body={'action': action})
        if action == 'stop' and data.get('id') != identifier:
            raise RunpodError('invalid_response', 'RunPod returned an unexpected action response. Check pod status before retrying.')
        return data


client = RunpodClient()


def amount(value):
    try:
        return value if type(value) in {int, float} and math.isfinite(value) and value >= 0 else None
    except OverflowError:
        return None


def unavailable(error):
    return {'available': False, 'reason': error.code, 'message': str(error)}


def workspace_mount(workspace, pod):
    mounts = pod.get('mounts') or {}
    if not isinstance(mounts, dict) or not isinstance(mounts.get('network', []), list):
        raise RunpodError('invalid_response', 'RunPod storage information is invalid.')
    path = Path(workspace).resolve()
    choices = []
    for kind, items in [('persistent', [mounts.get('persistent')]), ('network', mounts.get('network') or [])]:
        for mount in items:
            if not isinstance(mount, dict) or not isinstance(mount.get('path'), str):
                continue
            root = Path(mount['path'])
            if not root.is_absolute():
                continue
            root = root.resolve()
            if path == root or root in path.parents:
                choices.append((len(root.parts), kind, mount))
    if not choices:
        return None
    _, kind, mount = max(choices, key=lambda item: item[0])
    return kind, mount


def workspace_allocation(workspace, pod=None):
    if not pod_id():
        return {'available': False, 'reason': 'not_runpod'}
    try:
        pod = pod if pod is not None else client.pod(pod_id())
        selected = workspace_mount(workspace, pod)
        if not selected:
            return {'available': False, 'reason': 'no_mount', 'message': 'No RunPod storage mount matches this workspace.'}
        kind, mount = selected
        volume = client.request('GET', '/network-volumes/' + resource_id(mount.get('volumeId')), ttl=300) if kind == 'network' else mount
        if kind == 'network' and volume.get('id') != mount['volumeId']:
            raise RunpodError('invalid_response', 'RunPod returned an unexpected network volume.')
        size = amount(volume.get('size'))
        if not size:
            raise RunpodError('invalid_response', 'RunPod did not report an allocated storage size.')
        return {'available': True, 'kind': kind, 'mount': mount['path'], 'size_gb': size,
                'volume_id': mount.get('volumeId') if kind == 'network' else None,
                'tier': volume.get('type') if volume.get('type') in {'STANDARD', 'HIGH_PERFORMANCE'} else None}
    except RunpodError as error:
        return unavailable(error)
    except (AttributeError, TypeError, ValueError, OverflowError):
        return unavailable(RunpodError('invalid_response', 'RunPod returned incomplete feature information.'))


def billing_today(identifier):
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        data = client.request('GET', '/billing/pods', params={'podId': resource_id(identifier),
                              'startTime': start.isoformat(), 'bucketSize': 'hour'}, ttl=300)
        totals = (data.get('metadata') or {}).get('totals') or {}
        values = {key: amount(totals.get(field)) for key, field in
                  [('total_usd', 'totalAmount'), ('gpu_usd', 'gpuAmount'), ('cpu_usd', 'cpuAmount'), ('disk_usd', 'diskAmount')]}
        if any(value is None for value in values.values()):
            raise RunpodError('invalid_response', 'RunPod billing totals are unavailable.')
        return {'available': True, 'date_utc': start.date().isoformat(), **values}
    except RunpodError as error:
        return unavailable(error)
    except (AttributeError, TypeError, ValueError, OverflowError):
        return unavailable(RunpodError('invalid_response', 'RunPod returned incomplete feature information.'))


def summary(workspace):
    identifier = pod_id()
    if not identifier:
        return {'enabled': False}
    try:
        pod = client.pod(identifier)
    except RunpodError as error:
        return {'enabled': True, **unavailable(error)}
    rate = amount(pod.get('cost'))
    runtime = pod.get('runtime')
    uptime = amount(runtime.get('uptime')) if isinstance(runtime, dict) else None
    status = pod.get('status')
    estimate = amount(rate * (uptime / 3600)) if rate is not None and uptime is not None else None
    return {'enabled': True, 'available': True, 'pod_id': identifier,
            'status': status if isinstance(status, str) and status in {'RUNNING', 'EXITED', 'ERROR', 'TERMINATED', 'PROVISIONING', 'STARTING'} else 'UNKNOWN',
            'hourly_usd': rate, 'session_estimate_usd': estimate,
            'storage': workspace_allocation(workspace, pod), 'billing': billing_today(identifier)}


def create_router(workspace):
    router = APIRouter()

    @router.get('/api/runpod/status')
    def status():
        return summary(workspace)

    return router
