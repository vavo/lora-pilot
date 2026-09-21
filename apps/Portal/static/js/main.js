const sections = ["dashboard", "services", "storage", "models", "datasets", "mediapilot", "comfyui", "tagpilot", "trainpilot", "dpipe", "docs", "settings", "support"];
const viewCache = {};
let currentSection = null;
let activeScreen = null;
const initialSection = new URLSearchParams(window.location.search).get("open") === "comfyui" ? "comfyui" : (sections.includes(location.hash.slice(1)) ? location.hash.slice(1) : "dashboard");
let controlPilotUnlocked = false;
window.controlPilotSettings = window.controlPilotSettings || null;
const viewMap = {
  dashboard: { view: "/views/dashboard.html", init: screen => window.initDashboard && window.initDashboard(screen), stop: () => window.stopDashboard?.() },
  storage: { view: "/views/storage.html", init: screen => window.storagePage.init(screen), stop: () => window.storagePage.stop() },
  services: { view: "/views/services.html", init: screen => window.initServices && window.initServices(screen), stop: () => window.stopServices?.() },
  models: { view: "/views/models.html?v=20260907b", init: screen => window.initModels && window.initModels(screen), stop: () => window.stopModels?.() },
  datasets: { view: "/views/datasets.html", init: screen => window.initDatasets && window.initDatasets(screen) },
  mediapilot: { view: "/views/mediapilot.html?v=20260905a", init: screen => window.initMediapilot && window.initMediapilot(screen) },
  comfyui: { view: "/views/comfyui.html", init: screen => window.initComfyUI && window.initComfyUI(screen), stop: () => window.stopComfyUI?.() },
  tagpilot: { view: "/views/tagpilot.html", init: screen => window.initTagpilot && window.initTagpilot(screen) },
  trainpilot: { view: "/views/trainpilot.html", init: screen => window.initTrainpilot && window.initTrainpilot(screen), stop: () => window.stopTpLogPoll?.() },
  dpipe: { view: "/views/dpipe.html", init: screen => window.initDpipe && window.initDpipe(screen), stop: () => window.stopDpipeLog?.() },
  docs: { view: "/views/docs.html", init: screen => window.initDocs && window.initDocs(screen) },
  settings: { view: "/views/settings.html?v=20260916a", init: screen => window.initSettings && window.initSettings(screen) },
  support: { view: "/views/support.html", init: screen => window.initSupport && window.initSupport(screen) },
};

const contentEl = document.getElementById("content");
const mainEl = document.querySelector(".main");
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("overlay");
const burger = document.getElementById("burger");
const nav = document.getElementById("nav");
const themeToggle = document.getElementById("theme-toggle");
const logoImg = document.getElementById("logo-img");
const topLogo = document.getElementById("top-logo");
const sidebarCompactToggle = document.getElementById("sidebar-compact-toggle");
const authGate = document.getElementById("auth-gate");
const authPassword = document.getElementById("auth-password");
const authLoginBtn = document.getElementById("auth-login");
const authStatus = document.getElementById("auth-status");

let shutdownNoticeCountdownTimer = null;
let shutdownNoticePollTimer = null;

function closeSidebar() {
  sidebar?.classList.remove("open");
  overlay?.classList.remove("show");
  document.body.classList.remove("navigation-open");
  burger?.setAttribute("aria-expanded", "false");
}

function setTheme(mode) {
  const root = document.documentElement;
  root.setAttribute("data-theme", mode);
  document.querySelectorAll('input[name="settings-theme"]').forEach(input => {
    input.checked = input.value === mode;
  });
  const dark = mode === "dark";
  if (logoImg) logoImg.src = "/logo.svg";
  if (topLogo) topLogo.src = "/logo.svg";
  if (themeToggle) {
    themeToggle.querySelectorAll("[data-theme-choice]").forEach(button => {
      button.setAttribute("aria-pressed", String(button.dataset.themeChoice === mode));
    });
  }
}

function isDesktopLayout() {
  return !window.matchMedia || !window.matchMedia("(max-width: 768px)").matches;
}

