const DASHBOARD_POLL_MS = 8000;
let dashboardPollTimer = null;

window.stopDashboard = function () {
  if (dashboardPollTimer) {
    clearInterval(dashboardPollTimer);
    dashboardPollTimer = null;
  }
  if (shutdownTimer) {
    clearInterval(shutdownTimer);
    shutdownTimer = null;
  }
};

window.initDashboard = async function () {
  const status = document.getElementById("telemetry-status");
  const content = document.getElementById("telemetry-content");
  if (!status || !content) return;

  bindShutdownInputs();
  if (dashboardPollTimer) {
    clearInterval(dashboardPollTimer);
    dashboardPollTimer = null;
  }

  status.textContent = "Loading telemetry...";
  content.classList.add("is-hidden");
  await refreshDashboardTelemetry();

  dashboardPollTimer = setInterval(() => {
    if (!document.getElementById("telemetry-status")) {
      clearInterval(dashboardPollTimer);
      dashboardPollTimer = null;
      return;
    }
    refreshDashboardTelemetry();
  }, DASHBOARD_POLL_MS);
};

async function refreshDashboardTelemetry() {
  const status = document.getElementById("telemetry-status");
  const content = document.getElementById("telemetry-content");
  if (!status || !content) return;

  try {
    const [data, history] = await Promise.all([
      fetchJson("/api/telemetry"),
      fetchJson("/api/telemetry/history").catch(() => null),
    ]);

    const hostEl = document.getElementById("t-host");
    const uptimeEl = document.getElementById("t-uptime");
    if (hostEl) hostEl.textContent = data.host || "n/a";
    if (uptimeEl) uptimeEl.textContent = formatUptime(data.uptime_seconds || 0);

    const cpuPct = clampPct(((data.load_avg?.[0] || 0) / (data.cpu_count || 1)) * 100);
    const cpuBar = document.getElementById("cpu-bar");
    const cpuLbl = document.getElementById("cpu-label");
    if (cpuBar) cpuBar.style.width = `${cpuPct}%`;
    if (cpuLbl) cpuLbl.textContent = `${cpuPct}% of ${data.cpu_count || 1} cores (load ${(data.load_avg?.[0] || 0).toFixed(2)})`;

    const memPct = pct(data.mem_used, data.mem_total);
    const memBar = document.getElementById("mem-bar");
    const memLbl = document.getElementById("mem-label");
    if (memBar) memBar.style.width = `${memPct}%`;
    if (memLbl) memLbl.textContent = `${formatBytes(data.mem_used)} / ${formatBytes(data.mem_total)} (${memPct}%)`;

    renderGpuCards(data.gpus || []);
    renderDisks(data);
    renderTelemetryHistory(history);

    status.textContent = "";
    content.classList.remove("is-hidden");
    updateShutdownStatus();
  } catch (e) {
    status.textContent = `Error: ${e.message || e}`;
    renderTelemetryFallback();
    content.classList.remove("is-hidden");
  }
}

function renderGpuCards(gpus) {
  const gpuWrap = document.getElementById("gpu-bars");
  if (!gpuWrap) return;
  gpuWrap.innerHTML = "";

  if (!gpus.length) {
    const empty = document.createElement("div");
    empty.className = "dash-metric-box";
    empty.innerHTML = `<div class="dash-metric-title">GPU</div><div class="dash-metric-value">No GPU detected</div>`;
    gpuWrap.appendChild(empty);
    return;
  }

  gpus.forEach((g) => {
    const util = clampPct(g.util ?? 0);
    const memPct = pct(g.mem_used, g.mem_total);
    const div = document.createElement("div");
    div.className = "dash-gpu-item";
    div.innerHTML = `
      <div class="dash-gpu-head">
        <div class="dash-gpu-title">GPU ${g.index}: ${g.name}</div>
        <div class="dash-gpu-pill">${util}% util</div>
      </div>
      <div class="dash-gpu-row">
        <div class="dash-gpu-util">
          <div class="dash-gpu-label">Compute</div>
          <div class="bar-wrap"><div class="bar-fill gpu-util-bar"></div></div>
          <div class="dash-gpu-value">${util}%</div>
        </div>
        <div class="dash-gpu-mem">
          <div class="dash-gpu-label">Memory</div>
          <div class="bar-wrap"><div class="bar-fill gpu-mem-bar"></div></div>
          <div class="dash-gpu-value">${formatBytes(g.mem_used)} / ${formatBytes(g.mem_total)} (${memPct}%)</div>
        </div>
      </div>
    `;
    const utilBar = div.querySelector(".gpu-util-bar");
    const memBar = div.querySelector(".gpu-mem-bar");
    if (utilBar) utilBar.style.width = `${util}%`;
    if (memBar) memBar.style.width = `${memPct}%`;
    gpuWrap.appendChild(div);
  });
}

