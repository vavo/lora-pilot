"""Service identity shared by Portal and boot-time reconciliation (stdlib only).

Supervisor remains the process configuration. validate_supervisor checks its
programs, launchers and logs against this registry without rewriting user config.
"""
import configparser
import os
import shlex
from pathlib import Path


def _service(display, port, port_env, launcher, *, role, description, icon,
             order, open_ui=True, tensorboard=None, tensorboard_label=None, version=None):
    return dict(display=display, port=port, port_env=port_env, launcher=launcher,
                role=role, description=description, icon=icon, order=order,
                open_ui=open_ui, tensorboard=tensorboard, tensorboard_label=tensorboard_label,
                version=version or {})


SERVICES = {
    'jupyter': _service('Jupyter Lab', 8888, ('JUPYTER_PORT',), 'start-jupyter.sh',
        role='Notebooks', description='Work with notebooks and files in your workspace.', icon='docs', order=5),
    'code-server': _service('VS Code Server', 8443, ('CODE_SERVER_PORT',), 'start-code-server.sh',
        role='Code editor', description='Edit code and workspace files in your browser.', icon='storage', order=6),
    'comfy': _service('ComfyUI', 5555, ('COMFY_PORT',), 'comfy.sh',
        role='Image & video workflows', description='Node-based interface for image and video workflows.', icon='comfyui', order=0,
        version=dict(kind='git', repo_dir='/opt/pilot/repos/ComfyUI')),
    'kohya': _service('Kohya', 6666, ('KOHYA_PORT',), 'start-kohya.sh',
        role='LoRA training', description='Configure and train LoRAs with Kohya.', icon='models', order=2,
        tensorboard='kohya', tensorboard_label='Kohya', version=dict(kind='git', repo_dir='/opt/pilot/repos/kohya_ss')),
    'diffpipe': _service('TensorBoard', 4444, ('DIFFPIPE_PORT',), 'diffusion-pipe.sh',
        role='Training metrics', description='Follow training progress and compare your runs.', icon='dashboard', order=4,
        tensorboard='diffpipe', tensorboard_label='Diffusion Pipe', version=dict(kind='git', repo_dir='/opt/pilot/repos/diffusion-pipe')),
    'invoke': _service('Invoke AI', 9090, ('INVOKEAI_PORT', 'INVOKE_PORT'), 'invoke.sh',
        role='Image generation', description='Generate and edit images with Invoke AI.', icon='mediapilot', order=1,
        version=dict(kind='pip', python_bin='/opt/venvs/invoke/bin/python', package='invokeai')),
    'ai-toolkit': _service('AI Toolkit', 8675, ('AI_TOOLKIT_PORT',), 'ai-toolkit.sh',
        role='LoRA training', description='Train and manage LoRAs with AI Toolkit.', icon='dpipe', order=3,
        tensorboard='ai-toolkit', tensorboard_label='AI Toolkit', version=dict(kind='git', repo_dir='/opt/pilot/repos/ai-toolkit')),
    'controlpilot': _service('ControlPilot', 7878, ('PORTAL_PORT',), 'portal.sh', open_ui=False,
        role='Workspace interface', description='The interface you are using to manage your workspace.', icon='services', order=7),
    'copilot': _service('Copilot Sidecar', 7879, ('COPILOT_SIDECAR_PORT',), 'copilot-sidecar.sh', open_ui=False,
        role='Assistant', description='Connect the workspace assistant to Copilot.', icon='settings', order=8),
}
SERVICE_LOGS = {name: (f'/workspace/logs/{name}.out.log', f'/workspace/logs/{name}.err.log') for name in SERVICES}
VERSION_SPECS = {name: spec['version'] for name, spec in SERVICES.items() if spec['version']}
UPDATE_SPECS = {name: spec for name, spec in VERSION_SPECS.items() if spec['kind'] == 'pip'}
IMAGE_MANAGED_SERVICES = {name for name, spec in VERSION_SPECS.items() if spec['kind'] == 'git'}


def service_port(name, environ=None):
    env = os.environ if environ is None else environ
    spec = SERVICES[name]
    raw = next((env[key] for key in spec['port_env'] if env.get(key)), spec['port'])
    try:
        port = int(raw)
        return port if 1 <= port <= 65535 else None
    except (TypeError, ValueError):
        return None  # Never link to a different service when configuration is invalid.


def local_url(name, environ=None):
    port = service_port(name, environ)
    if port is None:
        raise ValueError(f'Invalid port for {name}')
    return f'http://127.0.0.1:{port}'


def public_definition(name, environ=None):
    spec = SERVICES[name]
    return dict(label=spec['display'], port=service_port(name, environ), role=spec['role'],
                description=spec['description'], icon=spec['icon'], order=spec['order'],
                capabilities=dict(open=spec['open_ui'], update=name in UPDATE_SPECS, install=name == 'code-server',
                    tensorboard=spec['tensorboard'], tensorboard_label=spec['tensorboard_label'],
                    disconnects_ui=name == 'controlpilot'))


def supervisor_state(name, output):
    parts = output.strip().split()
    states = {'STOPPED', 'STARTING', 'RUNNING', 'BACKOFF', 'STOPPING', 'EXITED', 'FATAL', 'UNKNOWN'}
    return parts[1] if len(parts) > 1 and parts[0] == name and parts[1] in states else 'UNKNOWN'


def validate_supervisor(path):
    parser = configparser.ConfigParser(interpolation=None)
    with Path(path).open() as source:
        parser.read_file(source)
    programs = {section.removeprefix('program:') for section in parser.sections() if section.startswith('program:')}
    errors = [f'Missing Supervisor program: {name}' for name in sorted(set(SERVICES) - programs)]
    errors += [f'Unregistered Supervisor program: {name}' for name in sorted(programs - set(SERVICES))]
    for name in sorted(programs & set(SERVICES)):
        section = parser[f'program:{name}']
        for option, expected in zip(('stdout_logfile', 'stderr_logfile'), SERVICE_LOGS[name]):
            if section.get(option) != expected:
                errors.append(f'{name}: {option} must be {expected}')
        launcher = '/opt/pilot/' + SERVICES[name]['launcher']
        tokens = shlex.split(section.get('command', ''))
        if tokens[:2] == ['/bin/bash', '-lc'] and len(tokens) == 3:
            tokens = shlex.split(tokens[2].replace(';', ' ; '))
        if launcher not in tokens:
            errors.append(f'{name}: command must launch {launcher}')
    return errors


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Validate the service registry against Supervisor')
    parser.add_argument('config', type=Path)
    errors = validate_supervisor(parser.parse_args().config)
    print('\n'.join(errors) if errors else 'Service registry agrees with Supervisor.')
    raise SystemExit(bool(errors))
