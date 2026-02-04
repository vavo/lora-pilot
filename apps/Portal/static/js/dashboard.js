window.initDashboard = async function () {
  const status = document.getElementById("telemetry-status");
  const content = document.getElementById("telemetry-content");
  if (!status || !content) return;
  bindShutdownInputs();

  status.textContent = "Loading telemetry...";
  content.classList.add("is-hidden");

  try {
    const data = await fetchJson("/api/telemetry");

    document.getElementById("t-host").textContent = data.host;
    document.getElementById("t-uptime").textContent = formatUptime(data.uptime_seconds);

    // CPU
    const cpuPct = Math.min(100, Math.round(((data.load_avg?.[0] || 0) / (data.cpu_count || 1)) * 100));
    const cpuBar = document.getElementById("cpu-bar");
    const cpuLbl = document.getElementById("cpu-label");
    if (cpuBar) cpuBar.style.width = `${cpuPct}%`;
    if (cpuLbl) cpuLbl.textContent = `${cpuPct}% of ${data.cpu_count || 1} cores (load ${(data.load_avg?.[0] || 0).toFixed(2)})`;
    const memPct = pct(data.mem_used, data.mem_total);
    const memBar = document.getElementById("mem-bar");
    const memLbl = document.getElementById("mem-label");
    if (memBar) memBar.style.width = `${memPct}%`;
    if (memLbl) memLbl.textContent = `${formatBytes(data.mem_used)} / ${formatBytes(data.mem_total)} (${memPct}%)`;

    // GPU(s)
    const gpuWrap = document.getElementById("gpu-bars");
    if (gpuWrap) {
      gpuWrap.innerHTML = "";
      (data.gpus || []).forEach(g => {
        const util = g.util ?? 0;
        const memPct = pct(g.mem_used, g.mem_total);

        const div = document.createElement("div");
        div.className = "dash-gpu-item";
        div.innerHTML = `
          <div class="dash-gpu-title">GPU ${g.index}: ${g.name}</div>
          <div class="dash-gpu-row">
            <div>
              <div class="dash-gpu-label">Util</div>
              <div class="bar-wrap"><div class="bar-fill gpu-util-bar"></div></div>
              <div class="dash-gpu-value">${util}%</div>
            </div>
            <div>
              <div class="dash-gpu-label">Memory</div>
              <div class="bar-wrap"><div class="bar-fill gpu-mem-bar"></div></div>
              <div class="dash-gpu-value">${formatBytes(g.mem_used)} / ${formatBytes(g.mem_total)}</div>
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

    // Disks
    const tbody = document.getElementById("disk-body");
    if (tbody) {
      tbody.innerHTML = "";

      // 1) Optional: /workspace data usage (du) row
      // Backend should return: workspace_data_used_bytes (number)
      if (typeof data.workspace_data_used_bytes === "number") {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>/workspace (data)</td>
          <td>${formatBytes(data.workspace_data_used_bytes)}</td>
          <td class="dash-disk-meta">data used</td>
        `;
        tbody.appendChild(tr);
      }

      // 2) Existing df-based mounts
      (data.disks || []).forEach(d => {
        const tr = document.createElement("tr");

        const bar = `<div class="bar-wrap"><div class="bar-fill disk-bar"></div></div>`;
        tr.innerHTML = `<td>${d.mount}</td><td>${formatBytes(d.used)} / ${formatBytes(d.total)} (${d.pct}%)</td><td>${bar}</td>`;
        const diskBar = tr.querySelector(".disk-bar");
        if (diskBar) diskBar.style.width = `${d.pct}%`;

        tbody.appendChild(tr);
      });
    }

    status.textContent = "";
    content.classList.remove("is-hidden");
    
    // Load shutdown status
    updateShutdownStatus();
  } catch (e) {
    status.textContent = `Error: ${e.message || e}`;
    renderTelemetryFallback();
    content.classList.remove("is-hidden");
  }
};

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
