const serviceVersions = {};
const serviceUpdatePollers = {};

window.initServices = async function () {
  await loadServices();
};

function iconSvg(name) {
  if (name === "play") {
    return `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M8 5v14l11-7L8 5Z" fill="currentColor"/></svg>`;
  }
  if (name === "restart") {
    return `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M21 12a9 9 0 1 1-3.1-6.7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M21 4v6h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  }
  if (name === "stop") {
    return `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7 7h10v10H7V7Z" fill="currentColor"/></svg>`;
  }
  if (name === "logs") {
    return `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M6 2h9l3 3v17H6V2Zm8 1.5V6h2.5L14 3.5ZM8 10h8v2H8v-2Zm0 4h8v2H8v-2Zm0 4h6v2H8v-2Z" fill="currentColor"/></svg>`;
  }
  if (name === "external") {
    return `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M14 4h6v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 14 20 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M20 14v6H4V4h6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  }
  return "";
}

function stateBadge(svc) {
  const raw = (svc.state_raw || "").toUpperCase();
  const cls = raw === "RUNNING" ? "running" : raw === "STARTING" ? "starting" : "stopped";
  const dotCls = raw === "RUNNING" ? "green" : raw === "STARTING" ? "orange" : "red";
  return { cls, dotCls, raw: raw || "UNKNOWN" };
}

function servicePortLabel(name) {
  const ports = {
    jupyter: 8888,
    "code-server": 8443,
    comfy: 5555,
    kohya: 6666,
    diffpipe: 4444,
    invoke: 9090,
    "ai-toolkit": 8675,
    copilot: 7879,
  };
  const port = ports[name];
  return port ? `:${port}` : "";
}

function serviceDomId(name) {
  return String(name || "").replace(/[^a-zA-Z0-9_-]/g, "-");
}

function versionText(info) {
  if (!info) return "Version: unavailable";
  if (info.installed && info.latest && info.update_available) return `Version: ${info.installed} -> ${info.latest}`;
  if (info.installed && info.latest) return `Version: ${info.installed} (latest)`;
  if (info.installed) return `Version: ${info.installed}`;
  if (info.detail) return `Version: ${info.detail}`;
  return "Version: unknown";
}

function renderServiceVersion(name, info) {
  const domId = serviceDomId(name);
  const versionEl = document.getElementById(`svc-version-${domId}`);
  const buttonEl = document.getElementById(`svc-update-${domId}`);
  if (!versionEl || !buttonEl) return;

  versionEl.textContent = versionText(info);
  const canUpdate = !!(info && info.update_supported && info.update_available);
  if (canUpdate) {
    buttonEl.classList.remove("is-hidden");
    buttonEl.disabled = false;
    buttonEl.title = info.latest ? `Install ${info.latest}` : "Install update";
  } else {
    buttonEl.classList.add("is-hidden");
    buttonEl.disabled = false;
    buttonEl.title = "No update available";
  }
}

function renderServiceUpdateStatus(name, status) {
  const domId = serviceDomId(name);
  const statusEl = document.getElementById(`svc-update-status-${domId}`);
  const buttonEl = document.getElementById(`svc-update-${domId}`);
  if (!statusEl || !buttonEl || !status) return;

  statusEl.classList.remove("is-hidden", "ok", "error", "running");
  if (status.state === "running") {
    const line = (status.last_line || "").trim();
    statusEl.textContent = line ? `Updating: ${line}` : "Updating...";
    statusEl.classList.add("running");
    buttonEl.disabled = true;
    return;
  }
  if (status.state === "done") {
    statusEl.textContent = status.installed_after ? `Updated: ${status.installed_after}` : "Update finished";
    statusEl.classList.add("ok");
    buttonEl.disabled = false;
    return;
  }
  if (status.state === "error") {
    const msg = status.error || status.last_line || "unknown error";
    statusEl.textContent = `Update failed: ${msg}`;
    statusEl.classList.add("error");
    buttonEl.disabled = false;
    return;
  }
  statusEl.classList.add("is-hidden");
  statusEl.textContent = "";
  buttonEl.disabled = false;
}

async function fetchServiceUpdateStatus(name) {
  try {
    return await fetchJson(`/api/services/${encodeURIComponent(name)}/update/status`);
  } catch (e) {
    return null;
  }
}

function stopServiceUpdatePolling(name) {
  const poller = serviceUpdatePollers[name];
  if (!poller) return;
  clearInterval(poller);
  delete serviceUpdatePollers[name];
}

async function startServiceUpdatePolling(name) {
  if (serviceUpdatePollers[name]) return;
  const tick = async () => {
    const status = await fetchServiceUpdateStatus(name);
    if (!status) return null;
    renderServiceUpdateStatus(name, status);
    if (status.state !== "running") {
      stopServiceUpdatePolling(name);
      if (status.state === "done") await loadServices();
    }
    return status;
  };
  const first = await tick();
  if (!first || first.state !== "running") return;
  serviceUpdatePollers[name] = setInterval(() => {
    tick().catch(() => {});
  }, 2000);
}

async function loadServiceVersions(services) {
  try {
    const versions = await fetchJson("/api/services/versions");
    const byName = {};
    versions.forEach(info => {
      byName[info.name] = info;
      serviceVersions[info.name] = info;
    });
    services.forEach(svc => renderServiceVersion(svc.name, byName[svc.name] || null));

    const supported = services.filter(svc => !!(byName[svc.name] && byName[svc.name].update_supported));
    const statuses = await Promise.all(supported.map(svc => fetchServiceUpdateStatus(svc.name)));
    statuses.forEach((status, index) => {
      const serviceName = supported[index].name;
      if (!status) return;
      renderServiceUpdateStatus(serviceName, status);
      if (status.state === "running") {
        startServiceUpdatePolling(serviceName).catch(() => {});
      }
    });
  } catch (e) {
    services.forEach(svc => renderServiceVersion(svc.name, null));
  }
}

async function loadServices() {
  const status = document.getElementById("svc-status");
  const list = document.getElementById("services-list");
  if (!status || !list) return;
  status.textContent = "Loading services...";
  list.classList.add("is-hidden");
  list.innerHTML = "";
  try {
    const data = await fetchJson("/api/services");
    data.forEach(svc => {
      const openUrl = serviceUrl(svc.name);
      const badge = stateBadge(svc);
      const running = svc.running === true || badge.raw === "RUNNING" || badge.raw === "STARTING";

      const card = document.createElement("div");
      card.className = "svc-card";
      const domId = serviceDomId(svc.name);

      const nameHtml = openUrl
        ? `<a class="svc-link" href="${openUrl}" target="_blank" rel="noopener noreferrer" title="Open ${svc.display}">${svc.display}<span class="svc-open-icon">${iconSvg("external")}</span></a>`
        : `<strong>${svc.display}</strong>`;

      const scheduleStartDisabled = running;
      const scheduleRestartDisabled = !running;
      const scheduleStopDisabled = !running;
      const portLabel = servicePortLabel(svc.name);
      const hasAutostart = typeof svc.autostart === "boolean";
      const autostartChecked = hasAutostart && svc.autostart ? "checked" : "";
      const autostartDisabled = hasAutostart ? "" : "disabled";
      const autostartLabel = hasAutostart ? "Auto-start on boot" : "Auto-start unknown";

      card.innerHTML = `
        <div class="svc-top">
          <div class="svc-main">
            <div class="svc-name">
              <span class="dot ${badge.dotCls}"></span>
              ${nameHtml}
            </div>
            <div class="svc-version-row">
              <span class="svc-version mono-sm" id="svc-version-${domId}">Version: checking...</span>
              <button class="btn secondary svc-update-btn is-hidden" id="svc-update-${domId}" type="button" onclick="startServiceUpdate('${svc.name}')">Update</button>
            </div>
            <div class="svc-update-status mono-sm is-hidden" id="svc-update-status-${domId}"></div>
          </div>
          <div class="svc-controls">
            <div class="svc-meta">
              <span class="svc-pill ${badge.cls}">${badge.raw}</span>
              ${portLabel ? `<span class="svc-port">Port ${portLabel}</span>` : ""}
            </div>
            <label class="svc-autostart" title="${autostartLabel}">
              <input class="svc-switch" type="checkbox" ${autostartChecked} ${autostartDisabled} onchange="toggleServiceAutostart('${svc.name}', this)" />
              <span>Auto-start</span>
            </label>
            <div class="svc-actions">
              <button class="btn icon" data-action="start" title="Start" ${scheduleStartDisabled ? "disabled" : ""} onclick="serviceAction('${svc.name}','start')">${iconSvg("play")}</button>
              <button class="btn icon" data-action="restart" title="Restart" ${scheduleRestartDisabled ? "disabled" : ""} onclick="serviceAction('${svc.name}','restart')">${iconSvg("restart")}</button>
              <button class="btn icon danger" data-action="stop" title="Stop" ${scheduleStopDisabled ? "disabled" : ""} onclick="serviceAction('${svc.name}','stop')">${iconSvg("stop")}</button>
              <button class="btn icon" data-action="logs" title="View logs" onclick="viewServiceLog('${svc.name}')">${iconSvg("logs")}</button>
            </div>
          </div>
        </div>
      `;
      list.appendChild(card);
    });
    await loadServiceVersions(data);
    status.textContent = "";
    list.classList.remove("is-hidden");
  } catch (e) {
    status.textContent = `Error: ${e.message || e}`;
  }
}

window.serviceAction = async function (name, action) {
  try {
    await fetchJson(`/api/services/${encodeURIComponent(name)}/${action}`, { method: "POST" });
    await loadServices();
  } catch (e) {
    alert(`Service action failed: ${e.message || e}`);
  }
};

window.startServiceUpdate = async function (name) {
  const info = serviceVersions[name] || null;
  const domId = serviceDomId(name);
  const buttonEl = document.getElementById(`svc-update-${domId}`);
  if (!buttonEl) return;

  buttonEl.disabled = true;
  renderServiceUpdateStatus(name, { state: "running", last_line: "Starting update..." });
  try {
    const payload = {};
    if (info && info.source === "pip" && info.latest) payload.target_version = info.latest;
    const result = await fetchJson(`/api/services/${encodeURIComponent(name)}/update/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    renderServiceUpdateStatus(name, result);
    await startServiceUpdatePolling(name);
  } catch (e) {
    renderServiceUpdateStatus(name, { state: "error", error: e.message || String(e) });
    alert(`Failed to start update: ${e.message || e}`);
    buttonEl.disabled = false;
  }
};

