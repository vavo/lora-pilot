/* Activity lives outside the page loader and survives section changes. */
function createActivityTracker(storage, now = Date.now) {
  const key = 'lora-pilot.activity.v1';
  const active = new Set(['queued', 'running', 'stopping']);
  const terminal = new Set(['succeeded', 'failed', 'stopped', 'cancelled', 'interrupted']);
  let saved;
  try { saved = JSON.parse(storage.getItem(key)); } catch {}
  let seen = new Map(Array.isArray(saved?.seen) ? saved.seen.filter(pair => Array.isArray(pair) && pair.length === 2 && pair.every(value => typeof value === 'string')).slice(-200) : []);
  const started = Number(saved?.started) || now();
  let notifications = Array.isArray(saved?.notifications) ? saved.notifications.filter(item =>
    item && typeof item.id === 'string' && typeof item.label === 'string' && terminal.has(item.state)).slice(-20) : [];
  const save = () => {
    try { storage.setItem(key, JSON.stringify({started, seen: [...seen], notifications})); } catch {}
  };
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
      notifications = [...notifications, ...notices.map(item => ({...item, unread:true}))].slice(-20);
      save();
      return notices;
    },
    get notifications() { return notifications; },
    markRead(id) {
      notifications.forEach(item => { if (!id || item.id === id) item.unread = false; });
      save();
    },
    active,
  };
}

