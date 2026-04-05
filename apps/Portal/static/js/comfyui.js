let comfyWebSocket = null;
let comfyStatusTimer = null;
let comfyReconnectTimer = null;
let comfyActive = false;
let previewEnabled = true;
let imageCount = 0;
let lastGeneratedImage = null;
let comfyPort = "5555";
let comfyStatusFailures = 0;
const COMFY_STATUS_FAILURE_THRESHOLD = 3;
const COMFY_PREVIEW_PANEL_STORAGE_KEY = "controlpilot_comfy_preview_collapsed";

function isComfyViewMounted() {
  return !!document.getElementById("comfy-iframe");
}

function isDesktopComfyLayout() {
  return window.matchMedia("(min-width: 1025px)").matches;
}

function isPreviewPanelCollapsed() {
  try {
    return localStorage.getItem(COMFY_PREVIEW_PANEL_STORAGE_KEY) === "1";
  } catch (e) {
    return false;
  }
}

function setPreviewPanelCollapsed(collapsed) {
  const shell = document.getElementById("comfy-shell");
  const toggle = document.getElementById("comfy-preview-toggle");
  const effectiveCollapsed = !!collapsed && isDesktopComfyLayout();
  if (shell) shell.classList.toggle("panel-collapsed", effectiveCollapsed);
  if (toggle) {
    const label = effectiveCollapsed ? "Expand preview panel" : "Collapse preview panel";
    toggle.setAttribute("aria-expanded", effectiveCollapsed ? "false" : "true");
    toggle.setAttribute("aria-label", label);
    toggle.title = label;
  }
}

function persistPreviewPanelCollapsed(collapsed) {
  try {
    localStorage.setItem(COMFY_PREVIEW_PANEL_STORAGE_KEY, collapsed ? "1" : "0");
  } catch (e) {}
}

function clearComfyTimers() {
  if (comfyStatusTimer) {
    clearInterval(comfyStatusTimer);
    comfyStatusTimer = null;
  }
  if (comfyReconnectTimer) {
    clearTimeout(comfyReconnectTimer);
    comfyReconnectTimer = null;
  }
}

window.stopComfyUI = function () {
  comfyActive = false;
  clearComfyTimers();
  comfyStatusFailures = 0;
  if (comfyWebSocket) {
    try {
      comfyWebSocket.onclose = null;
      comfyWebSocket.onerror = null;
      comfyWebSocket.close();
    } catch (e) {}
    comfyWebSocket = null;
  }
  const iframeEl = document.getElementById("comfy-iframe");
  if (iframeEl) {
    try {
      iframeEl.src = "about:blank";
    } catch (e) {}
  }
  window.removeEventListener("resize", handleComfyUILayoutChange);
};

window.initComfyUI = function () {
  const iframeEl = document.getElementById("comfy-iframe");
  if (!iframeEl) return;
  comfyActive = true;

  const toggleBtn = document.getElementById("preview-toggle");
  const clearBtn = document.getElementById("clear-preview");
  const panelToggleBtn = document.getElementById("comfy-preview-toggle");
  if (toggleBtn) toggleBtn.onclick = togglePreview;
  if (clearBtn) clearBtn.onclick = clearPreview;
  if (panelToggleBtn) {
    panelToggleBtn.onclick = function () {
      const nextCollapsed = !document.getElementById("comfy-shell")?.classList.contains("panel-collapsed");
      persistPreviewPanelCollapsed(nextCollapsed);
      setPreviewPanelCollapsed(nextCollapsed);
    };
  }

  previewEnabled = true;
  imageCount = 0;
  lastGeneratedImage = null;
  comfyStatusFailures = 0;
  updateImageCount();
  setPreviewPanelCollapsed(isPreviewPanelCollapsed());
  window.removeEventListener("resize", handleComfyUILayoutChange);
  window.addEventListener("resize", handleComfyUILayoutChange);

  updateConnectionStatus("connecting", "Connecting to ComfyUI...");
  checkComfyUIStatus();
  connectWebSocket();

  clearComfyTimers();
  comfyStatusTimer = setInterval(checkComfyUIStatus, 10000);

  setTimeout(loadLastGeneratedImage, 2000);
};

function handleComfyUILayoutChange() {
  setPreviewPanelCollapsed(isPreviewPanelCollapsed());
}