function renderDisks(data) {
  const tbody = document.getElementById("disk-body");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (typeof data.workspace_data_used_bytes === "number") {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>/workspace (data)</td>
      <td>${formatBytes(data.workspace_data_used_bytes)}</td>
      <td class="dash-disk-meta">data used</td>
    `;
    tbody.appendChild(tr);
  }

  (data.disks || []).forEach((d) => {
    const tr = document.createElement("tr");
    const bar = `<div class="bar-wrap"><div class="bar-fill disk-bar"></div></div>`;
    tr.innerHTML = `<td>${d.mount}</td><td>${formatBytes(d.used)} / ${formatBytes(d.total)} (${d.pct}%)</td><td>${bar}</td>`;
    const diskBar = tr.querySelector(".disk-bar");
    if (diskBar) diskBar.style.width = `${d.pct}%`;
    tbody.appendChild(tr);
  });
}

function renderTelemetryHistory(history) {
  const cpuChart = document.getElementById("cpu-history-chart");
  const gpuChart = document.getElementById("gpu-history-chart");
  const windowLabel = document.getElementById("history-window-label");
  const gpuLabel = document.getElementById("gpu-history-label");
  const points = Array.isArray(history?.points) ? history.points : [];
  const availableSeconds = Number(history?.available_seconds || 0);
  const windowText = availableSeconds > 0 ? `Window: ${formatHistoryWindow(availableSeconds)}` : "No history yet";
  if (windowLabel) windowLabel.textContent = windowText;
  if (gpuLabel) gpuLabel.textContent = windowText;

  if (!points.length) {
    renderEmptyChart(cpuChart);
    renderEmptyChart(gpuChart);
    return;
  }

  const cpuSeries = points.map((p) => {
    if (Number.isFinite(p?.cpu?.pct)) return clampPct(p.cpu.pct);
    return clampPct(((p?.cpu?.load_avg?.[0] || 0) / (p?.cpu?.cpu_count || 1)) * 100);
  });
  const gpuSeries = points.map((p) => {
    const gpus = Array.isArray(p?.gpus) ? p.gpus : [];
    if (!gpus.length) return 0;
    return clampPct(Math.max(...gpus.map((g) => Number(g?.util || 0))));
  });

  renderLineChart(cpuChart, cpuSeries, {
    lineColor: "#38bdf8",
    fillFrom: "rgba(56,189,248,0.38)",
    fillTo: "rgba(56,189,248,0.03)",
  });
  renderLineChart(gpuChart, gpuSeries, {
    lineColor: "#fb923c",
    fillFrom: "rgba(251,146,60,0.40)",
    fillTo: "rgba(251,146,60,0.03)",
  });
}

function renderLineChart(svg, series, colors) {
  if (!svg) return;
  const values = (Array.isArray(series) ? series : []).map(clampPct);
  if (!values.length) {
    renderEmptyChart(svg);
    return;
  }

  const width = 400;
  const height = 112;
  const pad = 8;
  const graphWidth = width - pad * 2;
  const graphHeight = height - pad * 2;
  const count = values.length;

  const coords = values.map((v, idx) => {
    const x = pad + (count > 1 ? (idx / (count - 1)) * graphWidth : graphWidth / 2);
    const y = pad + ((100 - v) / 100) * graphHeight;
    return { x, y };
  });
  const points = coords.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
  const baselineY = (height - pad).toFixed(2);
  const area = `${coords[0].x.toFixed(2)},${baselineY} ${points} ${coords[coords.length - 1].x.toFixed(2)},${baselineY}`;
  const gradId = `${svg.id}-fill`;
  const latest = values[values.length - 1];
  const gridY = [25, 50, 75].map((mark) => {
    const y = (pad + ((100 - mark) / 100) * graphHeight).toFixed(2);
    return `<line x1="${pad}" y1="${y}" x2="${width - pad}" y2="${y}" stroke="rgba(148,163,184,0.25)" stroke-width="1"/>`;
  }).join("");

  svg.innerHTML = `
    <defs>
      <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${colors.fillFrom}"></stop>
        <stop offset="100%" stop-color="${colors.fillTo}"></stop>
      </linearGradient>
    </defs>
    ${gridY}
    <polygon points="${area}" fill="url(#${gradId})"></polygon>
    <polyline points="${points}" fill="none" stroke="${colors.lineColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"></polyline>
    <circle cx="${coords[coords.length - 1].x.toFixed(2)}" cy="${coords[coords.length - 1].y.toFixed(2)}" r="3" fill="${colors.lineColor}"></circle>
    <text x="${width - pad - 2}" y="${pad + 11}" text-anchor="end" fill="${colors.lineColor}" font-size="11" font-weight="700">${latest}%</text>
  `;
}

function renderEmptyChart(svg) {
  if (!svg) return;
  svg.innerHTML = `
    <rect x="0" y="0" width="400" height="112" fill="transparent"></rect>
    <text x="200" y="59" text-anchor="middle" fill="var(--muted)" font-size="12">Collecting telemetry...</text>
  `;
}

function renderTelemetryFallback() {
  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };
  setText("t-host", "n/a");
  setText("t-uptime", "n/a");
  const cpuBar = document.getElementById("cpu-bar");
  const cpuLbl = document.getElementById("cpu-label");
  const memBar = document.getElementById("mem-bar");
  const memLbl = document.getElementById("mem-label");
  const gpuWrap = document.getElementById("gpu-bars");
  const windowLabel = document.getElementById("history-window-label");
  const gpuLabel = document.getElementById("gpu-history-label");
  if (windowLabel) windowLabel.textContent = "Telemetry unavailable";
  if (gpuLabel) gpuLabel.textContent = "Telemetry unavailable";
  if (gpuWrap) gpuWrap.innerHTML = `<div class="dash-metric-box"><div class="dash-metric-title">GPU</div><div class="dash-metric-value">Telemetry unavailable</div></div>`;
  renderEmptyChart(document.getElementById("cpu-history-chart"));
  renderEmptyChart(document.getElementById("gpu-history-chart"));
  if (cpuBar) cpuBar.style.width = "0%";
  if (cpuLbl) cpuLbl.textContent = "Telemetry unavailable";
  if (memBar) memBar.style.width = "0%";
  if (memLbl) memLbl.textContent = "Telemetry unavailable";
}

function pct(used, total) {
  if (!total) return 0;
  return Math.min(100, Math.round((used / total) * 100));
}

function formatUptime(sec) {
  const d = Math.floor(sec / 86400); sec %= 86400;
  const h = Math.floor(sec / 3600); sec %= 3600;
  const m = Math.floor(sec / 60);
  return `${d}d ${h}h ${m}m`;
}

function formatHistoryWindow(sec) {
  const s = Math.max(0, Math.round(sec));
  if (s < 120) return `${s}s`;
  const m = Math.round(s / 60);
  if (m < 120) return `${m}m`;
  const h = Math.floor(m / 60);
  const remM = m % 60;
  if (h < 48) return remM ? `${h}h ${remM}m` : `${h}h`;
  const d = Math.floor(h / 24);
  const remH = h % 24;
  return remH ? `${d}d ${remH}h` : `${d}d`;
}

function clampPct(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(100, Math.round(n)));
}

// Shutdown scheduler functionality
let shutdownTimer = null;

function clampInt(v, min, max) {
  const n = parseInt(v, 10);
  if (Number.isNaN(n)) return min;
  return Math.max(min, Math.min(max, n));
}

function pad2(n) {
  const x = Math.max(0, Math.min(99, n | 0));
  return String(x).padStart(2, "0");
}

function setShutdownScheduledUI(isScheduled) {
  const picker = document.getElementById("shutdown-picker");
  const countdown = document.getElementById("shutdown-countdown-box");
  const scheduleBtn = document.getElementById("schedule-shutdown-btn");
  const cancelBtn = document.getElementById("cancel-shutdown-btn");
  if (picker) picker.classList.toggle("is-hidden", isScheduled);
  if (countdown) countdown.classList.toggle("is-hidden", !isScheduled);
  if (scheduleBtn) scheduleBtn.classList.toggle("is-hidden", isScheduled);
  if (cancelBtn) cancelBtn.classList.toggle("is-hidden", !isScheduled);
}

function setCountdownDigits(totalSeconds) {
  const hh = document.getElementById("shutdown-hh");
  const mm = document.getElementById("shutdown-mm");
  const ss = document.getElementById("shutdown-ss");
  if (!hh || !mm || !ss) return;
  const s = Math.max(0, totalSeconds | 0);
  const hours = Math.floor(s / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  hh.textContent = pad2(Math.min(99, hours));
  mm.textContent = pad2(minutes);
  ss.textContent = pad2(secs);
}

async function scheduleShutdown() {
  const hoursEl = document.getElementById("shutdown-hours");
  const minsEl = document.getElementById("shutdown-mins");
  const secsEl = document.getElementById("shutdown-secs");

  if (!hoursEl || !minsEl || !secsEl) return;

  const hours = clampInt(hoursEl.value, 0, 99);
  const mins = clampInt(minsEl.value, 0, 59);
  const secs = clampInt(secsEl.value, 0, 59);
  const totalSeconds = (hours * 3600) + (mins * 60) + secs;

  if (totalSeconds < 1) {
    alert("Set a countdown greater than 0 seconds.");
    return;
  }
  
  try {
    const response = await fetchJson('/api/shutdown/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value: totalSeconds, unit: "seconds" })
    });
    
    if (response.status === 'scheduled') {
      updateShutdownStatus();
    }
  } catch (error) {
    alert('Failed to schedule shutdown: ' + error.message);
  }
}

async function cancelShutdown() {
  try {
    const response = await fetchJson('/api/shutdown/cancel', {
      method: 'POST'
    });
    
    if (response.status === 'cancelled') {
      if (shutdownTimer) {
        clearInterval(shutdownTimer);
        shutdownTimer = null;
      }
      updateShutdownStatus();
    }
  } catch (error) {
    alert('Failed to cancel shutdown: ' + error.message);
  }
}

async function updateShutdownStatus() {
  try {
    const status = await fetchJson('/api/shutdown/status');
    const timeSpan = document.getElementById('shutdown-time');
    const meta = document.getElementById("shutdown-meta");
    if (!timeSpan) return;
    
    if (status.scheduled) {
      setShutdownScheduledUI(true);
      timeSpan.textContent = status.shutdown_time || 'Unknown';
      if (meta) meta.classList.remove("is-hidden");
      
      // Store the initial time and start countdown
      const startTime = Date.now();
      const initialRemaining = status.time_remaining || 0;
      
      // Start countdown timer
      if (shutdownTimer) clearInterval(shutdownTimer);
      shutdownTimer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const currentRemaining = Math.max(0, initialRemaining - elapsed);
        updateCountdown(currentRemaining);
      }, 1000);
      
      updateCountdown(initialRemaining);
    } else {
      setShutdownScheduledUI(false);
      if (meta) meta.classList.add("is-hidden");
      if (shutdownTimer) {
        clearInterval(shutdownTimer);
        shutdownTimer = null;
      }
    }
    
  } catch (error) {
    // ignore transient errors
  }
}

function updateCountdown(seconds) {
  if (seconds <= 0) {
    setCountdownDigits(0);
    if (shutdownTimer) {
      clearInterval(shutdownTimer);
      shutdownTimer = null;
    }
    return;
  }

  setCountdownDigits(seconds);
}

function bindShutdownInputs() {
  const hoursEl = document.getElementById("shutdown-hours");
  const minsEl = document.getElementById("shutdown-mins");
  const secsEl = document.getElementById("shutdown-secs");
  if (!hoursEl || !minsEl || !secsEl) return;
  if (hoursEl.dataset.bound) return;
  hoursEl.dataset.bound = "1";

  const normalize = () => {
    hoursEl.value = String(clampInt(hoursEl.value, 0, 99));
    minsEl.value = String(clampInt(minsEl.value, 0, 59));
    secsEl.value = String(clampInt(secsEl.value, 0, 59));
  };

  [hoursEl, minsEl, secsEl].forEach(el => {
    el.addEventListener("blur", normalize);
    el.addEventListener("change", normalize);
  });
}
