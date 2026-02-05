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