function updateImageCount() {
  const countEl = document.getElementById("image-count");
  if (countEl) countEl.textContent = String(imageCount);
}

async function checkComfyUIStatus() {
  try {
    const response = await fetch("/api/comfy/status");
    const status = await response.json();

    const statusEl = document.getElementById("comfy-status");
    const portEl = document.getElementById("comfy-port");
    const iframeEl = document.getElementById("comfy-iframe");

    if (status.status === "running") {
      comfyStatusFailures = 0;
      comfyPort = status.port || "5555";
      if (statusEl) {
        statusEl.className = "status-indicator status-connected";
        statusEl.textContent = "Running";
      }
      if (portEl) portEl.textContent = comfyPort;
      if (iframeEl && (!iframeEl.src || iframeEl.src === "about:blank")) {
        iframeEl.src = getComfyUIUrl(comfyPort);
      }
    } else {
      comfyStatusFailures += 1;
      const stillRetrying = comfyStatusFailures < COMFY_STATUS_FAILURE_THRESHOLD;
      if (statusEl) {
        statusEl.className = stillRetrying ? "status-indicator status-connecting" : "status-indicator status-disconnected";
        statusEl.textContent = stillRetrying ? `Checking... (${comfyStatusFailures}/${COMFY_STATUS_FAILURE_THRESHOLD})` : "Stopped";
      }
      if (portEl) portEl.textContent = status.port || comfyPort || "5555";
      if (!stillRetrying && iframeEl) iframeEl.src = "about:blank";
    }
  } catch (error) {
    comfyStatusFailures += 1;
    const stillRetrying = comfyStatusFailures < COMFY_STATUS_FAILURE_THRESHOLD;
    const statusEl = document.getElementById("comfy-status");
    const iframeEl = document.getElementById("comfy-iframe");
    if (statusEl) {
      statusEl.className = stillRetrying ? "status-indicator status-connecting" : "status-indicator status-disconnected";
      statusEl.textContent = stillRetrying ? `Retrying... (${comfyStatusFailures}/${COMFY_STATUS_FAILURE_THRESHOLD})` : "Error";
    }
    if (!stillRetrying && iframeEl) iframeEl.src = "about:blank";
  }
}

function getComfyUIUrl(port) {
  return window.buildPortUrl(port) || "about:blank";
}

function sanitizePreviewImageUrl(rawUrl) {
  return window.sanitizeHttpUrl(rawUrl, {
    sameOrigin: true,
    allowedPathPrefixes: ["/proxy/comfy/", "/output/", "/thumbs/", "/invoke/"],
  });
}

function renderPlaceholder(container, message) {
  if (!container) return;
  const placeholder = document.createElement("div");
  placeholder.className = "preview-placeholder";
  placeholder.textContent = message;
  container.replaceChildren(placeholder);
}

async function loadLastGeneratedImage() {
  try {
    const response = await fetch("/api/comfy/latest-image");
    if (!response.ok) return;
    const data = await response.json();
    if (typeof data.image_count === "number") {
      imageCount = data.image_count;
      updateImageCount();
    }
    if (data.image) {
      displayLastImage(data.image);
    }
  } catch (error) {
    if (!lastGeneratedImage) {
      showPlaceholder("No images generated yet");
    }
  }
}

function displayLastImage(imageInfo) {
  const container = document.getElementById("preview-container");
  const infoEl = document.getElementById("preview-info");
  const dimensionsEl = document.getElementById("preview-dimensions");
  const timeEl = document.getElementById("preview-time");

  if (!container || !infoEl || !dimensionsEl || !timeEl) return;

  lastGeneratedImage = imageInfo;

  const img = document.createElement("img");
  img.className = "preview-image";

  if (imageInfo.url && imageInfo.url.startsWith("/proxy/comfy/view")) {
    const parsed = new URL(imageInfo.url, window.location.origin);
    const filename = parsed.searchParams.get("filename");
    const subfolder = parsed.searchParams.get("subfolder") || imageInfo.subfolder || "";
    if (filename) {
      img.src = getComfyUIImageUrl(filename, subfolder, comfyPort);
    }
  } else if (imageInfo.url) {
    const safeUrl = sanitizePreviewImageUrl(imageInfo.url);
    if (!safeUrl) {
      showPlaceholder("Preview unavailable");
      return;
    }
    img.src = safeUrl;
  }

  dimensionsEl.textContent = imageInfo.dimensions || "-";
  timeEl.textContent = imageInfo.generated_at ? new Date(imageInfo.generated_at).toLocaleTimeString() : "-";

  container.replaceChildren(img);
  infoEl.classList.remove("is-hidden");
}

