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
