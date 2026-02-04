let comfyWebSocket = null;
let comfyStatusTimer = null;
let previewEnabled = true;
let imageCount = 0;
let lastGeneratedImage = null;
let comfyPort = "5555";

window.initComfyUI = function () {
  const iframeEl = document.getElementById("comfy-iframe");
  if (!iframeEl) return;

  const toggleBtn = document.getElementById("preview-toggle");
  const clearBtn = document.getElementById("clear-preview");
  if (toggleBtn) toggleBtn.onclick = togglePreview;
  if (clearBtn) clearBtn.onclick = clearPreview;

  previewEnabled = true;
  imageCount = 0;
  lastGeneratedImage = null;
  updateImageCount();

  updateConnectionStatus("connecting", "Connecting to ComfyUI...");
  checkComfyUIStatus();
  connectWebSocket();

  if (comfyStatusTimer) clearInterval(comfyStatusTimer);
  comfyStatusTimer = setInterval(checkComfyUIStatus, 10000);

  setTimeout(loadLastGeneratedImage, 2000);
};

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
      if (statusEl) {
        statusEl.className = "status-indicator status-disconnected";
        statusEl.textContent = "Stopped";
      }
      if (portEl) portEl.textContent = status.port || "5555";
      if (iframeEl) iframeEl.src = "about:blank";
    }
  } catch (error) {
    const statusEl = document.getElementById("comfy-status");
    if (statusEl) {
      statusEl.className = "status-indicator status-disconnected";
      statusEl.textContent = "Error";
    }
  }
}

function getComfyUIUrl(port) {
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
    img.src = imageInfo.url;
  }

  dimensionsEl.textContent = imageInfo.dimensions || "-";
  timeEl.textContent = imageInfo.generated_at ? new Date(imageInfo.generated_at).toLocaleTimeString() : "-";

  container.innerHTML = "";
  container.appendChild(img);
  infoEl.classList.remove("is-hidden");
}

function showPlaceholder(message) {
  const container = document.getElementById("preview-container");
  const infoEl = document.getElementById("preview-info");
  if (container) container.innerHTML = `<div class="preview-placeholder">${message}</div>`;
  if (infoEl) infoEl.classList.add("is-hidden");
}

function connectWebSocket() {
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
      setTimeout(connectWebSocket, 3000);
    };

    comfyWebSocket.onerror = function (error) {
      updateConnectionStatus("disconnected", "Connection error");
      console.error("WebSocket error:", error);
    };
  } catch (error) {
    updateConnectionStatus("disconnected", "Failed to connect");
    console.error("Failed to create WebSocket:", error);
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
    img.src = imageData.url;
  }

  const now = new Date();
  timeEl.textContent = now.toLocaleTimeString();
  imageCount += 1;
  updateImageCount();

  container.innerHTML = "";
  container.appendChild(img);
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
  if (container) container.innerHTML = '<div class="preview-placeholder">Preview paused</div>';
  const infoEl = document.getElementById("preview-info");
  if (infoEl) infoEl.classList.add("is-hidden");
}
