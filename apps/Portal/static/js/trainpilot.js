let tpLogTimer = null;

window.initTrainpilot = function () {
  bindTpControls();
  loadTpDatasets();
  startTpLogPoll();
};

function bindTpControls() {
  const status = document.getElementById("tp-status");
  if (status) status.textContent = "";
}

async function loadTpDatasets() {
  const sel = document.getElementById("tp-dataset");
  const status = document.getElementById("tp-status");
  if (!sel) return;
  sel.innerHTML = `<option>Loading datasets...</option>`;
  try {
    const data = await fetchJson("/api/datasets");
    sel.innerHTML = "";
    if (!data.length) {
      sel.innerHTML = `<option value="">No datasets found</option>`;
      return;
    }
    data.forEach(d => {
      const label = `${d.display || d.name} (${d.images || 0} images)`;
      const val = d.path || d.name;
      const opt = document.createElement("option");
      opt.value = val;
      opt.textContent = label;
      sel.appendChild(opt);
    });
    // Pre-fill output with selected dataset name (friendly)
    if (sel.options.length) {
      const firstVal = sel.options[0].textContent || "";
      autoFillOutput(firstVal);
      sel.addEventListener("change", () => {
        const txt = sel.options[sel.selectedIndex]?.textContent || "";
        autoFillOutput(txt);
      });
    }
  } catch (e) {
    if (status) status.textContent = `Error loading datasets: ${e.message || e}`;
  }
}

window.openDatasets = function (evt) {
  if (evt) evt.preventDefault();
  if (window.loadSection) {
    window.loadSection("datasets");
  } else {
    window.location.href = "/#datasets";
  }
};

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
    const status = document.getElementById("tp-status");
    if (!pre) return;
    try {
      const data = await fetchJson("/api/trainpilot/logs?limit=500");
      const lines = data.lines || [];
      pre.textContent = lines.join("\n");
      // show last line as status hint
      if (status && lines.length) {
        status.textContent = lines[lines.length - 1];
      }
      // auto-scroll to bottom
      pre.scrollTop = pre.scrollHeight;
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

function autoFillOutput(labelText) {
  const out = document.getElementById("tp-output");
  if (!out) return;
  if (!out.value || out.value.trim() === "") {
    // strip image count from label "(123 images)"
    const base = labelText.replace(/\s*\([^)]*\)\s*$/, "").trim();
    if (base) out.value = base;
  }
}
