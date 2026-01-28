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
  const host = window.location.hostname;
  const proto = window.location.protocol;
  if (host.includes(".proxy.runpod.net")) {
    const parts = host.split(".");
    const first = parts[0];
    const idx = first.lastIndexOf("-");
    if (idx !== -1) {
      const base = first.slice(0, idx);
      const newHost = [base + "-" + port, ...parts.slice(1)].join(".");
      return `${proto}//${newHost}/`;
    }
  }
  return `${proto}//${host}:${port}/`;
};
