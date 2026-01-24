// Global Copilot drawer UI (persists across subpages)
(function () {
  const fab = document.getElementById("copilot-fab");
  const drawer = document.getElementById("copilot-drawer");
  const closeBtn = document.getElementById("copilot-drawer-close");
  const startBtn = document.getElementById("copilot-drawer-start");
  const statusEl = document.getElementById("copilot-drawer-status");
  const promptEl = document.getElementById("copilot-drawer-prompt");
  const sendBtn = document.getElementById("copilot-drawer-send");
  const allowUrlsEl = document.getElementById("copilot-drawer-allow-urls");
  const clearBtn = document.getElementById("copilot-drawer-clear");
  const outEl = document.getElementById("copilot-drawer-output");
  const runningEl = document.getElementById("copilot-drawer-running");

  if (!fab || !drawer || !statusEl || !promptEl || !sendBtn || !outEl) return;

  let lastStatusAt = 0;

  function setDrawerOpen(open) {
    drawer.style.display = open ? "" : "none";
    if (open) refreshStatus(true);
  }

  async function refreshStatus(force = false) {
    const now = Date.now();
    if (!force && now - lastStatusAt < 15000) return;
    lastStatusAt = now;
    statusEl.textContent = "Loading…";
    try {
      const st = await fetchJson("/api/copilot/status");
      const version = st.copilot_version ? ` (${st.copilot_version})` : "";
      statusEl.textContent = st.copilot_in_path
        ? `Ready. copilot found${version}.`
        : "Sidecar reachable but copilot not found in PATH.";
    } catch (e) {
      statusEl.textContent = `Sidecar not running/reachable. (${e.message || e})`;
    }
  }

  async function startSidecar() {
    try {
      await fetchJson(`/api/services/${encodeURIComponent("copilot")}/start`, { method: "POST" });
      await new Promise(r => setTimeout(r, 400));
      await refreshStatus(true);
    } catch (e) {
      alert(`Failed to start sidecar: ${e.message || e}`);
    }
  }

  async function runPrompt() {
    const prompt = (promptEl.value || "").trim();
    if (!prompt) return;
    sendBtn.disabled = true;
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
      outEl.scrollTop = outEl.scrollHeight;
      await refreshStatus(true);
    } catch (e) {
      outEl.textContent = `Error: ${e.message || e}`;
    } finally {
      sendBtn.disabled = false;
      if (runningEl) runningEl.style.display = "none";
    }
  }

  if (fab) fab.addEventListener("click", () => setDrawerOpen(drawer.style.display === "none"));
  if (closeBtn) closeBtn.addEventListener("click", () => setDrawerOpen(false));
  if (startBtn) startBtn.addEventListener("click", startSidecar);
  if (clearBtn) clearBtn.addEventListener("click", () => { outEl.textContent = ""; });
  sendBtn.addEventListener("click", runPrompt);
  promptEl.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") runPrompt();
  });

  // Lazy status refresh if drawer stays open.
  setInterval(() => {
    if (drawer.style.display !== "none") refreshStatus(false);
  }, 5000);
})();

