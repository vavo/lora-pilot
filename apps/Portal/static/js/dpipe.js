let dpLogTimer = null;

window.initDpipe = function () {
  const status = document.getElementById("dp-status");
  if (status) status.textContent = "";
  const wandb = document.getElementById("dp-enable-wandb");
  const fields = ["dp-wandb-name","dp-wandb-proj","dp-wandb-key"].map(id => document.getElementById(id));
  if (wandb && !wandb.dataset.bound) {
    wandb.dataset.bound = "1";
    wandb.addEventListener("change", () => {
      fields.forEach(f => { if (f) f.style.display = wandb.checked ? "" : "none"; });
    });
    fields.forEach(f => { if (f) f.style.display = wandb.checked ? "" : "none"; });
  }
  startLogPoll();
};

window.startDpipe = async function () {
  const status = document.getElementById("dp-status");
  if (status) status.textContent = "Starting...";
  try {
    const payload = {
      dataset_path: val("dp-dataset"),
      config_dir: val("dp-config"),
      output_dir: val("dp-output"),
      transformer_path: val("dp-transformer"),
      vae_path: val("dp-vae"),
      llm_path: val("dp-llm"),
      clip_path: val("dp-clip"),
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

function startLogPoll() {
  if (dpLogTimer) return;
  const poll = async () => {
    const pre = document.getElementById("dp-logs");
    if (!pre) return;
    try {
      const data = await fetchJson("/dpipe/train/logs?limit=500");
      const lines = Object.values(data.logs || {}).flat();
      pre.textContent = lines.join("\n");
    } catch (e) {
      // ignore
    }
  };
  poll();
  dpLogTimer = setInterval(poll, 2000);
}

window.stopDpipeLog = function () {
  if (dpLogTimer) clearInterval(dpLogTimer);
  dpLogTimer = null;
};

function val(id) { return document.getElementById(id)?.value.trim() || ""; }
function num(id) { return parseInt(val(id) || "0", 10); }
function checked(id) { return !!document.getElementById(id)?.checked; }
