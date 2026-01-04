let tpLogTimer = null;

window.initTrainpilot = function () {
  bindTpControls();
  startTpLogPoll();
};

function bindTpControls() {
  const status = document.getElementById("tp-status");
  if (status) status.textContent = "";
}

window.startTrainPilot = async function () {
  const dataset = document.getElementById("tp-dataset")?.value.trim() || "";
  const output = document.getElementById("tp-output")?.value.trim() || "";
  const profile = document.getElementById("tp-profile")?.value || "regular";
  const toml = document.getElementById("tp-toml")?.value.trim() || "";
  const status = document.getElementById("tp-status");
  if (status) status.textContent = "Starting...";
  try {
    await fetchJson("/api/trainpilot/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset_name: dataset,
        output_name: output,
        profile,
        toml_path: toml,
      }),
    });
    if (status) status.textContent = "Running...";
  } catch (e) {
    if (status) status.textContent = `Error: ${e.message || e}`;
  }
};

window.stopTrainPilot = async function () {
  const status = document.getElementById("tp-status");
  if (status) status.textContent = "Stopping...";
  try {
    await fetchJson("/api/trainpilot/stop", { method: "POST" });
    if (status) status.textContent = "Stopped.";
  } catch (e) {
    if (status) status.textContent = `Error: ${e.message || e}`;
  }
};

function startTpLogPoll() {
  if (tpLogTimer) return;
  const poll = async () => {
    const pre = document.getElementById("tp-logs");
    if (!pre) return;
    try {
      const data = await fetchJson("/api/trainpilot/logs?limit=500");
      pre.textContent = (data.lines || []).join("\n");
    } catch (e) {
      // ignore transient errors
    }
  };
  poll();
  tpLogTimer = setInterval(poll, 2000);
}

window.stopTpLogPoll = function () {
  if (tpLogTimer) clearInterval(tpLogTimer);
  tpLogTimer = null;
};