window.toggleServiceAutostart = async function (name, toggle) {
  if (!toggle) return;
  const enabled = !!toggle.checked;
  toggle.disabled = true;
  try {
    await fetchJson(`/api/services/${encodeURIComponent(name)}/settings/autostart`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
  } catch (e) {
    toggle.checked = !enabled;
    alert(`Failed to update auto-start: ${e.message || e}`);
  } finally {
    toggle.disabled = false;
  }
};

window.viewServiceLog = async function (name) {
  try {
    const res = await fetchJson(`/api/services/${encodeURIComponent(name)}/log?lines=200`);
    const modal = document.getElementById("svc-log-modal");
    const title = document.getElementById("svc-log-title");
    const content = document.getElementById("svc-log-content");
    if (title) title.textContent = `Service Log: ${name} (${res.path})`;
    if (content) content.textContent = res.log || "";
    if (modal) modal.classList.add("show");
  } catch (e) {
    alert(`Failed to load log: ${e.message || e}`);
  }
};

window.closeServiceLog = function (evt) {
  if (evt && evt.target) {
    const t = evt.target;
    const isBackdrop = t.id === "svc-log-modal";
    const isCloseBtn = t.classList && t.classList.contains("modal-close");
    if (!isBackdrop && !isCloseBtn) return;
  }
  const modal = document.getElementById("svc-log-modal");
  if (modal) modal.classList.remove("show");
};
