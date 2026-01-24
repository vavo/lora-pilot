window.initCopilot = async function () {
  const statusEl = document.getElementById("copilot-status");
  const outEl = document.getElementById("copilot-output");
  const promptEl = document.getElementById("copilot-prompt");
  const runEl = document.getElementById("copilot-send");
  const runningEl = document.getElementById("copilot-running");
  const refreshEl = document.getElementById("copilot-refresh");
  const startEl = document.getElementById("copilot-start");
  const allowUrlsEl = document.getElementById("copilot-allow-urls");

  if (!statusEl || !outEl || !promptEl || !runEl) return;

  async function refreshStatus() {
    statusEl.textContent = "Loading...";
    try {
      const st = await fetchJson("/api/copilot/status");
      const version = st.copilot_version ? ` (${st.copilot_version})` : "";
      statusEl.textContent = st.copilot_in_path
        ? `Sidecar reachable. copilot found${version}. Config: ${st.config_json}`
        : `Sidecar reachable but copilot not found in PATH.`;
    } catch (e) {
      statusEl.textContent = `Copilot sidecar not running/reachable. Start it in Services or click "Start sidecar". (${e.message || e})`;
    }
  }

  async function startSidecar() {
    try {
      await fetchJson(`/api/services/${encodeURIComponent("copilot")}/start`, { method: "POST" });
      await new Promise(r => setTimeout(r, 400));
      await refreshStatus();
    } catch (e) {
      alert(`Failed to start sidecar: ${e.message || e}`);
    }
  }

  async function runPrompt() {
    const prompt = (promptEl.value || "").trim();
    if (!prompt) return;
    outEl.textContent = "";
    runEl.disabled = true;
    if (runningEl) runningEl.style.display = "";
    try {
      const payload = {
        prompt,
        allow_all_tools: true,
        allow_all_paths: true,
        allow_all_urls: !!(allowUrlsEl && allowUrlsEl.checked),
      };
      const res = await fetchJson("/api/copilot/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      const combined = [(res.stdout || "").trim(), (res.stderr || "").trim()].filter(Boolean).join("\n\n");
      outEl.textContent = combined || "(no output)";
    } catch (e) {
      outEl.textContent = `Error: ${e.message || e}`;
    } finally {
      runEl.disabled = false;
      if (runningEl) runningEl.style.display = "none";
    }
  }

  if (refreshEl) refreshEl.addEventListener("click", refreshStatus);
  if (startEl) startEl.addEventListener("click", startSidecar);
  runEl.addEventListener("click", runPrompt);

  await refreshStatus();
};

