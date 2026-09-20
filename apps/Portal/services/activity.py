"""Compact job state for the page-independent activity indicator."""
import re

from fastapi import APIRouter


def progress(lines):
    for line in reversed(lines):
        if 'steps' not in line:
            continue
        match = re.search(r'(\d{1,3})%\|', line)
        if match:
            return min(100, int(match[1]))
        match = re.search(r'(\d+)\s*/\s*(\d+)', line)
        if match and int(match[2]):
            return min(100, round(100 * int(match[1]) / int(match[2])))
    return None


def create_router(training, downloads, other_training):
    router = APIRouter()

    @router.get('/api/activity')
    def activity():
        items, unavailable = [], []
        paused = False
        try:
            if training.root.exists():
                training.start()
                with training.lock:
                    paused = training.paused
                    for run in training.list()[:100]:
                        items.append(dict(id='training:' + run['id'], kind='training', run_id=run['id'],
                            label=run['spec']['output_name'], state=run['status'], created_at=run['created_at'],
                            progress=progress(training.logs(run['id'])) if run['status'] == 'running' else None,
                            section='trainpilot'))
        except Exception:
            unavailable.append('Guided training')
        try:
            for job in downloads.list_jobs()['jobs']:
                items.append(dict(id=f'download:{job["name"]}:{job["started_at"]}', kind='download',
                    label=job['name'], state={'done': 'succeeded', 'error': 'failed'}.get(job['state'], job['state']),
                    created_at=job['started_at'], progress=job['progress_pct'], section='models'))
        except Exception:
            unavailable.append('Downloads')
        try:
            items.extend(other_training())
        except Exception:
            unavailable.append('Other training')
        return {'items': items, 'paused': paused, 'unavailable': unavailable}

    return router
