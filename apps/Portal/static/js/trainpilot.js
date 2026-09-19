let tpLogTimer = null;
let tpPollGeneration = 0;
let tpStarting = false, tpRunning = false, tpStopping = false, tpMoving = false;
let tpStatusKnown = false, tpDismissedRunId = null, tpLastData = null;
let tpDatasets = [];
const tpProfiles = { quick_test: "Quick test", regular: "Balanced", high_quality: "Extended" };

window.initTrainpilot = async function () {
  const page = document.getElementById('tp-page');
  tpStatusKnown = false;
  bindTpControls();
  await loadTpDatasets();
  if (page && page === document.getElementById('tp-page')) window.trainingWorkspace.init();
};

function bindTpControls() {
  const status = document.getElementById("tp-status");
  const output = document.getElementById("tp-output");
  const tomlPath = document.getElementById("tp-toml");
  if (status) status.textContent = "";
  if (tomlPath && !tomlPath.value) {
    tomlPath.value = "/workspace/config/trainpilot/newlora.toml";
  }
  if (output && !output.dataset.bound) {
    output.dataset.bound = "1";
    output.addEventListener("input", () => {
      const normalized = normalizeOutputName(output.value || "");
      if (normalized !== output.value) output.value = normalized;
      updateEpochExample(normalized);
    });
    updateEpochExample(output.value || "");
  }
  document.querySelectorAll('[name="tp-profile-choice"]').forEach(input => input.addEventListener("change", () => {
    document.getElementById("tp-profile").value = input.value;
    updateTpSummary();
  }));
  document.getElementById("tp-review-dataset").onclick = () => {
    const dataset = tpDatasets.find(d => d.name === document.getElementById("tp-dataset").value);
    if (dataset) openTagpilotDataset(dataset.name);
  };
  document.getElementById("tp-move-loras").onclick = moveTrainpilotLoras;
  document.getElementById("tp-another").onclick = () => {
    tpDismissedRunId = tpLastData?.run_id;
    renderTpResult(tpLastData);
    document.getElementById("tp-dataset")?.focus();
  };
  document.getElementById("tp-result-logs").onclick = () => {
    const details = document.getElementById("tp-diagnostics");
    details.open = true;
    details.scrollIntoView({ block: "start" });
    details.querySelector("summary").focus();
  };
  document.getElementById("tp-copy-path").onclick = async event => {
    try {
      await navigator.clipboard.writeText(document.getElementById("tp-result-path").textContent);
      event.target.textContent = "Copied";
    } catch { event.target.textContent = "Select the path to copy"; }
  };
  refreshTrainpilotTensorBoardStatus().catch(() => {});
}

function findLatestProgress(lines) {
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    const line = lines[i];
    if (!line || !line.includes("steps")) continue;
    const percentMatch = line.match(/(\d+)%\|/);
    const stepMatch = line.match(/(\d+)\s*\/\s*(\d+)/);
    if (!percentMatch && !stepMatch) continue;
    const current = stepMatch ? parseInt(stepMatch[1], 10) : null;
    const total = stepMatch ? parseInt(stepMatch[2], 10) : null;
    const percent = percentMatch
      ? parseInt(percentMatch[1], 10)
      : (current && total ? Math.round((current / total) * 100) : null);
    if (percent === null || Number.isNaN(percent)) continue;
    const lossMatch = line.match(/avr_loss=([0-9.]+)/);
    return {
      percent: Math.max(0, Math.min(100, percent)),
      current,
      total,
      loss: lossMatch ? lossMatch[1] : null,
    };
  }
  return null;
}

function updateProgressUI(progress, running, finished) {
  const wrap = document.getElementById("tp-progress-wrap");
  const bar = document.getElementById("tp-progress-bar");
  const text = document.getElementById("tp-progress-text");
  if (!wrap || !bar || !text) return;
  if (!running || finished || !progress) {
    wrap.classList.add("is-hidden");
    bar.style.width = "0%";
    text.textContent = "";
    return;
  }
  wrap.classList.remove("is-hidden");
  bar.style.width = `${progress.percent}%`;
  const stepText = progress.current && progress.total
    ? `${progress.current}/${progress.total}`
    : `${progress.percent}%`;
  const lossText = progress.loss ? ` • loss ${progress.loss}` : "";
  text.textContent = `${progress.percent}% (${stepText})${lossText}`;
}

function setModelDownloadUI(pct, label) {
  const wrap = document.getElementById("tp-modeldl-wrap");
  const bar = document.getElementById("tp-modeldl-bar");
  const text = document.getElementById("tp-modeldl-text");
  if (!wrap || !bar || !text) return;
  wrap.classList.remove("is-hidden");
  if (typeof pct === "number" && isFinite(pct)) {
    const clamped = Math.max(0, Math.min(100, Math.round(pct)));
    bar.style.width = `${clamped}%`;
    text.textContent = label || `${clamped}%`;
  } else {
    // Indeterminate: animate by cycling width via CSS transition.
    const now = Date.now();
    const phase = Math.floor((now / 700) % 2);
    bar.style.width = phase ? "85%" : "35%";
    text.textContent = label || "Downloading…";
  }
}

