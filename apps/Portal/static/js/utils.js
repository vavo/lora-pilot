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
  if (!res.ok) {
    if (res.status === 401 && typeof window.showControlPilotLogin === "function") {
      window.showControlPilotLogin("ControlPilot password required");
    }
    const txt = await res.text();
    throw new Error(txt || res.statusText);
  }
  
  // Handle empty responses or non-JSON content
  const contentType = res.headers.get('content-type');
  if (!contentType || !contentType.includes('application/json')) {
    // Return empty object for non-JSON responses to avoid parsing errors
    return {};
  }
  
  const text = await res.text();
  if (!text.trim()) {
    // Return empty object for empty responses
    return {};
  }
  
  try {
    return JSON.parse(text);
  } catch (e) {
    console.warn('Failed to parse JSON response:', text, e);
    // Return empty object instead of throwing
    return {};
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
  const force = Boolean(opts.force);
  const now = Date.now();
  if (!force && _tbStatusCache.data && _tbStatusCache.expiresAt > now) return _tbStatusCache.data;

  const data = await fetchJson("/api/tensorboard/status");
  _tbStatusCache.data = data || {};
  _tbStatusCache.expiresAt = now + 5_000;
  return data;
};

window.getTensorBoardSourceStatus = async function (source, opts = {}) {
  const payload = await window.getTensorBoardStatus(opts);
  if (!payload || typeof payload !== "object") return null;
  return payload.sources && payload.sources[source] ? payload.sources[source] : null;
};

window.openTensorBoard = async function (source, opts = {}) {
  const tb = await window.getTensorBoardSourceStatus(source, opts);
  const label = typeof opts.label === "string" && opts.label ? opts.label : "TensorBoard";
  if (!tb) {
    if (typeof opts.onError === "function") {
      opts.onError(`No TensorBoard metadata for ${label}`);
      return false;
    }
    alert(`No TensorBoard metadata for ${label}`);
    return false;
  }

  if (!tb.ready) {
    const msg = tb.reason || `${label} has no TensorBoard events yet.`;
    if (!opts.allowUnavailable) {
      if (typeof opts.onError === "function") {
        opts.onError(msg);
        return false;
      }
      alert(msg);
      return false;
    }
  }

  const payload = await window.getTensorBoardStatus(opts);
  const tbUrl = window.buildPortUrl(payload.port || 4444);
  if (!tbUrl) return false;
  window.open(tbUrl, "_blank", "noopener,noreferrer");
  return true;
};

window.setTensorBoardStatus = function (status) {
  _tbStatusCache.data = status;
  _tbStatusCache.expiresAt = Date.now() + 5_000;
};

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
  const ports = {
    "jupyter": 8888,
    "code-server": 8443,
    "comfy": 5555,
    "kohya": 6666,
    "diffpipe": 4444,
    "invoke": 9090,
    "ai-toolkit": 8675,
  };
  const port = ports[name];
  if (!port || name === "controlpilot") return null;
  return window.buildPortUrl(port);
};
