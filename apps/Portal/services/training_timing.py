"""Training elapsed time and cautious estimates from the trainer's own progress."""
import re
import time
from datetime import datetime


def seconds(value):
    try:
        parts = [int(part) for part in value.split(':')]
        if not 1 <= len(parts) <= 3:
            return None
        result = 0
        for part in parts:
            result = result * 60 + part
        return result
    except ValueError:
        return None


def timing(run, lines, updated=None, clock=time.time):
    current = clock()
    def timestamp(value):
        try:
            return datetime.fromisoformat(value).timestamp()
        except (TypeError, ValueError):
            return None
    started = timestamp(run.get('started_at'))
    ended = timestamp(run.get('finished_at'))
    active = run['status'] in {'running', 'stopping'}
    end = current if active else ended
    result = dict(elapsed_seconds=max(0, int(end - started)) if started is not None and end is not None else None,
                  remaining_seconds=None, stage=run['status'])
    if not active:
        return result
    result['stage'] = 'Starting trainer'
    if any(re.search(r'cach|encoding.*(?:latent|text)', line, re.I) for line in lines[-10:]):
        result['stage'] = 'Preparing caches'
    for line in reversed(lines):
        if not re.search(r'\bsteps\s*:', line):
            continue
        match = re.search(r'(\d+)\s*/\s*(\d+)\s*\[([\d:]+)<([\d:]+)', line)
        if match:
            step, total = int(match[1]), int(match[2])
            elapsed, remaining = seconds(match[3]), seconds(match[4])
            result['stage'] = 'Training' if step else 'Starting training'
            if run['status'] == 'running' and 10 <= step < total and elapsed is not None and elapsed >= 30 and remaining is not None and updated is not None and 0 <= current - updated <= 60:
                result['remaining_seconds'] = remaining
            break
    if run['status'] == 'stopping':
        result['stage'] = 'Stopping'
    return result