function clearModelDownloadUI() {
  const wrap = document.getElementById("tp-modeldl-wrap");
  const bar = document.getElementById("tp-modeldl-bar");
  const text = document.getElementById("tp-modeldl-text");
  if (!wrap || !bar || !text) return;
  wrap.classList.add("is-hidden");
  bar.style.width = "0%";
  text.textContent = "";
}

async function ensureTrainpilotModelsPresent(tomlPath) {
  const check = await fetchJson("/api/training/preflight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(window.trainingWorkspace.spec()),
  });
  const missing = (check && check.missing) ? check.missing : [];
  if (!missing.length) return true;

  const lines = missing.map(m => {
    const kind = m.kind || "model";
    const path = m.value || "(missing in TOML)";
    const mapped = m.model_name ? ` → ${m.model_name}` : "";
    return `- ${kind}: ${path}${mapped}`;
  }).join("\n");

  const ok = confirm(`Missing model files for this training family:\n\n${lines}\n\nDownload now?`);
  if (!ok) return false;

  const downloadable = missing.filter(m => m.model_name);
  const manual = missing.filter(m => !m.model_name);
  if (manual.length) {
    alert(
      `Some missing files can't be matched to an entry in models.manifest.\n` +
      `Please download them from the Models tab, then try again.\n\n` +
      manual.map(m => `- ${m.kind || "model"}: ${m.value || "(missing in TOML)"}`).join("\n")
    );
    return false;
  }

  for (let i = 0; i < downloadable.length; i += 1) {
    const m = downloadable[i];
    const modelName = m.model_name;
    const prefix = `${i + 1}/${downloadable.length}`;
    setModelDownloadUI(null, `${prefix} Starting ${modelName}…`);
    await fetchJson(`/api/models/${encodeURIComponent(modelName)}/pull/start`, { method: "POST" });
    while (true) {
      const st = await fetchJson(`/api/models/${encodeURIComponent(modelName)}/pull/status`);
      if (st && st.state === "running") {
        const pct = (typeof st.progress_pct === "number") ? st.progress_pct : null;
        const label = st.last_line ? `${prefix} ${st.last_line}` : `${prefix} Downloading ${modelName}…`;
        setModelDownloadUI(pct, label);
        await new Promise(r => setTimeout(r, 1000));
        continue;
      }
      if (st && st.state === "done") {
        setModelDownloadUI(100, `${prefix} Downloaded ${modelName}`);
        await new Promise(r => setTimeout(r, 350));
        break;
      }
      if (st && st.state === "error") {
        throw new Error(st.error || `Download failed: ${modelName}`);
      }
      await new Promise(r => setTimeout(r, 1000));
    }
  }

  clearModelDownloadUI();
  return true;
}

async function loadTpDatasets() {
  const sel = document.getElementById("tp-dataset");
  if (!sel) return;
  try {
    tpDatasets = await fetchJson("/api/datasets");
    if (!sel.isConnected) return;
    sel.replaceChildren();
    if (!tpDatasets.length) sel.add(new Option("No datasets yet", ""));
    tpDatasets.forEach(d => sel.add(new Option(d.display || d.name, d.name)));
    if (window.pendingTrainDataset && tpDatasets.some(d => d.name === window.pendingTrainDataset)) {
      sel.value = window.pendingTrainDataset;
    }
    window.pendingTrainDataset = null;
    const changed = () => {
      autoFillOutput(sel.selectedOptions[0]?.textContent || "");
      updateTpSummary();
    };
    sel.addEventListener("change", changed);
    if (tpDatasets.length) changed();
    else updateTpSummary();
  } catch (error) {
    if (sel.isConnected) {
      sel.replaceChildren(new Option("Datasets unavailable", ""));
      showTpError(`Could not load datasets: ${error.message || error}`);
      updateTpSummary();
    }
  }
}

function updateTpSummary() {
  const selected = document.getElementById("tp-dataset");
  if (!selected) return;
  const dataset = tpDatasets.find(d => d.name === selected.value);
  const text = dataset ? `${dataset.images} images · ${dataset.captioned_images || 0} captions` : "Upload a dataset to get started.";
  document.getElementById("tp-dataset-info").textContent = text;
  document.getElementById("tp-summary-dataset").textContent = dataset?.display || "Choose a dataset";
  document.getElementById("tp-summary-profile").textContent = tpProfiles[document.getElementById("tp-profile").value];
  document.getElementById("tp-summary-output").textContent = document.getElementById("tp-output").value || "—";
  const check = document.getElementById("tp-check-dataset");
  check.textContent = dataset?.images ? `Dataset available · ${text}` : "Add images to a dataset before training.";
  check.classList.toggle("verified", !!dataset?.images);
  document.getElementById("tp-review-dataset").hidden = !dataset;
  syncTpActions();
}

