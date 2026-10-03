"""Owner-only connection/approval routes, separate from MCP credentials."""
import hashlib
import hmac
import re
import stat

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import Field

from .contracts import Automation, Input, READ_SCOPES, SCOPES
from .files import Rejected
try:
    from ..services.gpu_guard import LAUNCH_LOCK
except ImportError:
    from services.gpu_guard import LAUNCH_LOCK


class OwnerChange(Input):
    password: str = Field(min_length=1, max_length=1024)


class Enable(OwnerChange):
    enabled: bool


class Client(OwnerChange):
    label: str = Field(min_length=1, max_length=80)
    scopes: list[str] = Field(max_length=20)
    datasets: list[str] = Field(default_factory=list, max_length=100)
    runs: list[str] = Field(default_factory=list, max_length=100)
    days: int = Field(default=30, ge=1, le=30)
    policy: Automation = Field(default_factory=Automation)


class Approval(OwnerChange):
    approve: bool


def create_app(runtime, enabled, authenticated, session_value, verify_password):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    store = runtime.store

    @app.exception_handler(RequestValidationError)
    async def invalid(request, error):
        return JSONResponse({'detail': 'Invalid MCP settings input'}, status_code=422)

    @app.exception_handler(Exception)
    async def unavailable(request, error):
        code = error.code if isinstance(error, Rejected) else 'MCP_UNAVAILABLE'
        return JSONResponse({'detail': code}, status_code=403 if code == 'NOT_AUTHORIZED' else 409,
                            headers={'Cache-Control': 'no-store'})

    def check(request, change=None):
        if not runtime.origin:
            raise Rejected('Configure MCP_PUBLIC_URL before managing MCP')
        if (request.headers.get('host') != runtime.host or not enabled() or not authenticated(request)
                or request.headers.get('sec-fetch-site') == 'cross-site'):
            raise Rejected('NOT_AUTHORIZED')
        csrf = hmac.new(session_value().encode(), b'lora-pilot:mcp-settings:v1', hashlib.sha256).hexdigest()
        if change is not None:
            if (request.headers.get('origin') != runtime.origin
                    or not hmac.compare_digest(request.headers.get('x-mcp-csrf', ''), csrf)
                    or not verify_password(change.password)):
                raise Rejected('NOT_AUTHORIZED')
        return csrf

    def options():
        datasets, runs = [], []
        try:
            datasets = [name for name, info in store.files.listdir('datasets') if stat.S_ISDIR(info.st_mode)]
        except FileNotFoundError:
            pass
        try:
            for name, info in store.files.listdir('config/training'):
                if re.fullmatch(r'[a-f0-9]{32}', name) and stat.S_ISDIR(info.st_mode):
                    try:
                        run = store.files.json('config/training/' + name + '/run.json')
                        if run.get('id') == name:
                            runs.append(dict(id=name, name=run['spec']['output_name']))
                    except (OSError, ValueError, KeyError, Rejected):
                        continue
        except FileNotFoundError:
            pass
        return dict(datasets=datasets, runs=runs)

    @app.get('/api/settings/mcp')
    def status(request: Request):
        csrf = check(request)
        try:
            data = store.read()
        except FileNotFoundError:
            data = dict(enabled=False, clients={}, plans={})
        return dict(enabled=data['enabled'], csrf=csrf, url=runtime.origin + '/mcp',
            execution_enabled=runtime.facade.writes, available=runtime.failure is None and runtime.http is not None,
            scopes=sorted(SCOPES if runtime.facade.writes else READ_SCOPES),
            clients=[dict({key: client[key] for key in ('id', 'label', 'scopes', 'datasets', 'runs', 'expires_at', 'revoked')}, policy=client.get('policy', {}))
                     for client in data['clients'].values()],
            approvals=[{key: plan[key] for key in ('id', 'kind', 'principal', 'disclosure', 'expires_at', 'state')}
                       for plan in data['plans'].values() if plan['state'] == 'pending' and plan['expires_at'] > store.clock()],
            **options())

    @app.post('/api/settings/mcp')
    def configure(request: Request, payload: Enable):
        check(request, payload)
        if payload.enabled and (runtime.failure or runtime.http is None):
            raise Rejected('MCP_UNAVAILABLE')
        store.initialize()
        store.claim()
        with LAUNCH_LOCK:
            store.set_enabled(payload.enabled)
        return dict(enabled=payload.enabled)

    def check_objects(payload):
        available = options()
        if (not set(payload.datasets) <= set(available['datasets'])
                or not set(payload.runs) <= {run['id'] for run in available['runs']}
                or not set(payload.scopes) <= (SCOPES if runtime.facade.writes else READ_SCOPES)):
            raise Rejected('INVALID_INPUT')

    @app.post('/api/settings/mcp/clients')
    def create_client(request: Request, payload: Client):
        check(request, payload)
        check_objects(payload)
        client_id, token = store.create_client(payload.label, payload.scopes, payload.datasets, payload.runs, payload.days, payload.policy.model_dump())
        return dict(id=client_id, token=token)

    @app.patch('/api/settings/mcp/clients/{client_id}')
    def change_client(request: Request, client_id: str, payload: Client):
        check(request, payload)
        check_objects(payload)
        with LAUNCH_LOCK:
            store.change_client(client_id, payload.label, payload.scopes, payload.datasets, payload.runs, payload.days, payload.policy.model_dump())
        return dict(updated=True)

    @app.delete('/api/settings/mcp/clients/{client_id}')
    def revoke(request: Request, client_id: str, payload: OwnerChange):
        check(request, payload)
        with LAUNCH_LOCK:
            store.revoke(client_id)
        return dict(revoked=True)

    @app.post('/api/settings/mcp/clients/{client_id}/rotate')
    def rotate(request: Request, client_id: str, payload: OwnerChange):
        check(request, payload)
        return dict(token=store.rotate(client_id))

    @app.post('/api/settings/mcp/approvals/{plan_id}')
    def approve(request: Request, plan_id: str, payload: Approval):
        check(request, payload)
        store.approve(plan_id, payload.approve)
        return dict(approved=payload.approve)

    return app
