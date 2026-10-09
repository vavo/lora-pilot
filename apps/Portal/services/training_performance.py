"""Local measurements and editable starting points, with no invented benchmarks."""
import csv
import io
import subprocess
from datetime import datetime
from fastapi import HTTPException

from .experiment_export import portable_settings
from .diagnostics import build_identity


def gpu_snapshot():
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used',
                                 '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=2)
        rows = list(csv.reader(io.StringIO(result.stdout)))
        if result.returncode or len(rows) != 1:
            return None  # Recommendations target one GPU, not the sum of several cards.
        name, total, used = rows[0]
        total, used = int(total.strip()), int(used.strip())
        if total <= 0 or not 0 <= used <= total:
            return None
        return dict(name=name.strip(), total_mib=total, used_mib=used)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def sample(run):
    gpu = gpu_snapshot()
    if not gpu:
        return
    performance = run.setdefault('performance', dict(gpu=gpu, build=build_identity(), peak_device_mib=0, samples=0))
    if performance['gpu']['name'] != gpu['name'] or performance['gpu']['total_mib'] != gpu['total_mib']:
        return
    performance['peak_device_mib'] = max(performance['peak_device_mib'], gpu['used_mib'])
    performance['samples'] += 1


def finish(run, directory):
    performance = run.get('performance')
    if not performance:
        return
    try:
        performance['elapsed_seconds'] = max(0, int((datetime.fromisoformat(run['finished_at'])
                                                  - datetime.fromisoformat(run['started_at'])).total_seconds()))
        performance['settings'] = portable_settings(run, directory)
    except (OSError, ValueError, KeyError, HTTPException):
        pass  # Measurements must never turn a successful training run into a failed one.


def recommendation(family, profile, runs, gpu=None):
    rank = {'quick_test': 32, 'regular': 48, 'high_quality': 64}[profile] if family == 'sdxl' else {'quick_test': 16, 'regular': 32, 'high_quality': 64}[profile]
    total = gpu['total_mib'] if gpu else 0
    defaults = dict(train_batch_size=1 if family != 'sdxl' or total < 23000 else 2 if total < 46000 else 4,
                    gradient_accumulation_steps=1 if family != 'sdxl' else 2, network_dim=rank)
    if family in {'flux1', 'hunyuan_image21'}:
        defaults['blocks_to_swap'] = 18 if total < (80000 if family == 'hunyuan_image21' else 46000) else 0
    match = None
    revision = build_identity()['revision']
    if gpu:
        for run in runs:
            evidence = run.get('performance', {})
            measured_gpu = evidence.get('gpu', {})
            settings = evidence.get('settings', {})
            limits = dict(train_batch_size=(1, 8), gradient_accumulation_steps=(1, 16),
                          network_dim=(4, 128), blocks_to_swap=(0, 35))
            usable = all(type(settings.get(key)) is int and limits[key][0] <= settings[key] <= limits[key][1]
                         for key in defaults)
            if (run['status'] == 'succeeded' and not run.get('recovery') and evidence.get('samples', 0) >= 2
                    and evidence.get('elapsed_seconds', 0) > 0 and usable
                    and evidence.get('build', {}).get('revision') == revision
                    and run['spec']['family'] == family and run['spec']['profile'] == profile
                    and measured_gpu.get('name') == gpu['name'] and measured_gpu.get('total_mib') == total):
                match = run
                break
    if match:
        settings = match['performance']['settings']
        defaults.update({key: settings[key] for key in defaults if key in settings})
    return dict(gpu=gpu, settings=defaults, measured=bool(match),
                evidence=dict(run_id=match['id'], output_name=match['spec']['output_name'],
                              elapsed_seconds=match['performance']['elapsed_seconds'],
                              peak_device_mib=match['performance']['peak_device_mib'],
                              samples=match['performance']['samples']) if match else None)