function showTpError(message) {
  const el = document.getElementById("tp-error");
  if (el) { el.textContent = message; el.hidden = !message; }
}

function syncTpActions() {
  const start = document.getElementById("tp-start");
  if (!start) return;
  const dataset = tpDatasets.find(d => d.name === document.getElementById("tp-dataset").value);
  const busy = tpStarting || tpStopping;
  start.disabled = busy || !tpStatusKnown || !dataset?.images || !document.getElementById("tp-output").value.trim();
  start.hidden = false;
  start.textContent = tpStarting ? "Preparing training…" : "Add to training queue";
  const stop = document.getElementById("tp-stop");
  stop.hidden = !tpRunning;
  stop.disabled = tpStopping;
  document.getElementById("tp-fields").disabled = busy;
}

async function refreshTpPreflight() {
  return window.trainingWorkspace?.preflight();
}

window.openDatasets = function (evt) {
  if (evt) evt.preventDefault();
  if (window.loadSection) {
    window.loadSection("datasets");
  } else {
    window.location.href = "/#datasets";
  }
};

window.openTrainpilotTensorBoard = async function () {
  const statusEl = document.getElementById("tp-tensorboard-status");
  const status = (msg) => {
    if (!statusEl) return;
    statusEl.textContent = msg || "";
  };
  try {
    await window.openTensorBoard("trainpilot", {
      label: "TrainPilot",
      onError: status,
      allowUnavailable: false,
    });
    status("");
  } catch (e) {
    status(e.message || e);
  }
};

window.refreshTrainpilotTensorBoardStatus = async function () {
  const statusEl = document.getElementById("tp-tensorboard-status");
  if (!statusEl) return;
  try {
    const tb = await window.getTensorBoardSourceStatus("trainpilot", { force: false });
    if (tb && tb.ready) {
      statusEl.textContent = "TensorBoard: run logs detected";
    } else {
      statusEl.textContent = `TensorBoard: ${tb && tb.reason ? tb.reason : "No data yet"}`;
    }
  } catch (e) {
    statusEl.textContent = "TensorBoard: unavailable";
  }
};

window.startTrainPilot = () => window.trainingWorkspace.submit();
window.stopTrainPilot = () => window.trainingWorkspace.stopRun();
window.stopTpLogPoll = function () {
  tpPollGeneration++;
  clearTimeout(tpLogTimer);
  tpLogTimer = null;
  window.trainingWorkspace?.stop();
};

function renderTpResult(data) {
  const panel = document.getElementById("tp-result");
  if (!panel) return;
  const complete = !!data?.run_id && !data.running && data.exit_code === 0 && !data.run?.stopped && data.run_id !== tpDismissedRunId;
  panel.hidden = !complete;
  document.getElementById("tp-completion-steps").hidden = !complete;
  document.getElementById("tp-files-saved").hidden = !(data.artifacts?.length);
  document.getElementById("tp-setup").hidden = complete;
  document.getElementById("tp-heading").textContent = complete ? "Your LoRA is trained" : "Train your LoRA";
  document.getElementById("tp-subheading").textContent = complete ? "Training finished. Choose what to do with your files next." : "Choose your images and a training profile. TrainPilot handles the setup.";
  if (!complete) return;
  document.getElementById("tp-result-dataset").textContent = data.run?.dataset?.replace(/^1_/, "").replaceAll("_", " ") || "Current run";
  document.getElementById("tp-result-profile").textContent = tpProfiles[data.run?.profile] || "Custom";
  document.getElementById("tp-result-finished").textContent = data.run?.finished_at ? new Date(data.run.finished_at).toLocaleString() : "Completed";
  const files = data.artifacts || [];
  document.getElementById("tp-result-count").textContent = files.length ? `${files.length} checkpoint${files.length === 1 ? "" : "s"} ${data.moved ? "copied to your LoRA library" : "saved in your workspace"}.` : "No new LoRA files found. Check the logs and output folder.";
  const list = document.getElementById("tp-result-files");
  const signature = JSON.stringify(files);
  if (list.dataset.files !== signature) {
    list.dataset.files = signature;
    list.replaceChildren();
    files.forEach(file => {
      const row = document.createElement("tr");
      for (const value of [file.name, formatBytes(file.size_bytes)]) {
        const cell = document.createElement("td"); cell.textContent = value; row.append(cell);
      }
      list.append(row);
    });
  }
  document.getElementById("tp-result-path").textContent = (data.moved ? data.lora_destination : data.output_dir) || "Unavailable";
  document.getElementById("tp-result-destination").textContent = data.lora_destination || "";
  document.getElementById("tp-result-instructions").textContent = data.moved ? "A copy is in your shared LoRA library. Your original run files remain saved." : "Copy the trained files to your shared LoRA folder, or generate a comparison below.";
  if (data.moved && !tpMoving) document.getElementById("tp-move-status").textContent = "Your LoRA files are ready in the shared library.";
  const button = document.getElementById("tp-move-loras");
  button.disabled = tpMoving || data.moved || !data.move_available;
  button.textContent = tpMoving ? "Copying files…" : data.moved ? "Copied to LoRA library" : "Copy to LoRA library";
}

