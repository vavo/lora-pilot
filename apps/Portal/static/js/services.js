let servicesScreen = null;
const serviceVersions = {};
const serviceUpdatePollers = {};

window.initServices = async function (screen = window.createScreenLifecycle()) {
  servicesScreen = screen;
  servicesData = [];
  selectedService = "comfy";
  serviceFilter = "all";
  for (const cache of [serviceVersions, serviceUpdateStatuses]) Object.keys(cache).forEach(key => delete cache[key]);
  serviceActions.clear();
  serviceAutostartPending.clear();
  screen.onCleanup(() => {
    for (const name of Object.keys(serviceUpdatePollers)) stopServiceUpdatePolling(name);
  });
  await loadServices();
};

let servicesData = [];
let selectedService = "comfy";
let serviceFilter = "all";
const serviceUpdateStatuses = {};
const serviceActions = new Set();
const serviceAutostartPending = new Set();

function serviceEscape(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function serviceInfo(svc) {
  return svc.definition || { label: svc.display || svc.name, role: "Workspace service", description: "Manage this workspace service.", icon: "services" };
}

function serviceIcon(svc) {
  return document.querySelector(`.nav [data-section="${serviceInfo(svc).icon}"] .nav-icon`)?.innerHTML || "";
}

function stateBadge(svc) {
  if (svc.installed === false) return { cls: "stopped", raw: "NOT_INSTALLED", label: "Not installed" };
  const raw = (svc.state_raw || "UNKNOWN").toUpperCase();
  const cls = raw === "RUNNING" ? "running" : ["STARTING", "STOPPING"].includes(raw) ? "starting" : ["FATAL", "BACKOFF"].includes(raw) ? "error" : "stopped";
  const label = raw.charAt(0) + raw.slice(1).toLowerCase();
  return { cls, raw, label };
}

function visibleServices() {
  return servicesData.filter(svc => serviceFilter === "all" || (serviceFilter === "running" ? stateBadge(svc).raw === "RUNNING" : ["STOPPED", "EXITED"].includes(stateBadge(svc).raw)));
}

window.filterServices = function (filter) {
  serviceFilter = filter;
  renderServices();
};

function renderServices() {
  const list = document.getElementById("services-list");
  const visible = visibleServices();
  if (!visible.some(svc => svc.name === selectedService)) selectedService = visible[0]?.name || "";
  const counts = {};
  servicesData.forEach(svc => { const label = stateBadge(svc).label.toLowerCase(); counts[label] = (counts[label] || 0) + 1; });
  document.getElementById("svc-summary").textContent = Object.entries(counts).map(([state, count]) => `${count} ${state}`).join(" · ") || "No services available";
  document.querySelectorAll("[data-service-filter]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.serviceFilter === serviceFilter)));
  list.replaceChildren();
  visible.forEach(svc => {
    const info = serviceInfo(svc), badge = stateBadge(svc);
    const row = document.createElement("button");
    row.type = "button";
    row.className = "svc-row";
    row.dataset.service = svc.name;
    row.setAttribute("aria-pressed", String(svc.name === selectedService));
    row.setAttribute("aria-controls", "svc-detail");
    row.innerHTML = `<span class="svc-icon" aria-hidden="true">${serviceIcon(svc)}</span>
      <span class="svc-row-copy"><strong>${serviceEscape(info.label)}</strong><span class="svc-update-hint is-hidden" id="svc-hint-${serviceDomId(svc.name)}">Update available</span><span class="svc-role">${serviceEscape(info.role)}</span></span>
      <span class="svc-state ${badge.cls}">${serviceEscape(badge.label)}</span>`;
    row.onclick = () => {
      selectedService = svc.name;
      list.querySelectorAll(".svc-row").forEach(item => item.setAttribute("aria-pressed", String(item.dataset.service === selectedService)));
      renderServiceDetail();
      if (window.matchMedia("(max-width: 900px)").matches) {
        document.getElementById("svc-detail-title").focus({ preventScroll: true });
        document.getElementById("svc-detail").scrollIntoView({ block: "start" });
      }
    };
    const entry = document.createElement("div");
    entry.className = "svc-entry";
    entry.appendChild(row);
    const url = badge.raw === "RUNNING" ? serviceUrl(svc.name) : null;
    if (url) {
      const open = document.createElement("a");
      open.className = "svc-quick-open";
      open.href = url;
      open.target = "_blank";
      open.rel = "noopener noreferrer";
      open.title = `Open ${info.label}`;
      open.setAttribute("aria-label", `Open ${info.label}`);
      open.innerHTML = '<span aria-hidden="true">↗</span>';
      entry.appendChild(open);
    }
    list.appendChild(entry);
  });
  if (!visible.length) list.textContent = servicesData.length ? `No ${serviceFilter} services.` : "No services were returned by the supervisor.";
  renderServiceDetail();
  servicesData.forEach(svc => renderServiceVersion(svc.name, serviceVersions[svc.name]));
}

function renderServiceDetail() {
  const scope = servicesScreen.latest("detail");
  const detail = document.getElementById("svc-detail");
  const svc = servicesData.find(item => item.name === selectedService);
  detail.hidden = !svc;
  if (!svc) { detail.replaceChildren(); return; }
  const info = serviceInfo(svc), badge = stateBadge(svc), domId = serviceDomId(svc.name);
  const running = badge.raw === "RUNNING", starting = badge.raw === "STARTING", stopping = badge.raw === "STOPPING";
  const missing = svc.installed === false;
  const installing = serviceUpdateStatuses[svc.name]?.state === "running";
  const busy = serviceActions.has(svc.name);
  const url = running ? serviceUrl(svc.name) : null;
  const port = servicePortLabel(svc.name);
  const tbSource = serviceTensorBoardSource(svc.name);
  detail.innerHTML = `
    <button class="svc-text-button svc-back" type="button">Back to services</button>
    <header class="svc-detail-heading"><span class="svc-icon" aria-hidden="true">${serviceIcon(svc)}</span><div><h3 id="svc-detail-title" tabindex="-1">${serviceEscape(info.label)}</h3><p>${serviceEscape(info.description)}</p></div></header>
    <div class="svc-detail-meta"><span class="svc-state ${badge.cls}">${serviceEscape(badge.label)}</span>${port ? `<span>Port ${serviceEscape(port.slice(1))}</span>` : ""}</div>
    <div class="svc-actions">
      ${url ? `<a class="btn primary" href="${serviceEscape(url)}" target="_blank" rel="noopener noreferrer">Open ${serviceEscape(info.label)} <span aria-hidden="true">↗</span></a>` : ""}
      ${missing && info.capabilities?.install ? `<button class="btn primary" type="button" id="svc-install-${domId}" ${installing ? "disabled" : ""}>${installing ? "Installing…" : "Install VS Code"}</button>` : ""}
      ${!running && !missing ? `<button class="btn primary" type="button" data-action="start" ${busy || starting || stopping ? "disabled" : ""}>${starting ? "Starting…" : stopping ? "Stopping…" : "Start service"}</button>` : ""}
      ${running ? `<button class="btn secondary" type="button" data-action="restart" ${busy ? "disabled" : ""}>Restart</button>` : ""}
      ${running || starting ? `<button class="btn secondary svc-stop" type="button" data-action="stop" ${busy ? "disabled" : ""}>Stop</button>` : ""}
    </div>
    ${missing ? '<p class="svc-control-note">Optional download, about 235 MB. Installation and editor data stay in your workspace. Installation does not start the editor.</p>' : ""}
    ${info.capabilities?.disconnects_ui ? '<p class="svc-control-note">Restarting or stopping ControlPilot disconnects this interface.</p>' : ""}
    <section class="svc-detail-section svc-autostart-row"><div><label for="svc-autostart-toggle">Start with workspace</label><p>${missing ? "Install this service before enabling auto-start." : typeof svc.autostart === "boolean" ? "Automatically start this service when your workspace starts." : "Auto-start setting is unavailable."}</p></div><input id="svc-autostart-toggle" class="svc-switch" type="checkbox" role="switch" ${svc.autostart === true ? "checked" : ""} ${missing || typeof svc.autostart !== "boolean" || serviceAutostartPending.has(svc.name) ? "disabled" : ""}></section>
    <section class="svc-detail-section"><div class="svc-section-row"><div><h4>Version</h4><p id="svc-version-${domId}">Checking version…</p><p id="svc-available-${domId}" class="svc-update-hint is-hidden">Update available</p></div><button class="btn secondary svc-update-btn is-hidden" id="svc-update-${domId}" type="button">Update</button></div><p class="svc-update-status is-hidden" id="svc-update-status-${domId}" role="status"></p></section>
    ${tbSource ? `<section class="svc-detail-section"><div class="svc-section-row"><div><h4>Training metrics</h4><p id="svc-tensorboard-status-${domId}">TensorBoard: checking…</p></div><button class="svc-text-button" type="button" data-tensorboard>Open TensorBoard</button></div></section>` : ""}
    <section class="svc-detail-section svc-logs"><div class="svc-section-row"><h4>Logs</h4><button class="svc-text-button" type="button" data-log>View full log <span aria-hidden="true">↗</span></button></div><pre id="svc-log-preview" class="svc-log-pre mono">Loading log…</pre></section>`;
  detail.querySelector(".svc-back").onclick = () => {
    document.querySelector('.svc-row[aria-pressed="true"]')?.focus({ preventScroll: true });
    document.getElementById("services-list").scrollIntoView({ block: "start" });
  };
  const installButton = detail.querySelector(`#svc-install-${domId}`);
  if (installButton) installButton.onclick = () => startServiceInstall(svc.name);
  detail.querySelectorAll("[data-action]").forEach(button => button.onclick = () => serviceAction(svc.name, button.dataset.action));
  detail.querySelector("#svc-autostart-toggle").onchange = event => toggleServiceAutostart(svc.name, event.target);
  detail.querySelector(`#svc-update-${domId}`).onclick = () => startServiceUpdate(svc.name);
  detail.querySelector("[data-log]").onclick = () => viewServiceLog(svc.name);
  if (tbSource) {
    detail.querySelector("[data-tensorboard]").onclick = () => openServiceTensorBoard(svc.name);
    refreshServiceTensorBoardStatus(svc.name).catch(() => {});
  }
  if (Object.hasOwn(serviceVersions, svc.name)) renderServiceVersion(svc.name, serviceVersions[svc.name]);
  renderServiceUpdateStatus(svc.name, serviceUpdateStatuses[svc.name]);
  loadServiceLogPreview(svc.name, scope);
}

async function loadServiceLogPreview(name, scope) {
  const preview = document.getElementById("svc-log-preview");
  try {
    const result = await scope.json(`/api/services/${encodeURIComponent(name)}/log?lines=8`);
    preview.textContent = result.log || "No log output yet.";
  } catch (error) {
    if (scope.active) preview.textContent = "Log unavailable. Try View full log to retry.";
  }
}

function servicePortLabel(name) {
  const port = window.serviceDefinitions?.[name]?.port;
  return port ? `:${port}` : "";
}

function serviceTensorBoardSource(name) {
  return window.serviceDefinitions?.[name]?.capabilities?.tensorboard || "";
}

function serviceDisplayLabel(name) {
  const info = window.serviceDefinitions?.[name];
  return info?.capabilities?.tensorboard_label || info?.label || name;
}

function serviceDomId(name) {
  return String(name || "").replace(/[^a-zA-Z0-9_-]/g, "-");
}

function versionText(info) {
  if (!info) return "Version unavailable";
  if (info.installed && info.latest && info.update_available) return `Installed build: ${info.installed} → ${info.latest}`;
  if (info.installed && info.latest) return `Installed build: ${info.installed} (latest)`;
  if (info.installed) return `Installed build: ${info.installed}`;
  if (info.detail) return info.detail;
  return "Version: unknown";
}

function renderServiceVersion(name, info) {
  const domId = serviceDomId(name);
  const versionEl = document.getElementById(`svc-version-${domId}`);
  const buttonEl = document.getElementById(`svc-update-${domId}`);
  const canUpdate = !!(info && info.update_supported && info.update_available);
  document.getElementById(`svc-hint-${domId}`)?.classList.toggle("is-hidden", !canUpdate);
  document.getElementById(`svc-available-${domId}`)?.classList.toggle("is-hidden", !canUpdate);
  if (!versionEl || !buttonEl || info === undefined) return;
  versionEl.textContent = versionText(info);
  if (canUpdate) {
    buttonEl.classList.remove("is-hidden");
    buttonEl.disabled = serviceUpdateStatuses[name]?.state === "running";
    buttonEl.title = info.latest ? `Install ${info.latest}` : "Install update";
  } else {
    buttonEl.classList.add("is-hidden");
    buttonEl.disabled = false;
    buttonEl.title = "No update available";
  }
}

function renderServiceUpdateStatus(name, status) {
  if (status) serviceUpdateStatuses[name] = status;
  const installation = status?.operation === "install";
  const installButton = document.getElementById(`svc-install-${serviceDomId(name)}`);
  if (installButton && status) {
    installButton.disabled = status.state === "running";
    installButton.textContent = status.state === "running" ? "Installing…" : status.state === "error" ? "Retry installation" : "Install VS Code";
  }
  const domId = serviceDomId(name);
  const statusEl = document.getElementById(`svc-update-status-${domId}`);
  const buttonEl = document.getElementById(`svc-update-${domId}`);
  if (!statusEl || !buttonEl || !status) return;

  statusEl.classList.remove("is-hidden", "ok", "error", "running");
  if (status.state === "running") {
    const line = (status.last_line || "").trim();
    statusEl.textContent = line ? `${installation ? "Installing" : "Updating"}: ${line}` : installation ? "Installing…" : "Updating…";
    statusEl.classList.add("running");
    buttonEl.disabled = true;
    return;
  }
  if (status.state === "done") {
    statusEl.textContent = installation ? "Installed. Use Start service when ready." : status.installed_after ? `Updated: ${status.installed_after}` : "Update finished";
    statusEl.classList.add("ok");
    buttonEl.disabled = false;
    return;
  }
  if (status.state === "error") {
    const msg = status.error || status.last_line || "unknown error";
    statusEl.textContent = `${installation ? "Installation" : "Update"} failed: ${msg}`;
    statusEl.classList.add("error");
    buttonEl.disabled = false;
    return;
  }
  statusEl.classList.add("is-hidden");
  statusEl.textContent = "";
  buttonEl.disabled = false;
}

async function fetchServiceUpdateStatus(name, screen = servicesScreen) {
  if (!screen?.active) return;
  try {
    return await screen.json(`/api/services/${encodeURIComponent(name)}/update/status`);
  } catch (e) {
    if (!screen.active) return;
    return null;
  }
}

function stopServiceUpdatePolling(name) {
  const poller = serviceUpdatePollers[name];
  if (!poller) return;
  poller.dispose();
  delete serviceUpdatePollers[name];
}

async function startServiceUpdatePolling(name) {
  const screen = servicesScreen;
  if (!screen?.active || serviceUpdatePollers[name]) return;
  const polling = screen.latest(`update:${name}`);
  serviceUpdatePollers[name] = polling;
  polling.poll(async () => {
    try {
      const status = await polling.json(`/api/services/${encodeURIComponent(name)}/update/status`);
      renderServiceUpdateStatus(name, status);
      if (status.state !== "running") {
        stopServiceUpdatePolling(name);
        if (status.state === "done" && screen.active) await loadServices();
      }
    } catch (error) {
      // A transient status failure must not stop watching a server-side update.
      if (polling.active) renderServiceUpdateStatus(name, {...serviceUpdateStatuses[name], state: "running", last_line: "Status unavailable; retrying…"});
    }
  }, 2000);
}

window.stopServices = function () { servicesScreen?.dispose(); };

async function loadServiceVersions(services, screen) {
  if (!screen?.active) return;
  try {
    const versions = await screen.json("/api/services/versions");
    const byName = {};
    versions.forEach(info => {
      byName[info.name] = info;
      serviceVersions[info.name] = info;
    });
    services.forEach(svc => renderServiceVersion(svc.name, byName[svc.name] || null));

    const supported = services.filter(svc => svc.definition?.capabilities?.install || !!(byName[svc.name] && byName[svc.name].update_supported));
    const statuses = await Promise.all(supported.map(svc => fetchServiceUpdateStatus(svc.name, screen)));
    screen.check();
    statuses.forEach((status, index) => {
      const serviceName = supported[index].name;
      if (!status) return;
      renderServiceUpdateStatus(serviceName, status);
      if (status.state === "running") {
        startServiceUpdatePolling(serviceName).catch(() => {});
      }
    });
  } catch (e) {
    if (!screen.active) return;
    services.forEach(svc => { serviceVersions[svc.name] = null; renderServiceVersion(svc.name, null); });
  }
}

async function loadServices() {
  const screen = servicesScreen.latest("list");
  const status = document.getElementById("svc-status");
  const workspace = document.getElementById("svc-workspace");
  const refresh = document.getElementById("svc-refresh");
  if (!status || !workspace) return;
  status.textContent = "Loading services…";
  refresh.disabled = true;
  try {
    const data = await screen.json("/api/services");
    window.serviceDefinitions = Object.fromEntries(data.map(svc => [svc.name, svc.definition]));
    servicesData = data.sort((a, b) => (a.definition?.order ?? 99) - (b.definition?.order ?? 99));
    renderServices();
    workspace.hidden = false;
    status.textContent = "";
    await loadServiceVersions(data, screen);
  } catch (e) {
    if (!screen.active) return;
    let message = e.message || String(e);
    try { message = JSON.parse(message).detail || message; } catch (_) {}
    status.textContent = `Could not refresh services: ${message}. Try Refresh.`;
  } finally {
    if (screen.active) refresh.disabled = false;
  }
}

window.serviceAction = async function (name, action) {
  const screen = servicesScreen;
  if (!screen?.active || serviceActions.has(name)) return;
  serviceActions.add(name);
  if (selectedService === name) renderServiceDetail();
  try {
    await screen.json(`/api/services/${encodeURIComponent(name)}/${action}`, { method: "POST" });
    if (name === "copilot") window.dispatchEvent(new CustomEvent("copilot-service-action", { detail: action }));
    serviceActions.delete(name);
    await loadServices();
  } catch (e) {
    if (!screen.active) return;
    alert(`Service action failed: ${e.message || e}`);
  } finally {
    if (screen.active) {
      serviceActions.delete(name);
      if (selectedService === name) renderServiceDetail();
    }
  }
};

window.startServiceInstall = async function (name) {
  const screen = servicesScreen;
  if (!screen?.active || serviceUpdateStatuses[name]?.state === "running") return;
  renderServiceUpdateStatus(name, { operation: "install", state: "running" });
  try {
    const status = await screen.json(`/api/services/${encodeURIComponent(name)}/install/start`, { method: "POST" });
    renderServiceUpdateStatus(name, status);
    if (status.state === "running") await startServiceUpdatePolling(name);
    else if (status.state === "done") await loadServices();
  } catch (error) {
    if (!screen.active) return;
    renderServiceUpdateStatus(name, { operation: "install", state: "error", error: "Could not confirm installation. Retry to check its status." });
  }
};

window.startServiceUpdate = async function (name) {
  const screen = servicesScreen;
  if (!screen?.active) return;
  const info = serviceVersions[name] || null;
  const domId = serviceDomId(name);
  const buttonEl = document.getElementById(`svc-update-${domId}`);
  if (!buttonEl || serviceUpdateStatuses[name]?.state === "running") return;

  buttonEl.disabled = true;
  renderServiceUpdateStatus(name, { state: "running", last_line: "Starting update..." });
  try {
    const payload = {};
    if (info && info.source === "pip" && info.latest) payload.target_version = info.latest;
    const result = await screen.json(`/api/services/${encodeURIComponent(name)}/update/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    renderServiceUpdateStatus(name, result);
    await startServiceUpdatePolling(name);
    if (!screen.active) return;
  } catch (e) {
    if (!screen.active) return;
    renderServiceUpdateStatus(name, { state: "error", error: e.message || String(e) });
    alert(`Failed to start update: ${e.message || e}`);
    buttonEl.disabled = false;
  }
};

window.toggleServiceAutostart = async function (name, toggle) {
  const screen = servicesScreen;
  if (!screen?.active) return;
  if (!toggle || serviceAutostartPending.has(name)) return;
  serviceAutostartPending.add(name);
  const enabled = !!toggle.checked;
  toggle.disabled = true;
  try {
    await screen.json(`/api/services/${encodeURIComponent(name)}/settings/autostart`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    const svc = servicesData.find(item => item.name === name);
    if (svc) svc.autostart = enabled;
  } catch (e) {
    if (!screen.active) return;
    toggle.checked = !enabled;
    alert(`Failed to update auto-start: ${e.message || e}`);
  } finally {
    if (!screen.active) return;
    serviceAutostartPending.delete(name);
    if (selectedService === name) {
      const current = document.getElementById("svc-autostart-toggle");
      if (current) { current.checked = servicesData.find(item => item.name === name)?.autostart === true; current.disabled = false; }
    }
  }
};

window.viewServiceLog = async function (name) {
  if (!servicesScreen?.active) return;
  const screen = servicesScreen.latest("modal-log");
  try {
    const res = await screen.json(`/api/services/${encodeURIComponent(name)}/log?lines=200`);
    const modal = document.getElementById("svc-log-modal");
    const title = document.getElementById("svc-log-title");
    const content = document.getElementById("svc-log-content");
    if (title) title.textContent = `Service Log: ${name} (${res.path})`;
    if (content) content.textContent = res.log || "";
    if (modal) modal.classList.add("show");
  } catch (e) {
    if (!screen.active) return;
    alert(`Failed to load log: ${e.message || e}`);
  }
};

window.openServiceTensorBoard = async function (name) {
  const screen = servicesScreen;
  if (!screen?.active) return;
  const source = serviceTensorBoardSource(name);
  if (!source) return;
  const domId = serviceDomId(name);
  const statusEl = document.getElementById(`svc-tensorboard-status-${domId}`);
  const setStatus = (msg) => {
    if (!statusEl) return;
    statusEl.textContent = msg || "";
  };
  try {
    await window.openTensorBoard(source, {
      screen,
      label: serviceDisplayLabel(name),
      onError: setStatus,
      allowUnavailable: false,
    });
    setStatus("TensorBoard: opening...");
  } catch (e) {
    if (!screen.active) return;
    setStatus(`TensorBoard: ${e.message || e}`);
  }
};

window.refreshServiceTensorBoardStatus = async function (name) {
  const screen = servicesScreen;
  if (!screen?.active) return;
  const source = serviceTensorBoardSource(name);
  if (!source) return;
  const domId = serviceDomId(name);
  const statusEl = document.getElementById(`svc-tensorboard-status-${domId}`);
  if (!statusEl) return;
  try {
    const tb = await window.getTensorBoardSourceStatus(source, { force: false, screen });
    if (tb && tb.ready) {
      statusEl.textContent = `TensorBoard: ${tb.reason}`;
      return;
    }
    statusEl.textContent = `TensorBoard: ${tb && tb.reason ? tb.reason : "No data yet"}`;
  } catch (e) {
    if (!screen.active) return;
    statusEl.textContent = "TensorBoard: unavailable";
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