function updateSidebarNavTooltips() {
  const links = nav?.querySelectorAll("a");
  if (!links) return;
  const compact = !!sidebar?.classList.contains("compact") && isDesktopLayout();
  links.forEach((link) => {
    const label = link.querySelector(".nav-label")?.textContent?.trim() || "";
    if (!label) {
      link.removeAttribute("title");
      link.removeAttribute("aria-label");
      return;
    }
    if (compact) {
      link.setAttribute("title", label);
      link.setAttribute("aria-label", label);
    } else {
      link.removeAttribute("title");
      link.removeAttribute("aria-label");
    }
  });
}

function setSidebarCompact(compact) {
  if (!sidebar || !isDesktopLayout()) return;
  sidebar.classList.toggle("compact", compact);
  const compactSetting = document.getElementById("settings-sidebar-compact");
  if (compactSetting) compactSetting.checked = compact;
  // Refresh theme toggle label text for compact vs full.
  const mode = document.documentElement.getAttribute("data-theme") || "light";
  setTheme(mode);
  updateSidebarNavTooltips();
  if (sidebarCompactToggle) {
    sidebarCompactToggle.title = compact ? "Expand sidebar" : "Collapse sidebar";
    sidebarCompactToggle.setAttribute("aria-label", sidebarCompactToggle.title);
  }
}

window.applyControlPilotUiSettings = function (settings = {}) {
  if (settings && typeof settings === "object") {
    window.controlPilotSettings = {
      ...(window.controlPilotSettings || {}),
      ...settings,
    };
  }
  const theme = settings && settings.theme === "dark" ? "dark" : "light";
  setTheme(theme);
  if (typeof settings.sidebar_compact === "boolean" && isDesktopLayout()) {
    setSidebarCompact(!!settings.sidebar_compact);
  }
};

window.refreshControlPilotSettings = async function () {
  const settings = await fetchJson("/api/settings");
  window.controlPilotSettings = settings || {};
  window.applyControlPilotUiSettings(window.controlPilotSettings);
  if (typeof window.applyCopilotDrawerDefaults === "function") {
    window.applyCopilotDrawerDefaults(window.controlPilotSettings);
  }
  return window.controlPilotSettings;
};

