let dpLogTimer = null;
const DP_STORAGE_KEY = "dpipeSettings";
const DP_SENSITIVE_FIELDS = new Set([
  "dp-wandb-key",
]);
const DP_FIELDS = [
  "dp-dataset",
  "dp-run",
  "dp-transformer",
  "dp-vae",
  "dp-llm",
  "dp-clip",
  "dp-epochs",
  "dp-batch",
  "dp-lr",
  "dp-gas",
  "dp-rank",
  "dp-dtype",
  "dp-save-every",
  "dp-eval-every",
  "dp-ckpt-mins",
  "dp-warmup",
  "dp-gradclip",
  "dp-steps-print",
  "dp-res",
  "dp-frames",
  "dp-ar",
  "dp-repeats",
  "dp-resume",
  "dp-double",
  "dp-optim",
  "dp-betas",
  "dp-wd",
  "dp-eps",
  "dp-vmode",
  "dp-eval-mb",
  "dp-eval-gas",
  "dp-enable-wandb",
  "dp-wandb-name",
  "dp-wandb-proj",
  "dp-wandb-key",
];

window.initDpipe = function () {
  const status = document.getElementById("dp-status");
  if (status) status.textContent = "";
  loadDpipeSettings();
  bindDpipeSettings();
  loadDpipeDatasets();
  const wandb = document.getElementById("dp-enable-wandb");
  const fields = ["dp-wandb-name","dp-wandb-proj","dp-wandb-key"].map(id => document.getElementById(id));
  if (wandb && !wandb.dataset.bound) {
    wandb.dataset.bound = "1";
    wandb.addEventListener("change", () => {
      fields.forEach(f => { if (f) f.classList.toggle("is-hidden", !wandb.checked); });
    });
    fields.forEach(f => { if (f) f.classList.toggle("is-hidden", !wandb.checked); });
  }
  startLogPoll();
};

window.startDpipe = async function () {
  const status = document.getElementById("dp-status");
  if (status) status.textContent = "Starting...";
  try {
    saveDpipeSettings();
    const modelPaths = {
      transformer_path: val("dp-transformer"),
      vae_path: val("dp-vae"),
      llm_path: val("dp-llm"),
      clip_path: val("dp-clip"),
    };
    const validate = await fetchJson("/dpipe/train/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(modelPaths),
    });
    if (validate && validate.missing && validate.missing.length) {
      const missingList = validate.missing.map(m => `${m.field}: ${m.path}`).join("\n");
      if (status) status.textContent = "Missing model files";
      const go = confirm(`Missing model files:\n${missingList}\n\nOpen Models page to download?`);
      if (go) {
        if (window.loadSection) {
          window.loadSection("models");
        } else {
          window.location.href = "/#models";
        }
      }
      return;
    }
    const payload = {
      dataset_name: val("dp-dataset"),
      run_name: val("dp-run"),
      transformer_path: modelPaths.transformer_path,
      vae_path: modelPaths.vae_path,
      llm_path: modelPaths.llm_path,
      clip_path: modelPaths.clip_path,
      epochs: num("dp-epochs"),
      batch_size: num("dp-batch"),
      learning_rate: parseFloat(val("dp-lr")),
      gradient_accumulation_steps: num("dp-gas"),
      rank: num("dp-rank"),
      dtype: val("dp-dtype"),
      save_every: num("dp-save-every"),
      eval_every: num("dp-eval-every"),
      checkpoint_every_n_minutes: num("dp-ckpt-mins"),
      warmup_steps: num("dp-warmup"),
      gradient_clipping: parseFloat(val("dp-gradclip")),
      steps_per_print: num("dp-steps-print"),
      resolutions_input: val("dp-res"),
      frame_buckets: val("dp-frames"),
      ar_buckets: val("dp-ar"),
      num_repeats: num("dp-repeats"),
      resume_from_checkpoint: checked("dp-resume"),
      only_double_blocks: checked("dp-double"),
      optimizer_type: val("dp-optim"),
      betas: val("dp-betas"),
      weight_decay: parseFloat(val("dp-wd")),
      eps: parseFloat(val("dp-eps")),
      video_clip_mode: val("dp-vmode"),
      eval_micro_batch_size_per_gpu: num("dp-eval-mb"),
      eval_gradient_accumulation_steps: num("dp-eval-gas"),
      enable_ar_bucket: true,
      enable_wandb: checked("dp-enable-wandb"),
      wandb_run_name: val("dp-wandb-name"),
      wandb_tracker_name: val("dp-wandb-proj"),
      wandb_api_key: val("dp-wandb-key"),
    };
    await fetchJson("/dpipe/train/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (status) status.textContent = "Running...";
  } catch (e) {
    if (status) status.textContent = `Error: ${e.message || e}`;
  }
};

window.stopDpipe = async function () {
  const status = document.getElementById("dp-status");
  if (status) status.textContent = "Stopping...";
  try {
    await fetchJson("/dpipe/train/stop", { method: "POST" });
    if (status) status.textContent = "Stopped.";
  } catch (e) {
    if (status) status.textContent = `Error: ${e.message || e}`;
  }
};

