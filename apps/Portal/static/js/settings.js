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
  };

  async function refresh() {
    const [settings, hf, copilot] = await Promise.all([
      fetchJson("/api/settings"),
      fetchJson("/api/hf-token"),
      fetchJson("/api/copilot/token"),
    ]);
    if (els.passwordEnabled) els.passwordEnabled.checked = !!(settings && settings.password_enabled);
    if (els.passwordInput) {
      els.passwordInput.value = "";
      els.passwordInput.placeholder = settings && settings.password_enabled
        ? "Enter new password to change it"
        : "Set ControlPilot password";
    }
    if (els.hfInput) {
      els.hfInput.value = "";
      els.hfInput.placeholder = hf && hf.set ? "HF_TOKEN saved" : "HF_TOKEN";
    }
    if (els.copilotInput) {
      els.copilotInput.value = "";
      els.copilotInput.placeholder = copilot && copilot.set ? "Copilot token saved" : "COPILOT_GITHUB_TOKEN";
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

  try {
    await refresh();
  } catch (e) {
    if (els.passwordStatus) els.passwordStatus.textContent = e.message || String(e);
  }
};