async function persistUiSettings() {
  try {
    const payload = {
      theme: document.documentElement.getAttribute("data-theme") || "light",
      sidebar_compact: !!sidebar?.classList.contains("compact"),
    };
    const res = await fetchJson("/api/settings/ui", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    window.controlPilotSettings = {
      ...(window.controlPilotSettings || {}),
      ...res,
    };
  } catch (e) {
    // Ignore save failures; UI state already changed locally.
  }
}

async function loadSection(section) {
  if (!controlPilotUnlocked) return;
  if (!contentEl) return;
  if (typeof section !== "string" || !Object.hasOwn(viewMap, section)) section = "dashboard";
  activeScreen?.dispose();
  const screen = window.createScreenLifecycle();
  activeScreen = screen;
  currentSection = section;
  screen.onCleanup(() => viewMap[section].stop?.());
  setCopilotSectionVisibility(section);
  document.querySelectorAll(".nav a").forEach(a => { a.classList.remove("active"); a.removeAttribute("aria-current"); });
  const active = document.querySelector(`.nav a[data-section="${section}"]`);
  if (active) { active.classList.add("active"); active.setAttribute("aria-current", "page"); }
  closeSidebar();
  try {
    if (!viewCache[section]) {
      const html = await screen.text(viewMap[section].view);
      viewCache[section] = html;
    }
  } catch (error) {
    if (screen.active && controlPilotUnlocked) {
      const message = document.createElement("div");
      message.className = "card";
      message.textContent = `Could not load ${section}. Select the page again to retry.`;
      contentEl.replaceChildren(message);
    }
    return;
  }
  if (!screen.active || !controlPilotUnlocked) return;
  contentEl.innerHTML = viewCache[section];
  // run initializer
  currentSection = section;
  history.replaceState(null, "", `#${section}`);
  window.scrollTo(0, 0);
  try {
    await viewMap[section].init(screen);
  } catch (error) {
    if (screen.active) contentEl.textContent = `Could not initialize ${section}: ${error.message || error}`;
    screen.dispose();
    return false;
  }
  if (!screen.active) return;
  // A successful mount is also the completion signal for navigation actions.
  contentEl.querySelectorAll("[data-nav-icon]").forEach(target => {
    const icon = document.querySelector(`.nav [data-section="${target.dataset.navIcon}"] .nav-icon`);
    if (icon) target.replaceChildren(icon.cloneNode(true));
  });
  return screen.active;
}

function setCopilotSectionVisibility(section) {
  const disabled = section === "mediapilot";
  const fab = document.getElementById("copilot-fab");
  const drawer = document.getElementById("copilot-drawer");

  mainEl?.classList.toggle("main--mediapilot", disabled);
  if (fab) {
    fab.hidden = disabled;
    fab.classList.toggle("is-hidden", disabled);
  }
  if (drawer) {
    if (disabled) drawer.classList.remove("open");
    drawer.hidden = disabled;
    drawer.classList.toggle("is-hidden", disabled);
  }
}

contentEl?.addEventListener("click", async event => {
  const control = event.target.closest("[data-open-section]");
  if (!control) return;
  event.preventDefault();
  const mounted = await loadSection(control.dataset.openSection);
  if (mounted && control.dataset.openUpload !== undefined) window.openUploadModal?.();
});

// expose for other modules
window.loadSection = loadSection;

function setAuthGateVisible(visible, message = "") {
  if (!authGate) return;
  authGate.classList.toggle("show", visible);
  authGate.setAttribute("aria-hidden", visible ? "false" : "true");
  if (authStatus) authStatus.textContent = message || "";
  if (visible) {
    authPassword?.focus();
  } else if (authPassword) {
    authPassword.value = "";
  }
}

window.showControlPilotLogin = function (message = "ControlPilot password required") {
  controlPilotUnlocked = false;
  activeScreen?.dispose();
  window.workspaceStatus.stop();
  setAuthGateVisible(true, message);
};

async function initControlPilotAuth() {
  try {
    const status = await fetchJson("/api/settings/auth/status");
    const enabled = !!(status && status.enabled);
    const authenticated = !!(status && status.authenticated);
    controlPilotUnlocked = !enabled || authenticated;
    setAuthGateVisible(enabled && !authenticated);
    return controlPilotUnlocked;
  } catch (e) {
    controlPilotUnlocked = true;
    setAuthGateVisible(false);
    return true;
  }
}

function formatHMS(totalSeconds) {
  const s = Math.max(0, totalSeconds | 0);
  const hours = Math.floor(s / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  const hh = String(Math.min(99, hours)).padStart(2, "0");
  const mm = String(minutes).padStart(2, "0");
  const ss = String(secs).padStart(2, "0");
  return `${hh}:${mm}:${ss}`;
}

function setShutdownNoticeVisible(visible) {
  const wrap = document.getElementById("shutdown-notice");
  if (!wrap) return;
  wrap.style.display = visible ? "flex" : "none";
}

function setShutdownNoticeTime(secondsRemaining) {
  const el = document.getElementById("shutdown-notice-time");
  if (!el) return;
  el.textContent = formatHMS(secondsRemaining);
}

function stopShutdownNoticeCountdown() {
  if (shutdownNoticeCountdownTimer) clearInterval(shutdownNoticeCountdownTimer);
  shutdownNoticeCountdownTimer = null;
}

function startShutdownNoticeCountdown(initialSeconds) {
  stopShutdownNoticeCountdown();
  const start = Date.now();
  const initial = Math.max(0, initialSeconds | 0);
  setShutdownNoticeTime(initial);
  shutdownNoticeCountdownTimer = setInterval(() => {
    const elapsed = Math.floor((Date.now() - start) / 1000);
    const remaining = Math.max(0, initial - elapsed);
    setShutdownNoticeTime(remaining);
    if (remaining <= 0) stopShutdownNoticeCountdown();
  }, 1000);
}

async function cancelShutdownFromNotice() {
  try {
    await fetchJson("/api/shutdown/cancel", { method: "POST" });
    // UI will refresh on next poll, but hide immediately for responsiveness.
    setShutdownNoticeVisible(false);
    stopShutdownNoticeCountdown();
  } catch (e) {
    alert(`Failed to cancel shutdown: ${e.message || e}`);
  }
}

async function initShutdownNotice() {
  const wrap = document.getElementById("shutdown-notice");
  const btnCancel = document.getElementById("shutdown-notice-cancel");
  const btnView = document.getElementById("shutdown-notice-view");
  if (!wrap || !btnCancel || !btnView) return;

  if (!btnCancel.dataset.bound) {
    btnCancel.dataset.bound = "1";
    btnCancel.addEventListener("click", () => {
      if (!confirm(btnCancel.dataset.failed === "true" ? "Dismiss the shutdown error?" : "Cancel the scheduled shutdown?")) return;
      cancelShutdownFromNotice();
    });
  }

  if (!btnView.dataset.bound) {
    btnView.dataset.bound = "1";
    btnView.addEventListener("click", () => {
      if (window.loadSection) window.loadSection("dashboard");
    });
  }

  const poll = async () => {
    try {
      const st = await fetchJson("/api/shutdown/status");
      const failed = !!(st && st.error);
      const label = wrap.querySelector(".label");
      if (label) label.textContent = failed ? "Shutdown failed" : "Shutdown in";
      const timeEl = document.getElementById("shutdown-notice-time");
      if (timeEl) timeEl.hidden = failed;
      btnCancel.textContent = failed ? "Dismiss" : "Cancel";
      btnCancel.dataset.failed = String(failed);
      if (failed) {
        setShutdownNoticeVisible(true);
        stopShutdownNoticeCountdown();
      } else if (st && st.scheduled) {
        setShutdownNoticeVisible(true);
        const seconds = st.time_remaining || 0;
        startShutdownNoticeCountdown(seconds);
      } else {
        setShutdownNoticeVisible(false);
        stopShutdownNoticeCountdown();
      }
    } catch (e) {
      // Ignore transient errors; keep last known UI.
    }
  };

  // Avoid duplicate poll loops.
  if (shutdownNoticePollTimer) clearInterval(shutdownNoticePollTimer);
  await poll();
  shutdownNoticePollTimer = setInterval(poll, 10_000);
}

// Event wiring
if (burger) {
  burger.addEventListener("click", () => {
    sidebar?.classList.toggle("open");
    overlay?.classList.toggle("show");
    const open = !!sidebar?.classList.contains("open");
    document.body.classList.toggle("navigation-open", open);
    burger.setAttribute("aria-expanded", String(open));
  });
}
if (overlay) overlay.addEventListener("click", closeSidebar);
if (nav) {
  nav.querySelectorAll("a").forEach(a => {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      const target = a.dataset.section;
      if (target) loadSection(target);
    });
  });
}
if (themeToggle) {
  themeToggle.addEventListener("click", event => {
    const choice = event.target.closest("[data-theme-choice]");
    if (!choice) return;
    setTheme(choice.dataset.themeChoice);
    persistUiSettings();
  });
}
if (sidebarCompactToggle) {
  sidebarCompactToggle.addEventListener("click", () => {
    const compact = sidebar?.classList.contains("compact");
    setSidebarCompact(!compact);
    persistUiSettings();
  });
}
if (authLoginBtn && !authLoginBtn.dataset.bound) {
  authLoginBtn.dataset.bound = "1";
  authLoginBtn.addEventListener("click", async () => {
    const password = authPassword?.value || "";
    if (!password.trim()) {
      if (authStatus) authStatus.textContent = "Enter the password.";
      authPassword?.focus();
      return;
    }
    authLoginBtn.disabled = true;
    if (authStatus) authStatus.textContent = "Unlocking...";
    try {
      await fetchJson("/api/settings/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      await window.refreshControlPilotSettings();
      controlPilotUnlocked = true;
      setAuthGateVisible(false);
      window.workspaceStatus.start();
      initShutdownNotice();
      loadSection(currentSection || initialSection);
    } catch (e) {
      if (authStatus) authStatus.textContent = e.message || String(e);
    } finally {
      authLoginBtn.disabled = false;
    }
  });
}
if (authPassword && !authPassword.dataset.bound) {
  authPassword.dataset.bound = "1";
  authPassword.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      authLoginBtn?.click();
    }
  });
}
window.addEventListener("resize", updateSidebarNavTooltips);

// Init theme & default section
(async function init() {
  setTheme("light");
  updateSidebarNavTooltips();
  const unlocked = await initControlPilotAuth();
  if (!unlocked) return;
  await window.refreshControlPilotSettings();
  window.workspaceStatus.start();
  initShutdownNotice();
  loadSection(initialSection);
})();