function bindDpipeSettings() {
  DP_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (!el || el.dataset.bound) return;
    el.dataset.bound = "1";
    const handler = () => {
      if (id === "dp-run" && el.type !== "checkbox") {
        const normalized = normalizeDpipeRunName(el.value || "");
        if (normalized !== el.value) el.value = normalized;
        el.dataset.autoFilled = "0";
      }
      saveDpipeSettings();
    };
    el.addEventListener("change", handler);
    el.addEventListener("input", handler);
  });
}

function loadDpipeSettings() {
  const data = loadDpipeSettingsData();
  DP_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (!el || DP_SENSITIVE_FIELDS.has(id) || !(id in data)) return;
    const value = data[id];
    if (el.type === "checkbox") {
      el.checked = Boolean(value);
    } else if (value !== null && value !== undefined) {
      el.value = String(value);
    }
  });
}

function loadDpipeSettingsData() {
  try {
    return JSON.parse(localStorage.getItem(DP_STORAGE_KEY) || "{}");
  } catch (e) {
    return {};
  }
}

function saveDpipeSettings() {
  const data = {};
  DP_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    if (DP_SENSITIVE_FIELDS.has(id)) return;
    if (el.type === "checkbox") {
      data[id] = el.checked;
    } else {
      data[id] = el.value;
    }
  });
  try {
    localStorage.setItem(DP_STORAGE_KEY, JSON.stringify(data));
  } catch (e) {
    // Ignore storage errors (private mode/quota)
  }
}

async function loadDpipeDatasets() {
  const sel = document.getElementById("dp-dataset");
  const status = document.getElementById("dp-status");
  if (!sel) return;
  const saved = loadDpipeSettingsData();
  const savedValue = typeof saved["dp-dataset"] === "string" ? saved["dp-dataset"] : "";
  if (!sel.dataset.boundDataset) {
    sel.dataset.boundDataset = "1";
    sel.addEventListener("change", () => {
      syncDpipeRunName();
      saveDpipeSettings();
    });
  }
  sel.innerHTML = `<option value="">Loading datasets...</option>`;
  try {
    const data = await fetchJson("/api/datasets");
    sel.innerHTML = "";
    if (!Array.isArray(data) || !data.length) {
      sel.innerHTML = `<option value="">No datasets found</option>`;
      return;
    }
    data.forEach(d => {
      const opt = document.createElement("option");
      opt.value = String(d.name || "");
      opt.textContent = `${d.display || d.name} (${d.images || 0} images)`;
      sel.appendChild(opt);
    });
    if (savedValue && Array.from(sel.options).some(opt => opt.value === savedValue)) {
      sel.value = savedValue;
    } else if (!sel.value && sel.options.length) {
      sel.selectedIndex = 0;
    }
    syncDpipeRunName();
  } catch (e) {
    sel.innerHTML = `<option value="">No datasets found</option>`;
    if (status) status.textContent = `Error loading datasets: ${e.message || e}`;
  }
}

function startLogPoll() {
  if (dpLogTimer) return;
  const poll = async () => {
    const pre = document.getElementById("dp-logs");
    if (!pre) return;
    try {
      const data = await fetchJson("/dpipe/train/logs?limit=500");
      const lines = normalizeDpipeLines(data);
      pre.textContent = lines.join("\n");
    } catch (e) {
      // ignore when no logs yet
    }
  };
  poll();
  dpLogTimer = setInterval(poll, 2000);
}

window.stopDpipeLog = function () {
  if (dpLogTimer) clearInterval(dpLogTimer);
  dpLogTimer = null;
};

function normalizeDpipeLines(data) {
  if (!data) return [];
  if (Array.isArray(data.lines)) return data.lines;
  const logs = data.logs || data.log || {};
  if (Array.isArray(logs)) return logs;
  if (logs && typeof logs === "object") {
    // Use Array.prototype.reduce() as fallback for older browsers without .flat()
    return Object.values(logs).reduce((acc, val) => acc.concat(val), []);
  }
  return [];
}

function syncDpipeRunName(force = false) {
  const run = document.getElementById("dp-run");
  const dataset = document.getElementById("dp-dataset");
  if (!run || !dataset) return;
  const isAutoFilled = run.dataset.autoFilled === "1";
  if (run.value.trim() && !force && !isAutoFilled) return;
  const label = dataset.options[dataset.selectedIndex]?.textContent || dataset.value || "dpipe_run";
  const base = label.replace(/\s*\([^)]*\)\s*$/, "").trim();
  run.value = normalizeDpipeRunName(base);
  run.dataset.autoFilled = "1";
}

function normalizeDpipeRunName(value) {
  return String(value || "")
    .trim()
    .replace(/\s+/g, "_");
}

function val(id) { return document.getElementById(id)?.value.trim() || ""; }
function num(id) { return parseInt(val(id) || "0", 10); }
function checked(id) { return !!document.getElementById(id)?.checked; }
