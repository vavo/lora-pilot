"""Owner-only setup checks and a read-only public MCP handshake."""
from urllib.parse import urlsplit

import anyio
from fastapi import HTTPException

from .server import public_origin
from .files import Rejected


def owner(request, enabled, authenticated):
    if not enabled() or not authenticated(request) or request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, 'Sign in to ControlPilot to check MCP setup.')
    if request.headers.get('origin'):
        try:
            origin = public_origin(request.headers['origin'])
        except ValueError:
            raise HTTPException(403, 'Invalid request origin') from None
        if urlsplit(origin).netloc != request.headers.get('host'):
            raise HTTPException(403, 'Invalid request origin')


def diagnostics(runtime, request):
    try:
        from ..services.diagnostics import build_identity
    except ImportError:
        from services.diagnostics import build_identity

    headers = {key.lower(): value for key, value in request.headers.items()}
    normalized = {key.encode(): value for key, value in headers.items()}
    scope = runtime.proxy_scope(request.scope, normalized)
    checks = []

    def check(name, label, passed, success, failure):
        checks.append(dict(id=name, label=label, state='pass' if passed else 'error',
                           message=success if passed else failure))

    check('address', 'Public address', bool(runtime.origin), 'MCP has a configured public address.',
          'Set MCP_PUBLIC_URL to your HTTPS origin, without /mcp, then restart ControlPilot.')
    check('host', 'Address match', not runtime.host or normalized.get(b'host') == runtime.host,
          'This address matches the MCP server configuration.',
          'Open the configured MCP address or correct MCP_PUBLIC_URL and PORTAL_PORT, then restart ControlPilot.')
    check('https', 'Proxy and HTTPS', runtime.accepts_transport(scope),
          'HTTPS reaches the MCP boundary.' if runtime.origin and runtime.origin.startswith('https://') else 'Loopback connection accepted.',
          'The HTTPS proxy is not trusted. Check MCP_RUNPOD_PROXY_PEERS and the proxy headers. '
          'If ControlPilot is also exposed through raw TCP, remove that mapping or use a trusted HTTPS proxy.')
    check('runtime', 'MCP runtime', runtime.failure is None and runtime.http is not None,
          'The MCP runtime is available.', 'Check the ControlPilot log and installed MCP dependencies.')
    try:
        enabled = runtime.store.read()['enabled']
        state_ok = True
    except FileNotFoundError:
        enabled, state_ok = False, True
    except (OSError, ValueError, Rejected):
        enabled, state_ok = False, False
    check('state', 'Connection records', state_ok, 'Connection records are readable.',
          'MCP connection records cannot be read. Preserve config/mcp and inspect the ControlPilot log.')
    ready = all(item['state'] == 'pass' for item in checks)
    return dict(ready=ready, enabled=enabled, endpoint=runtime.origin + '/mcp' if runtime.origin else '',
                build=build_identity(), checks=checks)


async def test_connection(runtime, token):
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client

    # Verify locally before sending a credential to the fixed public endpoint.
    try:
        runtime.store.authenticate(token)
    except Rejected:
        return dict(ok=False, code='TOKEN_REJECTED', message='This token is expired, revoked or invalid. Rotate it in Connections.')
    if not runtime.origin or runtime.failure or runtime.http is None:
        return dict(ok=False, code='MCP_UNAVAILABLE', message='Resolve the server setup checks first.')
    http_status = None
    async def record_status(response):
        nonlocal http_status
        http_status = response.status_code
    try:
        with anyio.fail_after(15):
            async with httpx2.AsyncClient(timeout=10, trust_env=False, follow_redirects=False,
                headers={'Authorization': 'Bearer ' + token}, event_hooks={'response': [record_status]}) as http:
                async with Client(streamable_http_client(runtime.origin + '/mcp', http_client=http)) as client:
                    tools = [tool.name for tool in (await client.list_tools()).tools]
                    checked = 'workspace_status' in tools
                    if checked and (await client.call_tool('workspace_status', {})).is_error:
                        return dict(ok=False, code='TOOL_FAILED', message='Connected, but workspace status failed. Check the ControlPilot log.')
        return dict(ok=True, tools=tools, workspace_checked=checked,
                    message=f'Public MCP connection verified. {len(tools)} tools available.' +
                    (' Workspace status succeeded.' if checked else ' Add Workspace status permission to test that tool.'))
    except Exception as error:
        # SDK transports may wrap HTTP failures in a task-group exception.
        for _ in range(5):
            nested = getattr(error, 'exceptions', ())
            if not nested:
                break
            error = nested[0]
        messages = {
            401: ('TOKEN_REJECTED', 'The public endpoint rejected this token. Check that this address serves the same workspace.'),
            403: ('PROXY_REJECTED', 'The proxy or MCP address check rejected the connection. Review the setup checks and proxy access rules.'),
            404: ('ENDPOINT_NOT_FOUND', 'The public address does not serve /mcp. Check the configured address and running image.'),
            426: ('HTTPS_REQUIRED', 'The server could not verify HTTPS from its proxy. Review Proxy and HTTPS above.'),
        }
        code, message = messages.get(http_status, ('CONNECTION_FAILED', 'The public MCP handshake failed. Check proxy access, TLS and the ControlPilot log.'))
        if isinstance(error, (TimeoutError, httpx2.TimeoutException)):
            code, message = 'TIMEOUT', 'The public MCP connection timed out. Check that the pod and its proxy are reachable.'
        return dict(ok=False, code=code, message=message)
