window.initSettings = async function () {
  const els = {
    passwordEnabled: document.getElementById("settings-password-enabled"),
    passwordInput: document.getElementById("settings-password"),
    passwordSave: document.getElementById("settings-password-save"),
    passwordStatus: document.getElementById("settings-password-status"),
    logout: document.getElementById("settings-logout"),
    hfInput: document.getElementById("settings-hf-token"),
    hfSave: document.getElementById("settings-hf-save"),
    hfClear: document.getElementById("settings-hf-clear"),
    hfStatus: document.getElementById("settings-hf-status"),
    copilotInput: document.getElementById("settings-copilot-token"),
    copilotSave: document.getElementById("settings-copilot-save"),
    copilotClear: document.getElementById("settings-copilot-clear"),
    copilotStatus: document.getElementById("settings-copilot-status"),
    mediapilotInput: document.getElementById("settings-mediapilot-password"),
    mediapilotSave: document.getElementById("settings-mediapilot-save"),
    mediapilotStatus: document.getElementById("settings-mediapilot-status"),
    theme: document.getElementById("settings-theme"),
    uiSave: document.getElementById("settings-ui-save"),
    sidebarCompact: document.getElementById("settings-sidebar-compact"),
    uiStatus: document.getElementById("settings-ui-status"),
    shutdownMode: document.getElementById("settings-shutdown-mode"),
    shutdownHours: document.getElementById("settings-shutdown-hours"),
    shutdownMins: document.getElementById("settings-shutdown-mins"),
    shutdownSecs: document.getElementById("settings-shutdown-secs"),
    shutdownSave: document.getElementById("settings-shutdown-save"),
    shutdownStatus: document.getElementById("settings-shutdown-status"),
    jupyterToken: document.getElementById("settings-jupyter-token"),
    jupyterOrigin: document.getElementById("settings-jupyter-origin"),
    jupyterSave: document.getElementById("settings-jupyter-save"),
    jupyterStatus: document.getElementById("settings-jupyter-status"),
    copilotAllowUrls: document.getElementById("settings-copilot-allow-urls"),
    copilotDefaultsSave: document.getElementById("settings-copilot-defaults-save"),
    copilotDefaultsStatus: document.getElementById("settings-copilot-defaults-status"),
  };

  async function refresh() {
    const [settings, hf, copilot] = await Promise.all([
      fetchJson("/api/settings"),
      fetchJson("/api/hf-token"),
      fetchJson("/api/copilot/token"),
    ]);
    if (els.passwordEnabled) els.passwordEnabled.checked = !!(settings && settings.password_enabled);
    if (els.theme) els.theme.value = settings && settings.theme === "dark" ? "dark" : "light";
    if (els.sidebarCompact) els.sidebarCompact.checked = !!(settings && settings.sidebar_compact);
    if (els.shutdownMode) els.shutdownMode.value = (settings && settings.shutdown_mode) || "";
    if (els.shutdownHours) els.shutdownHours.value = String((settings && settings.shutdown_default_hours) ?? 0);
    if (els.shutdownMins) els.shutdownMins.value = String((settings && settings.shutdown_default_mins) ?? 1);
    if (els.shutdownSecs) els.shutdownSecs.value = String((settings && settings.shutdown_default_secs) ?? 0);
    if (els.copilotAllowUrls) els.copilotAllowUrls.checked = !!(settings && settings.copilot_allow_all_urls);
    if (els.jupyterOrigin) els.jupyterOrigin.value = (settings && settings.jupyter_allow_origin_pat) || "";
    if (els.passwordInput) {
      els.passwordInput.value = "";
      els.passwordInput.placeholder = settings && settings.password_enabled
        ? "Enter new password to change it"
        : "Set ControlPilot password";
      if (els.passwordStatus) els.passwordStatus.textContent = settings && settings.password_enabled
        ? "Password saved. Enter a new value only to replace it."
        : "Not configured.";
    }
    if (els.hfInput) {
      els.hfInput.value = "";
      els.hfInput.placeholder = hf && hf.set ? "HF_TOKEN saved" : "HF_TOKEN";
      if (els.hfStatus) els.hfStatus.textContent = hf && hf.set
        ? "•••••••• saved. Enter a new token to replace it."
        : "Not configured.";
    }
    if (els.copilotInput) {
      els.copilotInput.value = "";
      els.copilotInput.placeholder = copilot && copilot.set ? "Copilot token saved" : "COPILOT_GITHUB_TOKEN";
      if (els.copilotStatus) els.copilotStatus.textContent = copilot && copilot.set
        ? "•••••••• saved. Enter a new token to replace it."
        : "Not configured.";
    }
    if (els.mediapilotInput) {
      els.mediapilotInput.value = "";
      els.mediapilotInput.placeholder = settings && settings.mediapilot_password_set
        ? "Password set. Enter new value or leave empty to remove it"
        : "Empty = no password";
      if (els.mediapilotStatus) els.mediapilotStatus.textContent = settings && settings.mediapilot_password_set
        ? "•••••••• saved. Enter a new password to replace it."
        : "Not configured.";
    }
    if (els.jupyterToken) {
      els.jupyterToken.value = "";
      els.jupyterToken.placeholder = settings && settings.jupyter_token_set
        ? "Token set. Enter new value or leave empty to regenerate"
        : "Leave empty to regenerate on restart";
      if (els.jupyterStatus) els.jupyterStatus.textContent = settings && settings.jupyter_token_set
        ? "•••••••• saved. Enter a new token to replace it."
        : "Not configured; Jupyter will generate one on restart.";
    }
  }

  async function savePassword() {
    const enabled = !!els.passwordEnabled?.checked;
    const password = els.passwordInput?.value || "";
    if (els.passwordStatus) els.passwordStatus.textContent = "Saving...";
    try {
      await fetchJson("/api/settings/password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled, password }),
      });
      if (els.passwordStatus) {
        els.passwordStatus.textContent = enabled ? "Protection enabled." : "Protection disabled.";
      }
      await refresh();
    } catch (e) {
      if (els.passwordStatus) els.passwordStatus.textContent = e.message || String(e);
    }
  }

  async function saveToken(url, inputEl, statusEl, successText, clear = false) {
    const token = clear ? "" : ((inputEl && inputEl.value) || "").trim();
    if (!clear && !token) {
      if (statusEl) statusEl.textContent = "Enter a token.";
      inputEl?.focus();
      return;
    }
    if (statusEl) statusEl.textContent = clear ? "Clearing..." : "Saving...";
    try {
      await fetchJson(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
      if (statusEl) statusEl.textContent = successText;
    } catch (e) {
      if (statusEl) statusEl.textContent = e.message || String(e);
      throw e;
    }
  }

  async function saveMediaPilotPassword() {
    const password = ((els.mediapilotInput && els.mediapilotInput.value) || "").trim();
    if (els.mediapilotStatus) els.mediapilotStatus.textContent = password ? "Saving..." : "Clearing...";
    try {
      const res = await fetchJson("/api/settings/mediapilot/password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (els.mediapilotStatus) {
        els.mediapilotStatus.textContent = res && res.set
          ? "MediaPilot password saved."
          : "MediaPilot password cleared.";
      }
      await refresh();
    } catch (e) {
      if (els.mediapilotStatus) els.mediapilotStatus.textContent = e.message || String(e);
    }
  }

  async function saveUiSettings() {
    if (els.uiStatus) els.uiStatus.textContent = "Saving...";
    try {
      const res = await fetchJson("/api/settings/ui", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          theme: els.theme?.value || "light",
          sidebar_compact: !!els.sidebarCompact?.checked,
        }),
      });
      if (typeof window.applyControlPilotUiSettings === "function") {
        window.applyControlPilotUiSettings(res);
      }
      if (els.uiStatus) els.uiStatus.textContent = "UI defaults saved.";
    } catch (e) {
      if (els.uiStatus) els.uiStatus.textContent = e.message || String(e);
    }
  }

  async function saveShutdownDefaults() {
    if (els.shutdownStatus) els.shutdownStatus.textContent = "Saving...";
    try {
      await fetchJson("/api/settings/shutdown-defaults", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          shutdown_mode: els.shutdownMode?.value || "",
          hours: Number(els.shutdownHours?.value || 0),
          mins: Number(els.shutdownMins?.value || 0),
          secs: Number(els.shutdownSecs?.value || 0),
        }),
      });
      if (els.shutdownStatus) els.shutdownStatus.textContent = "Shutdown defaults saved.";
      if (typeof window.refreshControlPilotSettings === "function") {
        await window.refreshControlPilotSettings();
      }
    } catch (e) {
      if (els.shutdownStatus) els.shutdownStatus.textContent = e.message || String(e);
    }
  }

  async function saveJupyterSettings() {
    if (els.jupyterStatus) els.jupyterStatus.textContent = "Saving and restarting Jupyter...";
    try {
      await fetchJson("/api/settings/jupyter", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: els.jupyterToken?.value ?? "",
          allow_origin_pat: els.jupyterOrigin?.value || "",
        }),
      });
      if (els.jupyterStatus) els.jupyterStatus.textContent = "Jupyter settings saved and service restarted.";
      await refresh();
    } catch (e) {
      if (els.jupyterStatus) els.jupyterStatus.textContent = e.message || String(e);
    }
  }

  async function saveCopilotDefaults() {
    if (els.copilotDefaultsStatus) els.copilotDefaultsStatus.textContent = "Saving...";
    try {
      const res = await fetchJson("/api/settings/copilot-defaults", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ allow_all_urls: !!els.copilotAllowUrls?.checked }),
      });
      if (typeof window.applyCopilotDrawerDefaults === "function") {
        window.applyCopilotDrawerDefaults(res);
      }
      if (els.copilotDefaultsStatus) els.copilotDefaultsStatus.textContent = "Copilot drawer defaults saved.";
    } catch (e) {
      if (els.copilotDefaultsStatus) els.copilotDefaultsStatus.textContent = e.message || String(e);
    }
  }

  if (els.passwordSave && !els.passwordSave.dataset.bound) {
    els.passwordSave.dataset.bound = "1";
    els.passwordSave.addEventListener("click", savePassword);
  }
  if (els.logout && !els.logout.dataset.bound) {
    els.logout.dataset.bound = "1";
    els.logout.addEventListener("click", async () => {
      try {
        await fetchJson("/api/settings/auth/logout", { method: "POST" });
      } catch (e) {
        // Ignore and show login either way.
      }
      if (typeof window.showControlPilotLogin === "function") {
        window.showControlPilotLogin("Logged out.");
      }
    });
  }
  if (els.hfSave && !els.hfSave.dataset.bound) {
    els.hfSave.dataset.bound = "1";
    els.hfSave.addEventListener("click", async () => {
      await saveToken("/api/hf-token", els.hfInput, els.hfStatus, "HF_TOKEN saved.");
      await refresh();
    });
  }
  if (els.hfClear && !els.hfClear.dataset.bound) {
    els.hfClear.dataset.bound = "1";
    els.hfClear.addEventListener("click", async () => {
      await saveToken("/api/hf-token", els.hfInput, els.hfStatus, "HF_TOKEN cleared.", true);
      await refresh();
    });
  }
  if (els.copilotSave && !els.copilotSave.dataset.bound) {
    els.copilotSave.dataset.bound = "1";
    els.copilotSave.addEventListener("click", async () => {
      await saveToken("/api/copilot/token", els.copilotInput, els.copilotStatus, "Copilot token saved.");
      await fetchJson("/api/settings/copilot/restart", { method: "POST" });
      if (els.copilotStatus) els.copilotStatus.textContent = "Copilot token saved and sidecar restarted.";
      await refresh();
    });
  }
  if (els.copilotClear && !els.copilotClear.dataset.bound) {
    els.copilotClear.dataset.bound = "1";
    els.copilotClear.addEventListener("click", async () => {
      await saveToken("/api/copilot/token", els.copilotInput, els.copilotStatus, "Copilot token cleared.", true);
      await fetchJson("/api/settings/copilot/restart", { method: "POST" });
      if (els.copilotStatus) els.copilotStatus.textContent = "Copilot token cleared and sidecar restarted.";
      await refresh();
    });
  }
  if (els.mediapilotSave && !els.mediapilotSave.dataset.bound) {
    els.mediapilotSave.dataset.bound = "1";
    els.mediapilotSave.addEventListener("click", saveMediaPilotPassword);
  }
  if (els.uiSave && !els.uiSave.dataset.bound) {
    els.uiSave.dataset.bound = "1";
    els.uiSave.addEventListener("click", saveUiSettings);
  }
  if (els.shutdownSave && !els.shutdownSave.dataset.bound) {
    els.shutdownSave.dataset.bound = "1";
    els.shutdownSave.addEventListener("click", saveShutdownDefaults);
  }
  if (els.jupyterSave && !els.jupyterSave.dataset.bound) {
    els.jupyterSave.dataset.bound = "1";
    els.jupyterSave.addEventListener("click", saveJupyterSettings);
  }
  if (els.copilotDefaultsSave && !els.copilotDefaultsSave.dataset.bound) {
    els.copilotDefaultsSave.dataset.bound = "1";
    els.copilotDefaultsSave.addEventListener("click", saveCopilotDefaults);
  }

  try {
    await refresh();
  } catch (e) {
    if (els.passwordStatus) els.passwordStatus.textContent = e.message || String(e);
  }
};
