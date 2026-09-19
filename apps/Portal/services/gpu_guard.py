"""Serialize ControlPilot launch checks; external tools remain advisory conflicts."""
import os
import subprocess
import threading

import httpx

LAUNCH_LOCK = threading.RLock()


def conflicts():
    reasons = []
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-compute-apps=pid,process_name,used_gpu_memory',
             '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5,
        )
        if result.returncode:
            reasons.append('GPU status unavailable. Check the NVIDIA driver before resuming.')
        else:
            for line in result.stdout.splitlines():
                if line.strip():
                    reasons.append('GPU workload: ' + line.strip())
    except (OSError, subprocess.TimeoutExpired):
        reasons.append('GPU status unavailable. An NVIDIA GPU is required.')
    try:
        with httpx.Client(timeout=2, trust_env=False) as client:
            response = client.get(f'http://127.0.0.1:{int(os.environ.get("COMFY_PORT", "5555"))}/queue')
            response.raise_for_status()
            data = response.json()
            if data.get('queue_running') or data.get('queue_pending'):
                reasons.append('ComfyUI has running or queued generation jobs.')
    except httpx.ConnectError:
        pass  # A stopped ComfyUI service cannot own queued work.
    except (httpx.HTTPError, ValueError, TypeError):
        reasons.append('ComfyUI queue status unavailable. Check Services before resuming.')
    return reasons
