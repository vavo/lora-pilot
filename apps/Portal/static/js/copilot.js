window.initCopilot = async function () {
  const statusEl = document.getElementById("copilot-status");
  const outEl = document.getElementById("copilot-output");
  const promptEl = document.getElementById("copilot-prompt");
  const runEl = document.getElementById("copilot-send");
  const runningEl = document.getElementById("copilot-running");
  const refreshEl = document.getElementById("copilot-refresh");
  const startEl = document.getElementById("copilot-start");
  const allowUrlsEl = document.getElementById("copilot-allow-urls");
  const tokenEl = document.getElementById("copilot-token");
  const tokenStatusEl = document.getElementById("copilot-token-status");
  const saveTokenEl = document.getElementById("copilot-save-token");
  const clearTokenEl = document.getElementById("copilot-clear-token");

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

  async function refreshTokenStatus() {
    if (!tokenStatusEl) return;
    try {
      const st = await fetchJson("/api/copilot/token");
      tokenStatusEl.textContent = st && st.set ? "Token saved" : "No token";
      if (tokenEl && st && st.set) tokenEl.placeholder = "Token saved (leave blank to keep)";
      if (tokenEl && (!st || !st.set)) tokenEl.placeholder = "GitHub token (COPILOT_GITHUB_TOKEN)";
    } catch (e) {
      tokenStatusEl.textContent = "Token status unavailable";
    }
  }

  async function saveToken(token) {
    const val = String(token || "").trim();
    if (!val) {
      alert("Enter a token first.");
      return;
    }
    if (tokenStatusEl) tokenStatusEl.textContent = "Saving...";
    try {
      await fetchJson("/api/copilot/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: val }),
      });
      await fetchJson(`/api/services/${encodeURIComponent("copilot")}/restart`, { method: "POST" });
      if (tokenEl) tokenEl.value = "";
      if (tokenStatusEl) tokenStatusEl.textContent = "Saved + sidecar restarted";
      await refreshStatus();
      await refreshTokenStatus();
    } catch (e) {
      if (tokenStatusEl) tokenStatusEl.textContent = `Save failed`;
      alert(`Failed to save token: ${e.message || e}`);
    }
  }

  async function clearToken() {
    if (!confirm("Clear saved Copilot token and restart sidecar?")) return;
    if (tokenStatusEl) tokenStatusEl.textContent = "Clearing...";
    try {
      await fetchJson("/api/copilot/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: "" }),
      });
      await fetchJson(`/api/services/${encodeURIComponent("copilot")}/restart`, { method: "POST" });
      if (tokenEl) tokenEl.value = "";
      if (tokenStatusEl) tokenStatusEl.textContent = "Cleared + sidecar restarted";
      await refreshStatus();
      await refreshTokenStatus();
    } catch (e) {
      if (tokenStatusEl) tokenStatusEl.textContent = `Clear failed`;
      alert(`Failed to clear token: ${e.message || e}`);
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
    if (runningEl) runningEl.classList.remove("is-hidden");
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
      if (runningEl) runningEl.classList.add("is-hidden");
    }
  }

  if (refreshEl) refreshEl.addEventListener("click", refreshStatus);
  if (startEl) startEl.addEventListener("click", startSidecar);
  if (saveTokenEl) saveTokenEl.addEventListener("click", () => saveToken(tokenEl?.value || ""));
  if (clearTokenEl) clearTokenEl.addEventListener("click", clearToken);
  runEl.addEventListener("click", runPrompt);

  await refreshStatus();
  await refreshTokenStatus();
};
