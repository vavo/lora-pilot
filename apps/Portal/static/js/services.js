window.initServices = async function () {
  await loadServices();
};

async function loadServices() {
  const status = document.getElementById("svc-status");
  const table = document.getElementById("services-table");
  const tbody = document.getElementById("services-body");
  if (!status || !table || !tbody) return;
  status.textContent = "Loading services...";
  table.style.display = "none";
  tbody.innerHTML = "";
  try {
    const data = await fetchJson("/api/services");
    data.forEach(svc => {
      const tr = document.createElement("tr");
      const dotCls = svc.state_raw === "RUNNING" ? "green" : svc.state_raw === "STARTING" ? "orange" : "red";
      const openUrl = serviceUrl(svc.name);
      tr.innerHTML = `
        <td>${svc.display}</td>
        <td><span class="dot ${dotCls}"></span>${svc.state_raw}</td>
        <td class="actions">
          <button onclick="serviceAction('${svc.name}','start')">Start</button>
          <button onclick="serviceAction('${svc.name}','restart')">Reload</button>
          <button class="danger" onclick="serviceAction('${svc.name}','stop')">Stop</button>
        </td>
        <td>${openUrl ? `<a href="${openUrl}" target="_blank">Open</a>` : "—"}</td>
        <td><button onclick="viewServiceLog('${svc.name}')">Logs</button></td>
      `;
      tbody.appendChild(tr);
    });
    status.textContent = "";
    table.style.display = "";
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

window.viewServiceLog = async function (name) {
  try {
    const res = await fetchJson(`/api/services/${encodeURIComponent(name)}/log?lines=200`);
    alert(`${res.path}\n\n${res.log}`);
  } catch (e) {
    alert(`Failed to load log: ${e.message || e}`);
  }
};
