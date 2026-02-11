const sections = ["dashboard", "services", "models", "datasets", "mediapilot", "comfyui", "tagpilot", "trainpilot", "dpipe", "copilot", "docs", "support"];
const viewCache = {};
let currentSection = null;
const viewMap = {
  dashboard: { view: "/views/dashboard.html", init: () => window.initDashboard && window.initDashboard() },
  services: { view: "/views/services.html", init: () => window.initServices && window.initServices() },
  models: { view: "/views/models.html", init: () => window.initModels && window.initModels() },
  datasets: { view: "/views/datasets.html", init: () => window.initDatasets && window.initDatasets() },
  mediapilot: { view: "/views/mediapilot.html", init: () => window.initMediapilot && window.initMediapilot() },
  comfyui: { view: "/views/comfyui.html", init: () => window.initComfyUI && window.initComfyUI() },
  tagpilot: { view: "/views/tagpilot.html", init: () => window.initTagpilot && window.initTagpilot() },
  trainpilot: { view: "/views/trainpilot.html", init: () => window.initTrainpilot && window.initTrainpilot() },
  dpipe: { view: "/views/dpipe.html", init: () => window.initDpipe && window.initDpipe() },
  copilot: { view: "/views/copilot.html", init: () => window.initCopilot && window.initCopilot() },
  docs: { view: "/views/docs.html", init: () => window.initDocs && window.initDocs() },
  support: { view: "/views/support.html", init: () => window.initSupport && window.initSupport() },
};

const contentEl = document.getElementById("content");
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("overlay");
const burger = document.getElementById("burger");
const nav = document.getElementById("nav");
const themeToggle = document.getElementById("theme-toggle");
const logoImg = document.getElementById("logo-img");
const topLogo = document.getElementById("top-logo");
const sidebarCompactToggle = document.getElementById("sidebar-compact-toggle");

let shutdownNoticeCountdownTimer = null;
let shutdownNoticePollTimer = null;

function closeSidebar() {
  sidebar?.classList.remove("open");
  overlay?.classList.remove("show");
}

function setTheme(mode) {
  const root = document.documentElement;
  root.setAttribute("data-theme", mode);
  localStorage.setItem("theme", mode);
  const dark = mode === "dark";
  if (logoImg) logoImg.src = "/logo.svg";
  if (topLogo) topLogo.src = "/logo.svg";
  if (themeToggle) {
    const compact = sidebar?.classList.contains("compact");
    themeToggle.textContent = compact ? (dark ? "☀️" : "🌙") : (dark ? "☀️ Light mode" : "🌙 Dark mode");
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
  localStorage.setItem("sidebarCompact", compact ? "1" : "0");
  // Refresh theme toggle label text for compact vs full.
  const mode = document.documentElement.getAttribute("data-theme") || "light";
  setTheme(mode);
  updateSidebarNavTooltips();
  if (sidebarCompactToggle) {
    sidebarCompactToggle.title = compact ? "Expand sidebar" : "Collapse sidebar";
    sidebarCompactToggle.setAttribute("aria-label", sidebarCompactToggle.title);
  }
}

async function loadSection(section) {
  if (!contentEl) return;
  if (!viewMap[section]) section = "dashboard";
  // cleanup timers when switching away
  if (currentSection && currentSection !== section) {
    if (currentSection === "dashboard" && window.stopDashboard) window.stopDashboard();
    if (currentSection === "dpipe" && window.stopDpipeLog) window.stopDpipeLog();
    if (currentSection === "trainpilot" && window.stopTpLogPoll) window.stopTpLogPoll();
    if (currentSection === "comfyui" && window.stopComfyUI) window.stopComfyUI();
  }
  document.querySelectorAll(".nav a").forEach(a => a.classList.remove("active"));
  const active = document.querySelector(`.nav a[data-section="${section}"]`);
  if (active) active.classList.add("active");
  closeSidebar();
  if (!viewCache[section]) {
    const res = await fetch(viewMap[section].view);
    if (!res.ok) {
      contentEl.innerHTML = `<div class="card">Failed to load view: ${section}</div>`;
      return;
    }
    viewCache[section] = await res.text();
  }
  contentEl.innerHTML = viewCache[section];
  // run initializer
  viewMap[section].init();
  currentSection = section;
}
// expose for other modules
window.loadSection = loadSection;

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
      if (!confirm("Cancel the scheduled shutdown?")) return;
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
      if (st && st.scheduled) {
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
  themeToggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    setTheme(current === "dark" ? "light" : "dark");
  });
}
if (sidebarCompactToggle) {
  sidebarCompactToggle.addEventListener("click", () => {
    const compact = sidebar?.classList.contains("compact");
    setSidebarCompact(!compact);
  });
}
window.addEventListener("resize", updateSidebarNavTooltips);

// Init theme & default section
(function init() {
  // Desktop-only: restore compact state.
  const compactSaved = localStorage.getItem("sidebarCompact");
  if (compactSaved === "1") {
    setSidebarCompact(true);
  }
  const saved = localStorage.getItem("theme");
  setTheme(saved === "dark" ? "dark" : "light");
  updateSidebarNavTooltips();
  initShutdownNotice();
  loadSection("dashboard");
})();
