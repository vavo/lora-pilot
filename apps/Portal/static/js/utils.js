// Simple helpers shared across modules
window.formatBytes = function (bytes) {
  if (!bytes || bytes <= 0) return "—";
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(sizes.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  const val = bytes / Math.pow(1024, i);
  return `${val.toFixed(val >= 10 || i === 0 ? 0 : 1)} ${sizes[i]}`;
};

window.fetchJson = async function (url, opts = {}) {
  const res = await fetch(url, opts);
  opts.signal?.throwIfAborted();
  if (!res.ok) {
    if (res.status === 401 && typeof window.showControlPilotLogin === "function") {
      window.showControlPilotLogin("ControlPilot password required");
    }
    const txt = await res.text();
    throw new Error(txt || res.statusText);
  }
  
  if (res.status === 204) return null;
  const contentType = res.headers.get('content-type') || '';
  if (!/^application\/(?:[\w.-]+\+)?json(?:\s*;|$)/i.test(contentType)) {
    throw new Error('Unexpected server response. Expected JSON; check the connection and retry.');
  }
  const text = await res.text();
  opts.signal?.throwIfAborted();
  try {
    return JSON.parse(text);
  } catch {
    throw new Error('Invalid JSON response from the server. Retry the request.');
  }
};

window.buildPortUrl = function (port) {
  const numericPort = Number.parseInt(String(port), 10);
  if (!Number.isInteger(numericPort) || numericPort < 1 || numericPort > 65535) return null;

  const current = new URL(window.location.origin);
  const runpodMatch = /^([a-z0-9-]+)\.proxy\.runpod\.net$/i.exec(current.hostname);
  if (runpodMatch) {
    const label = runpodMatch[1];
    const idx = label.lastIndexOf("-");
    if (idx > 0) {
      current.hostname = `${label.slice(0, idx)}-${numericPort}.proxy.runpod.net`;
      current.port = "";
      current.pathname = "/";
      current.search = "";
      current.hash = "";
      return current.toString();
    }
  }

  current.port = String(numericPort);
  current.pathname = "/";
  current.search = "";
  current.hash = "";
  return current.toString();
};

const _tbStatusCache = {
  expiresAt: 0,
  data: null,
};

window.getTensorBoardStatus = async function (opts = {}) {
  opts.screen?.check();
  const force = Boolean(opts.force);
  const now = Date.now();
  if (!force && _tbStatusCache.data && _tbStatusCache.expiresAt > now) return _tbStatusCache.data;

  const data = await (opts.screen ? opts.screen.json("/api/tensorboard/status") : fetchJson("/api/tensorboard/status"));
  _tbStatusCache.data = data || {};
  _tbStatusCache.expiresAt = now + 5_000;
  return data;
};

window.getTensorBoardSourceStatus = async function (source, opts = {}) {
  const payload = await window.getTensorBoardStatus(opts);
  opts.screen?.check();
  if (!payload || typeof payload !== "object") return null;
  const info = payload.sources?.[source];
  if (!info) return null;
  const last = info.latest_mtime ? new Date(info.latest_mtime * 1000).toLocaleString() : null;
  return {...info, reason: !payload.server?.reachable ? payload.server?.reason || "Server unavailable"
    : last ? `Last log write: ${last}` : info.reason};
};

window.openTensorBoard = async function (source, opts = {}) {
  const dialog = document.createElement("dialog");
  dialog.style.cssText = "width:min(560px,calc(100vw - 48px));box-sizing:border-box;background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:12px;padding:20px";
  const title = document.createElement("h3");
  title.textContent = `${opts.label || source} · TensorBoard`;
  const status = document.createElement("p");
  status.setAttribute("role", "status");
  const label = document.createElement("label");
  label.textContent = "Recent runs";
  const select = document.createElement("select");
  select.setAttribute("aria-label", "Recent TensorBoard runs");
  select.style.cssText = "display:block;width:100%;margin:8px 0 16px";
  const detail = document.createElement("p");
  detail.style.overflowWrap = "anywhere";
  const actions = document.createElement("div");
  actions.style.cssText = "display:flex;flex-wrap:wrap;gap:8px";
  function button(text, action) {
    const btn = document.createElement("button");
    btn.type = "button"; btn.className = "btn secondary"; btn.textContent = text;
    btn.onclick = action; actions.append(btn); return btn;
  }
  let payload, runs = [];
  function selected() {
    const run = runs.find(r => r.name === select.value);
    open.disabled = !payload?.server?.reachable || !run?.loaded;
    detail.textContent = run ? `${run.recent ? "Recent log writes" : "Last log write"}: ${new Date(run.latest_mtime * 1000).toLocaleString()} · ${run.path}${run.loaded ? "" : " · Waiting for TensorBoard to load this run"}` : "No runs found. Enable TensorBoard logging in this trainer, then start a training run.";
  }
  const open = button("Open selected run", () => {
    const run = runs.find(r => r.name === select.value);
    if (!run?.loaded || !payload?.server?.reachable) return;
    const url = new URL(window.buildPortUrl(payload.port));
    const escaped = run.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    url.hash = `scalars&runFilter=${encodeURIComponent(`^${escaped}$`)}`;
    window.open(url.toString(), "_blank", "noopener,noreferrer");
  });
  open.disabled = true;
  const start = button("Start TensorBoard", async () => {
    start.disabled = true;
    try {
      await fetchJson("/api/tensorboard/start", {method: "POST"});
      await refresh();
    } catch (e) { status.textContent = e.message || String(e); }
  });
  const reload = button("Refresh", () => refresh());
  button("Close", () => dialog.close());
  async function refresh() {
    reload.disabled = true;
    try {
      payload = await window.getTensorBoardStatus({force: true, screen: opts.screen});
      if (!dialog.isConnected) return;
      runs = payload.sources?.[source]?.runs || [];
      status.textContent = payload.server.reason;
      start.hidden = !payload.server.can_start;
      start.disabled = false;
      const previous = select.value;
      select.replaceChildren(...runs.map(run => {
        const option = document.createElement("option");
        option.value = run.name;
        option.textContent = `${run.label || run.name} · ${new Date(run.latest_mtime * 1000).toLocaleString()}`;
        return option;
      }));
      if (runs.some(r => r.name === previous)) select.value = previous;
      select.disabled = !runs.length;
      selected();
    } catch (e) { status.textContent = e.message || String(e); open.disabled = true; start.hidden = true; }
    finally { reload.disabled = false; }
  }
  select.onchange = selected;
  dialog.append(title, status, label, select, detail, actions);
  document.body.append(dialog);
  dialog.addEventListener("close", () => dialog.remove(), {once:true});
  dialog.showModal();
  await refresh();
  return true;
};

window.setTensorBoardStatus = function (status) {
  _tbStatusCache.data = status;
  _tbStatusCache.expiresAt = Date.now() + 5_000;
};

function renderStorageUsage(label, meter, disk) {
  const valid = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
  const total = valid(disk?.total) && disk.total > 0 ? disk.total : null;
  const free = valid(disk?.free) ? disk.free : null;
  const used = valid(disk?.used) ? disk.used : total !== null && free !== null ? Math.max(0, total - free) : null;
  const bytes = value => value === 0 ? '0 B' : formatBytes(value);
  const text = total !== null && free !== null
    ? `${disk?.estimated ? 'About ' : ''}${bytes(free)} free of ${bytes(total)}`
    : total !== null && used !== null ? `${bytes(used)} of ${bytes(total)} ${disk?.capacity_source === 'runpod' ? 'in workspace' : 'used'}`
    : total !== null ? `${bytes(total)} capacity · usage unavailable`
    : used !== null ? `${bytes(used)} used · capacity unavailable` : 'Storage unavailable';
  if (label) label.textContent = text;
  if (!meter) return;
  const ratio = total !== null && used !== null ? Math.min(100, used / total * 100) : null;
  meter.dataset.state = ratio === null ? 'unknown' : ratio >= 95 ? 'full' : ratio >= 80 ? 'high' : 'normal';
  meter.setAttribute('role', 'img');
  meter.setAttribute('aria-label', ratio === null ? text : `${text}; ${Math.round(ratio)}% of capacity`);
  meter.querySelector('i').style.width = `${ratio ?? 0}%`;
}

window.sanitizeHttpUrl = function (rawUrl, opts = {}) {
  if (!rawUrl) return null;
  try {
    const parsed = new URL(rawUrl, window.location.origin);
    if (!["http:", "https:"].includes(parsed.protocol)) return null;
    if (opts.sameOrigin && parsed.origin !== window.location.origin) return null;

    const allowedPrefixes = Array.isArray(opts.allowedPathPrefixes) ? opts.allowedPathPrefixes : [];
    if (allowedPrefixes.length > 0) {
      const allowed = allowedPrefixes.some(prefix => parsed.pathname === prefix || parsed.pathname.startsWith(prefix));
      if (!allowed) return null;
    }

    return parsed.toString();
  } catch (e) {
    return null;
  }
};

// Build service URL respecting RunPod proxy subdomain pattern <id>-<port>.proxy.runpod.net
window.serviceUrl = function (name) {
  if (name === "comfy" && window.controlPilotSettings?.comfy_access?.enabled) return new URL("/comfy/", location.origin).href;
  const definition = window.serviceDefinitions?.[name];
  const port = definition?.port;
  if (!definition?.capabilities?.open || !port) return null;
  return window.buildPortUrl(port);
};