function showPlaceholder(message) {
  const container = document.getElementById("preview-container");
  const infoEl = document.getElementById("preview-info");
  renderPlaceholder(container, message);
  if (infoEl) infoEl.classList.add("is-hidden");
}

function connectWebSocket() {
  if (!comfyActive || !isComfyViewMounted()) return;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/comfy`;

  if (comfyWebSocket) {
    try {
      comfyWebSocket.close();
    } catch (e) {}
    comfyWebSocket = null;
  }

  try {
    comfyWebSocket = new WebSocket(wsUrl);

    comfyWebSocket.onopen = function () {
      updateConnectionStatus("connected", "Connected to ComfyUI");
    };

    comfyWebSocket.onmessage = function (event) {
      if (!previewEnabled) return;

      try {
        const data = JSON.parse(event.data);
        if (data.type === "executed" && data.data?.node) {
          for (const nodeId in data.data.node) {
            const nodeOutputs = data.data.node[nodeId];
            if (nodeOutputs.images && nodeOutputs.images.length > 0) {
              const image = nodeOutputs.images[0];
              displayImage(image);
            }
          }
        }
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    };

    comfyWebSocket.onclose = function () {
      updateConnectionStatus("disconnected", "Disconnected from ComfyUI");
      if (!comfyActive || !isComfyViewMounted()) return;
      comfyReconnectTimer = setTimeout(connectWebSocket, 3000);
    };

    comfyWebSocket.onerror = function (error) {
      updateConnectionStatus("disconnected", "Connection error");
      // Comfy websocket errors are often transient when the service restarts.
    };
  } catch (error) {
    updateConnectionStatus("disconnected", "Failed to connect");
  }
}

function updateConnectionStatus(status, message) {
  const statusEl = document.getElementById("connection-status");
  if (!statusEl) return;
  statusEl.className = `status-indicator status-${status}`;
  statusEl.textContent = message;
}

function displayImage(imageData) {
  const container = document.getElementById("preview-container");
  const infoEl = document.getElementById("preview-info");
  const dimensionsEl = document.getElementById("preview-dimensions");
  const timeEl = document.getElementById("preview-time");
  if (!container || !infoEl || !dimensionsEl || !timeEl) return;

  const img = document.createElement("img");
  img.className = "preview-image";

  if (imageData.filename) {
    img.src = getComfyUIImageUrl(imageData.filename, imageData.subfolder || "", comfyPort);
    if (imageData.size) {
      dimensionsEl.textContent = `${imageData.size[0]}x${imageData.size[1]}`;
    }
  } else if (imageData.url) {
    const safeUrl = sanitizePreviewImageUrl(imageData.url);
    if (!safeUrl) {
      showPlaceholder("Preview unavailable");
      return;
    }
    img.src = safeUrl;
  }

  const now = new Date();
  timeEl.textContent = now.toLocaleTimeString();
  imageCount += 1;
  updateImageCount();

  container.replaceChildren(img);
  infoEl.classList.remove("is-hidden");

  lastGeneratedImage = {
    url: img.src,
    dimensions: dimensionsEl.textContent,
    generated_at: now.toISOString(),
  };
}

function getComfyUIImageUrl(filename, subfolder, port) {
  const base = getComfyUIUrl(port).replace(/\/$/, "");
  let url = `${base}/view?filename=${encodeURIComponent(filename)}`;
  if (subfolder) {
    url += `&subfolder=${encodeURIComponent(subfolder)}`;
  }
  return url;
}

function togglePreview() {
  previewEnabled = !previewEnabled;
  const toggleBtn = document.getElementById("preview-toggle");
  if (toggleBtn) toggleBtn.textContent = previewEnabled ? "Pause Preview" : "Resume Preview";
  if (!previewEnabled) {
    clearPreview();
  } else if (lastGeneratedImage) {
    displayLastImage(lastGeneratedImage);
  }
}

function clearPreview() {
  const container = document.getElementById("preview-container");
  renderPlaceholder(container, "Preview paused");
  const infoEl = document.getElementById("preview-info");
  if (infoEl) infoEl.classList.add("is-hidden");
}