async function moveTrainpilotLoras() {
  return window.trainingWorkspace.publish();
}

function autoFillOutput(labelText) {
  const out = document.getElementById("tp-output");
  if (!out) return;
  // strip image count from label "(123 images)"
  const base = labelText.replace(/\s*\([^)]*\)\s*$/, "").trim();
  const normalized = normalizeOutputName(base);
  out.value = normalized;
  updateEpochExample(normalized);
}

function normalizeOutputName(value) {
  return String(value || "")
    .trim()
    .replace(/\s+/g, "_").replace(/[^A-Za-z0-9_-]/g, "").replace(/^[-_]+/, "").slice(0, 80);
}

function updateEpochExample(name) {
  const el = document.getElementById("tp-epoch-example");
  if (!el) return;
  const safe = normalizeOutputName(name) || "output_name";
  el.textContent = `Example file: ${safe}000001.safetensors`;
  updateTpSummary();
}

// TOML Config Modal Functions
window.showTomlConfig = async function () {
  const modal = document.getElementById("toml-modal");
  const content = document.getElementById("toml-content");
  const pathEl = document.getElementById("toml-modal-path");
  const saveStatus = document.getElementById("toml-save-status");
  
  if (!modal || !content) return;
  
  // Show modal with loading state
  modal.classList.add("show");
  content.className = "toml-loading";
  content.textContent = "Loading configuration...";
  if (saveStatus) saveStatus.textContent = "";
  
  try {
    // Fetch TOML content from backend
    const data = await fetchJson("/api/trainpilot/toml");
    
    if (data.content) {
      content.className = "";
      content.innerHTML = `<textarea id="toml-editor" class="toml-editor" spellcheck="false"></textarea>`;
      const editor = document.getElementById("toml-editor");
      if (editor) editor.value = data.content;
      if (pathEl) pathEl.textContent = data.path || "/workspace/config/trainpilot/newlora.toml";
      const pathInput = document.getElementById("tp-toml");
      const pathLabel = document.getElementById("toml-config-path");
      if (pathInput) pathInput.value = data.path || "/workspace/config/trainpilot/newlora.toml";
      if (pathLabel && data.path) pathLabel.textContent = data.path;
    } else {
      content.className = "toml-loading";
      content.textContent = "Configuration file not found or empty.";
    }
  } catch (error) {
    content.className = "toml-loading";
    content.textContent = `Error loading configuration: ${error.message}`;
  }
};

window.saveTomlConfig = async function () {
  const editor = document.getElementById("toml-editor");
  const saveBtn = document.getElementById("toml-save-btn");
  const saveStatus = document.getElementById("toml-save-status");
  if (!editor) return;
  const content = editor.value || "";
  if (saveBtn) saveBtn.disabled = true;
  if (saveStatus) saveStatus.textContent = "Saving...";
  try {
    const data = await fetchJson("/api/trainpilot/toml", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    if (saveStatus) saveStatus.textContent = "Saved.";
    refreshTpPreflight();
    const pathInput = document.getElementById("tp-toml");
    const pathLabel = document.getElementById("toml-config-path");
    const modalPath = document.getElementById("toml-modal-path");
    if (pathInput && data.path) pathInput.value = data.path;
    if (pathLabel && data.path) pathLabel.textContent = data.path;
    if (modalPath && data.path) modalPath.textContent = data.path;
  } catch (error) {
    if (saveStatus) saveStatus.textContent = error.message || String(error);
  } finally {
    if (saveBtn) saveBtn.disabled = false;
  }
};

window.closeTomlConfig = function (evt) {
  if (evt && evt.target) {
    const t = evt.target;
    const isBackdrop = t.id === "toml-modal";
    const isCloseBtn = t.classList && t.classList.contains("modal-close");
    if (!isBackdrop && !isCloseBtn) return;
  }
  const modal = document.getElementById("toml-modal");
  if (modal) modal.classList.remove("show");
};

// Close modal with Escape key
window.addEventListener("keydown", function (event) {
  if (event.key === "Escape") {
    const modal = document.getElementById("toml-modal");
    if (modal && modal.classList.contains("show")) closeTomlConfig();
  }
});
