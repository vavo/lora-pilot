/* Activity lives outside the page loader; only the current tab polls. */
function createActivityTracker(storage, now = Date.now) {
  const key = 'lora-pilot.activity.v1';
  const active = new Set(['queued', 'running', 'stopping']);
  const terminal = new Set(['succeeded', 'failed', 'stopped', 'cancelled', 'interrupted']);
  let saved;
  try { saved = JSON.parse(storage.getItem(key)); } catch {}
  let seen = new Map(Array.isArray(saved?.seen) ? saved.seen.filter(pair => Array.isArray(pair) && pair.length === 2 && pair.every(value => typeof value === 'string')).slice(-200) : []);
  const started = Number(saved?.started) || now();
  return {
    update(items) {
      const notices = [];
      for (const item of items) {
        const before = seen.get(item.id);
        const created = typeof item.created_at === 'number' ? item.created_at * 1000 : Date.parse(item.created_at);
        if (terminal.has(item.state) && before !== item.state &&
            (active.has(before) || (!before && created >= started))) notices.push(item);
        seen.delete(item.id); seen.set(item.id, item.state);
      }
      seen = new Map([...seen].slice(-200));
      try { storage.setItem(key, JSON.stringify({started, seen: [...seen]})); } catch {}
      return notices;
    },
    active,
  };
}

window.workspaceStatus = (() => {
  const $ = id => document.getElementById(id);
  let tracker, timer, epoch = 0, last = [], notices = [], signature = '';
  const text = (tag, value, className = '') => {
    const el = document.createElement(tag); el.textContent = value; el.className = className; return el;
  };
  const stateLabel = {succeeded:'Completed', failed:'Failed', interrupted:'Interrupted', stopped:'Stopped', cancelled:'Cancelled', running:'Running', queued:'Queued', stopping:'Stopping'};
  function openTask(item) {
    if (!['trainpilot', 'dpipe', 'models'].includes(item.section)) return;
    if (item.run_id && /^[a-f0-9]{32}$/.test(item.run_id)) window.pendingTrainingRun = item.run_id;
    if (item.section === 'models') window.pendingModelDownloads = true;
    $('workspace-activity').open = false;
    window.loadSection(item.section);
  }
  function render(items, message = '') {
    const active = items.filter(item => tracker.active.has(item.state));
    const running = active.filter(item => item.state !== 'queued');
    const lead = running[0] || active[0];
    const pct = Number.isFinite(lead?.progress) ? ` · ${lead.progress}%` : '';
    $('workspace-activity-label').textContent = message || (active.length
      ? `${active.length} active · ${lead.label}${pct}` : 'Activity · Idle');
    const next = JSON.stringify([items, notices, message]);
    if (signature === next) return;
    signature = next;
    const list = $('workspace-activity-list'); list.replaceChildren();
    const recent = [...active, ...items.filter(item => !tracker.active.has(item.state)).slice(0, 10)];
    if (message) list.append(text('p', message, 'journey-note'));
    if (!recent.length) list.append(text('p', 'Training and model downloads appear here.', 'journey-note'));
    for (const item of recent) {
      const row = text('div', '', 'workspace-job');
      const link = text('button', item.label, 'journey-link'); link.type = 'button'; link.onclick = () => openTask(item);
      row.append(link, text('span', `${stateLabel[item.state] || item.state}${Number.isFinite(item.progress) && tracker.active.has(item.state) ? ` · ${item.progress}%` : ''}`));
      list.append(row);
    }
    const notice = notices[0];
    $('workspace-notice').hidden = !notice;
    if (notice) {
      $('workspace-notice-text').textContent = `${notice.label}: ${stateLabel[notice.state] || notice.state}${notices.length > 1 ? ` · ${notices.length - 1} more` : ''}`;
      $('workspace-notice-view').onclick = () => { openTask(notice); notices.shift(); signature = ''; render(last); };
    }
  }
  async function poll(generation) {
    try {
      const data = await fetchJson('/api/activity');
      if (generation !== epoch) return;
      if (!Array.isArray(data.items)) throw new Error('Invalid activity response');
      const unavailable = data.unavailable || [];
      const affected = item => unavailable.includes(item.kind === 'download' ? 'Downloads' : item.id.startsWith('training:') ? 'Guided training' : 'Other training');
      last = [...data.items, ...last.filter(affected)];
      notices.push(...tracker.update(data.items)); notices = notices.slice(-20);
      render(last, unavailable.length ? `${unavailable.join(', ')} status unavailable · showing last known activity`
        : data.paused && last.some(item => item.state === 'queued' && item.kind === 'training') ? 'Training queue paused · open activity for progress' : '');
    } catch {
      if (generation === epoch) render(last, 'Activity unavailable · retrying');
    } finally {
      if (generation === epoch) timer = setTimeout(() => poll(generation), 5000);
    }
  }
  async function showDiagnostics() {
    const dialog = $('workspace-diagnostics');
    dialog.showModal(); $('diagnostics-copy').disabled = true;
    $('diagnostics-summary').value = 'Collecting local diagnostics…';
    $('diagnostics-status').textContent = '';
    try {
      const data = await fetchJson('/api/diagnostics');
      $('diagnostics-summary').value = data.summary;
      $('diagnostics-copy').disabled = false;
    } catch {
      $('diagnostics-summary').value = 'Diagnostics unavailable. Check the ControlPilot connection and try again.';
    }
  }
  function start() {
    stop();
    if (!tracker) {
      let storage;
      try { storage = window.sessionStorage; } catch { storage = {getItem:()=>null, setItem(){}}; }
      tracker = createActivityTracker(storage);
    }
    $('workspace-bar').hidden = false;
    $('workspace-build').onclick = showDiagnostics;
    $('diagnostics-close').onclick = () => $('workspace-diagnostics').close();
    $('diagnostics-copy').onclick = async () => {
      try {
        await navigator.clipboard.writeText($('diagnostics-summary').value);
        $('diagnostics-status').textContent = 'Diagnostics copied.';
      } catch {
        $('diagnostics-summary').focus(); $('diagnostics-summary').select();
        $('diagnostics-status').textContent = 'Clipboard unavailable. The summary is selected for manual copying.';
      }
    };
    $('workspace-notice-dismiss').onclick = () => { notices.shift(); signature = ''; render(last); };
    const generation = epoch;
    fetchJson('/api/build').then(data => {
      if (generation !== epoch) return;
      $('workspace-build').textContent = `Build ${data.revision ? data.revision.slice(0, 8) : 'unknown'}`;
      $('workspace-build').title = `Build date: ${data.built_at || 'unknown'} · Open diagnostics`;
    }).catch(() => { if (generation === epoch) $('workspace-build').textContent = 'Build unavailable'; });
    poll(generation);
  }
  function stop() {
    epoch++; clearTimeout(timer);
    if ($('workspace-bar')) $('workspace-bar').hidden = true;
    if ($('workspace-diagnostics')?.open) $('workspace-diagnostics').close();
  }
  return {start, stop};
})();
