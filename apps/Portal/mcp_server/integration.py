"""Compose the MCP lifecycle with Portal without constructing another queue."""
import os
from pathlib import Path

from .admin import create_app
from .facade import Facade
from .server import Boundary, Runtime
from .store import Store


def install(app, workspace, models, queue, auth_enabled, authenticated, session_value, verify_password):
    store = Store(workspace)
    bundled_manifest = Path(__file__).resolve().parents[3] / 'config/models.manifest.default'
    writes = all(os.environ.get(name) == '1' for name in
                 ('MCP_EXECUTION_ENABLED', 'MCP_STORAGE_VERIFIED', 'MCP_GPU_VERIFIED'))
    facade = Facade(store, queue, models, bundled_manifest, writes=writes)
    if writes:
        from .operations import Execution
        try:
            budget = int(os.environ.get('MCP_WRITE_BUDGET_BYTES', '0'))
        except ValueError:
            budget = 0
        Execution(facade, budget)
    runtime = Runtime(facade, os.environ.get('MCP_PUBLIC_URL', ''))
    runtime.admin = create_app(runtime, auth_enabled, authenticated, session_value, verify_password)
    app.add_middleware(Boundary, runtime=runtime)
    app.router.on_startup.append(runtime.start)
    app.router.on_shutdown.append(runtime.stop)
    return runtime
