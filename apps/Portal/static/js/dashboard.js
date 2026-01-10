window.initDashboard = async function () {
  const status = document.getElementById("telemetry-status");
  const content = document.getElementById("telemetry-content");
  if (!status || !content) return;

  status.textContent = "Loading telemetry...";
  content.style.display = "none";

  try {
    const data = await fetchJson("/api/telemetry");

    document.getElementById("t-host").textContent = data.host;
    document.getElementById("t-uptime").textContent = formatUptime(data.uptime_seconds);
    document.getElementById("t-load").textContent = (data.load_avg || []).map(v => v.toFixed(2)).join(" / ");

    const memLabel = `${formatBytes(data.mem_used)} / ${formatBytes(data.mem_total)} (${pct(data.mem_used, data.mem_total)}%)`;
    document.getElementById("t-mem").textContent = memLabel;

    // CPU
    const cpuPct = Math.min(100, Math.round(((data.load_avg?.[0] || 0) / (data.cpu_count || 1)) * 100));
    const cpuBar = document.getElementById("cpu-bar");
    const cpuLbl = document.getElementById("cpu-label");
    if (cpuBar) cpuBar.style.width = `${cpuPct}%`;
    if (cpuLbl) cpuLbl.textContent = `${cpuPct}% of ${data.cpu_count || 1} cores (load ${(data.load_avg?.[0] || 0).toFixed(2)})`;

    // GPU(s)
    const gpuWrap = document.getElementById("gpu-bars");
    if (gpuWrap) {
      gpuWrap.innerHTML = "";
      (data.gpus || []).forEach(g => {
        const util = g.util ?? 0;
        const memPct = pct(g.mem_used, g.mem_total);

        const div = document.createElement("div");
        div.style.marginBottom = "8px";
        div.innerHTML = `
          <div style="font-weight:600; margin-bottom:4px;">GPU ${g.index}: ${g.name}</div>
          <div style="display:flex; gap:14px; align-items:center; flex-wrap:wrap;">
            <div>
              <div style="font-size:12px; color:var(--muted); margin-bottom:4px;">Util</div>
              <div class="bar-wrap"><div class="bar-fill" style="width:${util}%;"></div></div>
              <div style="font-size:12px; color:var(--muted); margin-top:4px;">${util}%</div>
            </div>
            <div>
              <div style="font-size:12px; color:var(--muted); margin-bottom:4px;">Memory</div>
              <div class="bar-wrap"><div class="bar-fill" style="width:${memPct}%;"></div></div>
              <div style="font-size:12px; color:var(--muted); margin-top:4px;">${formatBytes(g.mem_used)} / ${formatBytes(g.mem_total)}</div>
            </div>
          </div>
        `;
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
          <td style="color:var(--muted); font-size:12px;">data used</td>
        `;
        tbody.appendChild(tr);
      }

      // 2) Existing df-based mounts
      (data.disks || []).forEach(d => {
        const tr = document.createElement("tr");

        const bar = `<div class="bar-wrap"><div class="bar-fill" style="width:${d.pct}%;"></div></div>`;
        tr.innerHTML = `<td>${d.mount}</td><td>${formatBytes(d.used)} / ${formatBytes(d.total)} (${d.pct}%)</td><td>${bar}</td>`;

        tbody.appendChild(tr);
      });
    }

    status.textContent = "";
    content.style.display = "";
    
    // Load shutdown status
    try {
      updateShutdownStatus();
    } catch (e) {
      console.error('Failed to load shutdown status:', e);
    }
  } catch (e) {
    status.textContent = `Error: ${e.message || e}`;
    content.style.display = "none";
  }
};

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

async function scheduleShutdown() {
  const valueInput = document.getElementById('shutdown-value');
  const unitSelect = document.getElementById('shutdown-unit');
  
  if (!valueInput || !unitSelect) {
    console.error('Shutdown input elements not found');
    return;
  }
  
  const value = parseInt(valueInput.value);
  const unit = unitSelect.value;
  
  if (!value || value < 1) {
    alert('Please enter a valid number greater than 0');
    return;
  }
  
  try {
    const response = await fetchJson('/api/shutdown/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value, unit })
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
  console.log('Updating shutdown status...');
  
  // Show debug info
  const debugDiv = document.getElementById('shutdown-debug');
  if (debugDiv) {
    debugDiv.style.display = 'block';
    debugDiv.textContent = 'Debug: Loading shutdown status...';
  }
  
  try {
    const status = await fetchJson('/api/shutdown/status');
    console.log('Shutdown status response:', status);
    
    // Null checks for all elements
    const inputsDiv = document.getElementById('shutdown-inputs');
    const statusDiv = document.getElementById('shutdown-status');
    const timeSpan = document.getElementById('shutdown-time');
    const countdownSpan = document.getElementById('shutdown-countdown');
    
    console.log('Elements found:', { inputsDiv, statusDiv, timeSpan, countdownSpan });
    
    if (debugDiv) {
      debugDiv.textContent = `Debug: Elements found - inputs: ${!!inputsDiv}, status: ${!!statusDiv}, time: ${!!timeSpan}, countdown: ${!!countdownSpan}`;
    }
    
    // Only proceed if all required elements exist
    if (!inputsDiv || !statusDiv || !timeSpan || !countdownSpan) {
      console.warn('Shutdown scheduler elements not found, skipping update');
      if (debugDiv) {
        debugDiv.textContent = 'Debug: Some elements missing, check DOM structure';
      }
      return;
    }
    
    if (status.scheduled) {
      inputsDiv.style.display = 'none';
      statusDiv.style.display = 'block';
      timeSpan.textContent = status.shutdown_time || 'Unknown';
      
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
      inputsDiv.style.display = 'flex';
      statusDiv.style.display = 'none';
      if (shutdownTimer) {
        clearInterval(shutdownTimer);
        shutdownTimer = null;
      }
    }
    
    // Hide debug after successful load
    if (debugDiv) {
      setTimeout(() => { debugDiv.style.display = 'none'; }, 2000);
    }
  } catch (error) {
    console.error('Failed to fetch shutdown status:', error);
    if (debugDiv) {
      debugDiv.textContent = `Debug: Error - ${error.message}`;
    }
  }
}

function updateCountdown(seconds) {
  const countdownSpan = document.getElementById('shutdown-countdown');
  if (!countdownSpan) {
    console.warn('Countdown element not found');
    return;
  }
  
  if (seconds <= 0) {
    countdownSpan.textContent = 'Shutting down...';
    if (shutdownTimer) {
      clearInterval(shutdownTimer);
      shutdownTimer = null;
    }
    return;
  }
  
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  let parts = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);
  
  countdownSpan.textContent = parts.join(' ');
}