window.workspaceStatus = (() => {
  const $ = id => document.getElementById(id);
  let tracker, timer, previewTimer, epoch = 0, last = [], signature = '', statusMessage = '';
  function hidePreview() {
    clearTimeout(previewTimer);
    $('workspace-notice').hidden = true;
  }
  function expirePreview() {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(hidePreview, 5000);
  }
  function setOpen(open, focus = true) {
    $('workspace-notifications').hidden = !open;
    $('workspace-bell').setAttribute('aria-expanded', String(open));
    if (open) { hidePreview(); tracker.markRead(); render(last, statusMessage); }
    if (focus) (open ? $('workspace-notifications-close') : $('workspace-bell')).focus({preventScroll:true});
  }
  function outsideClick(event) {
    if (!$('workspace-notifications').hidden && !$('workspace-notifications').contains(event.target) &&
        !$('workspace-bell').contains(event.target)) setOpen(false, false);
  }
  function escapePanel(event) {
    if (event.key === 'Escape' && !$('workspace-notifications').hidden) setOpen(false);
  }
  const text = (tag, value, className = '') => {
    const el = document.createElement(tag); el.textContent = value; el.className = className; return el;
  };
  const stateLabel = {succeeded:'Completed', failed:'Failed', interrupted:'Interrupted', stopped:'Stopped', cancelled:'Cancelled', running:'Running', queued:'Queued', stopping:'Stopping'};
  function openTask(item) {
    if (!['trainpilot', 'dpipe', 'models'].includes(item.section)) return;
    if (item.run_id && /^[a-f0-9]{32}$/.test(item.run_id)) window.pendingTrainingRun = item.run_id;
    if (item.section === 'models') window.pendingModelDownloads = true;
    tracker.markRead(item.id); hidePreview(); setOpen(false, false); render(last, statusMessage);
    window.loadSection(item.section);
  }
  function render(items, message = '') {
    statusMessage = message;
    const notices = tracker.notifications;
    const active = items.filter(item => tracker.active.has(item.state));
    const running = active.filter(item => item.state !== 'queued');
    const lead = running[0] || active[0];
    const pct = Number.isFinite(lead?.progress) ? ` · ${lead.progress}%` : '';
    $('workspace-activity-label').textContent = message || (active.length
      ? `${active.length} active · ${lead.label}${pct}` : 'No active tasks');
    const unread = notices.filter(item => item.unread).length;
    $('workspace-unread').textContent = String(unread);
    $('workspace-unread').hidden = !unread;
    $('workspace-bell').setAttribute('aria-label', unread ? `Notifications, ${unread} unread` : 'Notifications');
    const next = JSON.stringify([items, notices, message]);
    if (signature === next) return;
    signature = next;
    const list = $('workspace-activity-list'); list.replaceChildren();
    const recent = [...active, ...[...notices].reverse(), ...items.filter(item => !tracker.active.has(item.state)).slice(0, 10)]
      .filter((item, index, all) => all.findIndex(other => other.id === item.id) === index);
    if (message) list.append(text('p', message, 'journey-note'));
    if (!recent.length) list.append(text('p', 'Training and model downloads appear here.', 'journey-note'));
    for (const item of recent) {
      const row = text('div', '', 'workspace-job');
      const link = text('button', item.label, 'journey-link'); link.type = 'button'; link.onclick = () => openTask(item);
      row.append(link, text('span', `${stateLabel[item.state] || item.state}${Number.isFinite(item.progress) && tracker.active.has(item.state) ? ` · ${item.progress}%` : ''}`));
      list.append(row);
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
      const incoming = tracker.update(data.items);
      if (!$('workspace-notifications').hidden) tracker.markRead();
      else if (incoming.length) {
        const notice = incoming[incoming.length - 1];
        $('workspace-notice-text').textContent = `${notice.label}: ${stateLabel[notice.state] || notice.state}${incoming.length > 1 ? ` · ${incoming.length - 1} more` : ''}`;
        $('workspace-notice-view').onclick = () => openTask(notice);
        $('workspace-notice').hidden = false;
        expirePreview();
      }
      render(last, unavailable.length ? `${unavailable.join(', ')} status unavailable · showing last known activity`
        : data.paused && last.some(item => item.state === 'queued' && item.kind === 'training') ? 'Training queue paused · open activity for progress' : '');
    } catch {
      if (generation === epoch) render(last, 'Activity unavailable · retrying');
    } finally {
      if (generation === epoch) timer = setTimeout(() => poll(generation), 5000);
    }
  }
  async function showDiagnostics() {
    setOpen(false, false);
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
    $('workspace-bell').hidden = false;
    $('workspace-bell').onclick = () => setOpen($('workspace-notifications').hidden);
    $('workspace-notifications-close').onclick = () => setOpen(false);
    $('workspace-diagnostics-open').onclick = showDiagnostics;
    document.addEventListener('pointerdown', outsideClick);
    document.addEventListener('keydown', escapePanel);
    $('diagnostics-close').onclick = () => $('workspace-diagnostics').close();
    $('workspace-diagnostics').onclose = () => {
      if (!$('workspace-bell').hidden) $('workspace-bell').focus({preventScroll:true});
    };
    $('diagnostics-copy').onclick = async () => {
      try {
        await navigator.clipboard.writeText($('diagnostics-summary').value);
        $('diagnostics-status').textContent = 'Diagnostics copied.';
      } catch {
        $('diagnostics-summary').focus(); $('diagnostics-summary').select();
        $('diagnostics-status').textContent = 'Clipboard unavailable. The summary is selected for manual copying.';
      }
    };
    $('workspace-notice-dismiss').onclick = hidePreview;
    $('workspace-notice').onmouseenter = $('workspace-notice').onfocusin = () => clearTimeout(previewTimer);
    $('workspace-notice').onmouseleave = $('workspace-notice').onfocusout = expirePreview;
    const generation = epoch;
    render(last);
    poll(generation);
  }
  function stop() {
    epoch++; clearTimeout(timer);
    hidePreview();
    $('workspace-bell').hidden = true;
    $('workspace-bell').setAttribute('aria-expanded', 'false');
    $('workspace-notifications').hidden = true;
    document.removeEventListener('pointerdown', outsideClick);
    document.removeEventListener('keydown', escapePanel);
    if ($('workspace-diagnostics')?.open) $('workspace-diagnostics').close();
  }
  return {start, stop};
})();
