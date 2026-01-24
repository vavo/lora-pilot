const sections = ["dashboard", "services", "models", "datasets", "comfyui", "tagpilot", "trainpilot", "dpipe", "copilot", "docs", "support"];
const viewCache = {};
let currentSection = null;
const viewMap = {
  dashboard: { view: "/views/dashboard.html", init: () => window.initDashboard && window.initDashboard() },
  services: { view: "/views/services.html", init: () => window.initServices && window.initServices() },
  models: { view: "/views/models.html", init: () => window.initModels && window.initModels() },
  datasets: { view: "/views/datasets.html", init: () => window.initDatasets && window.initDatasets() },
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

function closeSidebar() {
  sidebar?.classList.remove("open");
  overlay?.classList.remove("show");
}

function setTheme(mode) {
  const root = document.documentElement;
  root.setAttribute("data-theme", mode);
  localStorage.setItem("theme", mode);
  const dark = mode === "dark";
  if (logoImg) logoImg.src = dark ? "/logodark.svg" : "/logo.svg";
  if (topLogo) topLogo.src = dark ? "/logodark.svg" : "/logo.svg";
  if (themeToggle) themeToggle.textContent = dark ? "☀️ Light mode" : "🌙 Dark mode";
}

async function loadSection(section) {
  if (!contentEl) return;
  if (!viewMap[section]) section = "dashboard";
  // cleanup timers when switching away
  if (currentSection && currentSection !== section) {
    if (currentSection === "dpipe" && window.stopDpipeLog) window.stopDpipeLog();
    if (currentSection === "trainpilot" && window.stopTpLogPoll) window.stopTpLogPoll();
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

// Init theme & default section
(function init() {
  const saved = localStorage.getItem("theme");
  setTheme(saved === "dark" ? "dark" : "light");
  loadSection("dashboard");
})();
