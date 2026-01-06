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