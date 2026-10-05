"""Bounded, private, atomic authorization and operation ledger."""
import copy
import fcntl
import hashlib
import hmac
import math
import os
import secrets
import threading
import time
import uuid
from contextlib import contextmanager

from .contracts import Automation, READ_SCOPES, SCOPES
from .files import Files, Rejected, canonical, digest

ROOT = 'config/mcp'
MAX_BYTES = 8 * 1024 * 1024
CONTROL_RESERVE_BYTES = 64 * 1024
MAX_OPERATIONS = 2048


class Store:
    def __init__(self, workspace, clock=time.time):
        self.files = Files(workspace)
        self.clock = clock
        self.lock = threading.RLock()
        self.owner = None
        self.high_clock = 0
        self.deadlines = {}

    def initialize(self):
        with self.lock, self.files.directory(ROOT, create=True, private=True):
            names = {name for name, _ in self.files.listdir(ROOT)}
            if names and 'state.json' not in names:
                raise Rejected('STORAGE_UNAVAILABLE')
            with self.transaction(create=True, control=True) as data:
                if not data:
                    data.update(version=1, workspace_id=uuid.uuid4().hex, enabled=False,
                                generation=0, clients={}, plans={}, operations={}, audit=[], last_clock=self.clock())

    def _validate(self, data):
        if (data.get('version') != 1 or type(data.get('enabled')) is not bool
                or not isinstance(data.get('workspace_id'), str)
                or type(data.get('generation')) is not int
                or type(data.get('last_clock')) not in {int, float}
                or not math.isfinite(data['last_clock'])):
            raise Rejected('STORAGE_UNAVAILABLE')
        for key in ('clients', 'plans', 'operations'):
            if not isinstance(data.get(key), dict):
                raise Rejected('STORAGE_UNAVAILABLE')
        if not isinstance(data.get('audit'), list):
            raise Rejected('STORAGE_UNAVAILABLE')
        for key, client in data['clients'].items():
            if (not isinstance(client, dict) or client.get('id') != key
                    or type(client.get('expires_at')) not in {float, int}
                    or not math.isfinite(client['expires_at']) or type(client.get('revoked')) is not bool
                    or type(client.get('version')) is not int
                    or not isinstance(client.get('token_hash'), str)
                    or len(client['token_hash']) != 64
                    or not isinstance(client.get('scopes'), list)
                    or not set(client['scopes']) <= SCOPES
                    or not isinstance(client.get('datasets'), dict)
                    or not isinstance(client.get('runs'), list)):
                raise Rejected('STORAGE_UNAVAILABLE')
            Automation.model_validate(client.get('policy', {}))
        return data

    def read(self):
        with self.lock, self.files.directory(ROOT, private=True):
            data = self._validate(self.files.json(ROOT + '/state.json', MAX_BYTES + CONTROL_RESERVE_BYTES, private=True))
            now = self.clock()
            if now + 2 < max(self.high_clock, data.get('last_clock', 0)):
                raise Rejected('CLOCK_UNAVAILABLE')
            self.high_clock = max(self.high_clock, now)
            return data

    @contextmanager
    def transaction(self, create=False, control=False):
        with self.lock, self.files.directory(ROOT, private=True) as directory:
            fd = os.open('state.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory)
            try:
                info = os.fstat(fd)
                import stat
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
                    raise Rejected('STORAGE_UNAVAILABLE')
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                try:
                    data = self.read()
                except FileNotFoundError:
                    if not create:
                        raise
                    data = {}
                original = canonical(data)
                yield data
                self._validate(data)
                updated = canonical(data)
                if updated == original:
                    return
                data['last_clock'] = max(data.get('last_clock', 0), self.clock())
                encoded = canonical(data)
                # Existing full ledgers and no-op replays must remain recoverable.
                limit = MAX_BYTES + CONTROL_RESERVE_BYTES if control or len(updated) <= len(original) else MAX_BYTES
                if control and len(encoded) > limit:
                    excess = len(encoded) - limit
                    while excess > 0 and len(data['audit']) > 1:
                        excess -= len(canonical(data['audit'].pop(0))) + 1
                    encoded = canonical(data)
                if len(encoded) > limit:
                    raise Rejected('LIMIT_EXCEEDED')
                if encoded != original:
                    self.files.write(ROOT + '/state.json', encoded, replace=bool(original != b'{}'))
            finally:
                os.close(fd)

    def claim(self):
        with self.lock:
            if self.owner is not None:
                return
            with self.files.directory(ROOT, private=True) as directory:
                fd = os.open('owner.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory)
            try:
                import stat
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
                    raise Rejected('STORAGE_UNAVAILABLE')
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.owner = fd
                with self.transaction(control=True) as data:
                    for plan in data['plans'].values():
                        if plan['state'] in {'pending', 'approved'}:
                            plan['state'] = 'invalid'
                    for op in data['operations'].values():
                        if op['state'] in {'accepted', 'dispatching'}:
                            op['state'] = 'unknown'
            except Exception:
                self.owner = None
                os.close(fd)
                raise

    def close(self):
        with self.lock:
            if self.owner is not None:
                os.close(self.owner)
                self.owner = None

    def audit(self, data, action, principal='owner', object_id=None):
        data['audit'].append(dict(at=self.clock(), action=action, principal=principal, object_id=object_id))
        data['audit'] = data['audit'][-1000:]

    def set_enabled(self, enabled):
        with self.transaction(control=True) as data:
            if data['enabled'] == enabled:
                return
            data['enabled'] = enabled
            data['generation'] += 1
            if not enabled:
                for plan in data['plans'].values():
                    if plan['state'] in {'pending', 'approved'}:
                        plan['state'] = 'invalid'
            self.audit(data, 'enable' if enabled else 'disable')

    def validate_grant(self, scopes, datasets, runs, days, policy):
        if not set(scopes) <= SCOPES or not 1 <= days <= 30:
            raise Rejected('INVALID_INPUT')
        if len(datasets) > 100 or len(runs) > 100:
            raise Rejected('LIMIT_EXCEEDED')
        if any(scope not in READ_SCOPES for scope in scopes) and 'operations:read' not in scopes:
            raise Rejected('INVALID_INPUT')
        required = {'training:submit': READ_SCOPES,
                    'training:cancel': {'runs:read', 'operations:read'},
                    'comparison:submit': {'runs:read', 'models:read', 'operations:read'},
                    'artifacts:export': {'runs:read', 'operations:read'}}
        if any(scope in scopes and not dependencies <= set(scopes) for scope, dependencies in required.items()):
            raise Rejected('INVALID_INPUT')
        return Automation.model_validate(policy or {}).model_dump()

    def create_client(self, label, scopes, datasets, runs, days=30, policy=None):
        policy = self.validate_grant(scopes, datasets, runs, days, policy)
        token = 'lp_mcp_' + secrets.token_urlsafe(32)
        client_id = uuid.uuid4().hex
        # Paths/names here come from the owner surface, never the assistant.
        grants = {uuid.uuid4().hex: name for name in datasets}
        with self.transaction() as data:
            if len(data['clients']) >= 100:
                raise Rejected('LIMIT_EXCEEDED')
            data['clients'][client_id] = dict(id=client_id, label=label, scopes=sorted(set(scopes)),
                datasets=grants, runs=sorted(set(runs)), expires_at=self.clock() + days * 86400,
                revoked=False, version=1, token_hash=hashlib.sha256(token.encode()).hexdigest(), policy=policy)
            self.audit(data, 'create_client', object_id=client_id)
        return client_id, token

    def change_client(self, client_id, label, scopes, datasets, runs, days, policy):
        policy = self.validate_grant(scopes, datasets, runs, days, policy)
        with self.transaction(control=True) as data:
            client = data['clients'].get(client_id)
            if client is None or client['revoked']:
                raise Rejected('NOT_AUTHORIZED')
            existing = {name: key for key, name in client['datasets'].items()}
            client.update(label=label, scopes=sorted(set(scopes)),
                          datasets={existing.get(name, uuid.uuid4().hex): name for name in datasets},
                          runs=sorted(set(runs)), expires_at=self.clock() + days * 86400,
                          version=client['version'] + 1, policy=policy)
            for plan in data['plans'].values():
                if plan['principal'] == client_id and plan['state'] in {'pending', 'approved'}:
                    plan['state'] = 'invalid'
            self.audit(data, 'change_client', object_id=client_id)

    def revoke(self, client_id):
        with self.transaction(control=True) as data:
            client = data['clients'].get(client_id)
            if client is None:
                raise Rejected()
            client['revoked'] = True
            client['version'] += 1
            for plan in data['plans'].values():
                if plan['principal'] == client_id and plan['state'] in {'pending', 'approved'}:
                    plan['state'] = 'invalid'
            self.audit(data, 'revoke_client', object_id=client_id)

    def rotate(self, client_id):
        token = 'lp_mcp_' + secrets.token_urlsafe(32)
        with self.transaction(control=True) as data:
            client = self.principal(client_id, data, require_enabled=False)
            client['token_hash'] = hashlib.sha256(token.encode()).hexdigest()
            self.audit(data, 'rotate_client', object_id=client_id)
        return token

    def authenticate(self, token):
        data = self.read()
        value = hashlib.sha256(token.encode()).hexdigest()
        found = None
        for client in data['clients'].values():
            if hmac.compare_digest(value, client['token_hash']):
                found = client['id']
        if found is None:
            raise Rejected('NOT_AUTHORIZED')
        return copy.deepcopy(self.principal(found, data))

    def principal(self, client_id, data=None, require_enabled=True):
        data = self.read() if data is None else data
        client = data['clients'].get(client_id)
        if ((require_enabled and not data['enabled']) or client is None or client['revoked']
                or client['expires_at'] <= self.clock()):
            raise Rejected('NOT_AUTHORIZED')
        return client

    def plan(self, principal, kind, payload, disclosure):
        with self.transaction() as data:
            client = self.principal(principal, data)
            # Operation tombstones retain replay identity after a plan expires.
            data['plans'] = {key: p for key, p in data['plans'].items()
                             if p['expires_at'] > self.clock()}
            self.deadlines = {key: value for key, value in self.deadlines.items() if key in data['plans']}
            if len(data['plans']) >= 256:
                raise Rejected('LIMIT_EXCEEDED')
            plan_id = uuid.uuid4().hex
            plan = dict(id=plan_id, kind=kind, principal=principal, version=client['version'],
                        generation=data['generation'], payload=payload, disclosure=disclosure,
                        digest=digest(payload), expires_at=self.clock() + 600, state='pending')
            policy = Automation.model_validate(client.get('policy', {})).model_dump()
            required_scope = {'training': 'training:submit', 'comparison': 'comparison:submit', 'export': 'artifacts:export'}[kind]
            if (policy['enabled'] and required_scope in client['scopes']
                    and payload.get('max_steps', 0) <= policy['max_steps']
                    and payload.get('max_seconds', 0) <= policy['max_seconds']
                    and payload.get('allocation_bytes', 0) <= policy['max_bytes']):
                plan.update(state='approved', approval='bounded_policy')
            data['plans'][plan_id] = plan
            self.deadlines[plan_id] = time.monotonic() + 600
            self.audit(data, 'plan', principal, plan_id)
        return {key: plan[key] for key in ('id', 'kind', 'disclosure', 'expires_at', 'state')}

    def approve(self, plan_id, approve):
        with self.transaction() as data:
            plan = data['plans'].get(plan_id)
            if plan is None:
                raise Rejected()
            client = self.principal(plan['principal'], data)
            if (plan['state'] != 'pending' or self.expired(plan)
                    or plan['version'] != client['version'] or plan['generation'] != data['generation']):
                raise Rejected('PLAN_STALE')
            plan['state'] = 'approved' if approve else 'rejected'
            self.audit(data, plan['state'], object_id=plan_id)

    def expired(self, plan):
        return plan['expires_at'] <= self.clock() or time.monotonic() >= self.deadlines.get(plan['id'], 0)

    def accept(self, principal, tool, request, scope):
        """Approval consumption and acceptance share one atomic durable record."""
        with self.transaction() as data:
            client = self.principal(principal, data)
            if scope not in client['scopes']:
                raise Rejected('NOT_AUTHORIZED')
            key = digest([data['workspace_id'], principal, request['request_id']])
            payload_hash = digest([tool, request])
            if key in data['operations']:
                op = data['operations'][key]
                if op['payload_hash'] != payload_hash:
                    raise Rejected('IDEMPOTENCY_CONFLICT')
                return copy.deepcopy(op), False
            if len(data['operations']) >= MAX_OPERATIONS:
                raise Rejected('LIMIT_EXCEEDED')
            plan = data['plans'].get(request.get('plan_id'))
            if tool != 'run_cancel':
                kind = tool.removesuffix('_start').removesuffix('_create')
                if plan is None or plan['principal'] != principal:
                    raise Rejected()
                if (plan['kind'] != kind or self.expired(plan)
                        or plan['version'] != client['version'] or plan['generation'] != data['generation']):
                    raise Rejected('PLAN_STALE')
                if plan['state'] != 'approved':
                    raise Rejected('APPROVAL_REQUIRED')
                if digest(plan['payload']) != plan['digest']:
                    raise Rejected('PLAN_STALE')
            active = [op for op in data['operations'].values()
                      if op['tool'] == tool and op['state'] in {'accepted', 'dispatching', 'running', 'unknown'}
                      and (op['principal'] == principal or (plan and op['payload'].get('run_id') is not None
                           and op['payload'].get('run_id') == plan['payload'].get('run_id')))]
            if active and tool != 'run_cancel':
                raise Rejected('CONFLICT')
            op = dict(id=uuid.uuid4().hex, principal=principal, tool=tool, payload_hash=payload_hash,
                      state='accepted', created_at=self.clock(), result={},
                      payload=copy.deepcopy(plan['payload']) if plan else {'run_id': request['run_id']},
                      grant_version=client['version'], generation=data['generation'])
            data['operations'][key] = op
            if plan:
                plan['state'] = 'consumed'
            self.audit(data, 'accept', principal, op['id'])
        return copy.deepcopy(op), True

    def update_operation(self, op_id, **updates):
        with self.transaction(control=True) as data:
            for op in data['operations'].values():
                if op['id'] == op_id:
                    op.update(updates)
                    self.audit(data, 'operation_' + op['state'], op['principal'], op_id)
                    return copy.deepcopy(op)
        raise Rejected()

    def operation(self, principal, op_id):
        data = self.read()
        self.principal(principal, data)
        for op in data['operations'].values():
            if op['id'] == op_id and op['principal'] == principal:
                return copy.deepcopy(op)
        raise Rejected()
