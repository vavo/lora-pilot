// Cache-busting query for module imports to avoid stale browser caches.
import { loadFolders, loadImages, resetGallery, ensureTagsLoaded } from "./gallery.js?v=cb23";

console.log("MAIN JS LOADED");

const TOAST_DURATION = 3500;
const THEME_KEY = "theme";

function normalizeTheme(value) {
  return value === "dark" ? "dark" : "light";
}

function getThemeFromQuery() {
  try {
    const p = new URLSearchParams(window.location.search);
    const theme = p.get("theme");
    if (theme === "dark" || theme === "light") return theme;
  } catch (_) {}
  return null;
}

function getThemeFromParent() {
  try {
    if (window.parent && window.parent !== window) {
      const parentTheme = window.parent.document?.documentElement?.getAttribute("data-theme");
      if (parentTheme === "dark" || parentTheme === "light") return parentTheme;
    }
  } catch (_) {}
  return null;
}

function getThemeFromStorage() {
  try {
    return normalizeTheme(localStorage.getItem(THEME_KEY) || "light");
  } catch (_) {
    return "light";
  }
}

function applyTheme(theme) {
  const normalized = normalizeTheme(theme);
  document.documentElement.setAttribute("data-theme", normalized);
}

function initThemeSync() {
  const initialTheme =
    getThemeFromQuery() ||
    getThemeFromParent() ||
    getThemeFromStorage();
  applyTheme(initialTheme);

  try {
    if (window.parent && window.parent !== window) {
      const parentRoot = window.parent.document?.documentElement;
      if (parentRoot) {
        const observer = new MutationObserver(() => {
          const next = parentRoot.getAttribute("data-theme");
          if (next === "dark" || next === "light") applyTheme(next);
        });
        observer.observe(parentRoot, { attributes: true, attributeFilter: ["data-theme"] });
      }
    }
  } catch (_) {}

  window.addEventListener("storage", (event) => {
    if (event.key === THEME_KEY) {
      applyTheme(normalizeTheme(event.newValue || "light"));
    }
  });
}

initThemeSync();

function ensureToastContainer() {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  return container;
}

function showToast(message, type = "error") {
  if (!message) return;
  const container = ensureToastContainer();
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
    if (!container.children.length) container.remove();
  }, TOAST_DURATION);
}

window.showToast = showToast;

window.addEventListener("unhandledrejection", (event) => {
  console.error("Unhandled rejection:", event.reason);
  window.showToast?.("Something went wrong. Please try again.");
});

window.addEventListener("error", (event) => {
  console.error("Global error:", {
    message: event.message,
    source: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    error: event.error,
  });
  window.showToast?.("Something went wrong. Please try again.");
  event.preventDefault(); // Suppress default browser error handling
});

const progressBar = document.getElementById("loading-progress-bar");
const loadingScreen = document.getElementById("loading-screen");
const authPanel = document.getElementById("auth-panel");
const authInput = document.getElementById("auth-password");
const authSubmit = document.getElementById("auth-submit");
const authError = document.getElementById("auth-error");
const PROGRESS_STEPS = {
  start: 10,
  folders: 60,
  images: 100,
};

function setProgress(val) {
  if (progressBar) progressBar.style.width = `${val}%`;
}

function showLoadingScreen() {
  if (loadingScreen) loadingScreen.classList.remove("hidden");
}

function hideLoadingScreen() {
  if (loadingScreen) loadingScreen.classList.add("hidden");
}

function setAuthError(message) {
  if (authError) authError.textContent = message || "";
}

async function fetchAuthStatus() {
  const res = await fetch("./auth/status");
  if (!res.ok) throw new Error(`Failed to fetch auth status: ${res.status}`);
  return res.json();
}

async function login(password) {
  const res = await fetch("./auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (res.status === 401) return false;
  if (!res.ok) throw new Error(`Failed to login: ${res.status}`);
  return true;
}

async function init() {
  setProgress(PROGRESS_STEPS.start);
  resetGallery(); // Ensure gallery is clean before starting
  try {
    await loadFolders();
    setProgress(PROGRESS_STEPS.folders);
    // Now we explicitly call loadImages from here, after folders are loaded.
    await loadImages(1, false);
    setProgress(PROGRESS_STEPS.images);
    await ensureTagsLoaded();
  } catch (error) {
    console.error("Error initializing app:", error);
    window.showToast?.("Failed to initialize.");
  } finally {
    setTimeout(() => {
      hideLoadingScreen();
    }, 150);
  }
}

const start = async () => {
  showLoadingScreen();
  setProgress(0);

  let authEnabled = false;
  let authenticated = false;
  try {
    const status = await fetchAuthStatus();
    authEnabled = !!status?.enabled;
    authenticated = !!status?.authenticated;
  } catch (error) {
    console.error("Failed to check auth status:", error);
    window.showToast?.("Failed to check auth.");
    hideLoadingScreen();
    return;
  }

  if (!authEnabled) {
    if (authPanel) authPanel.classList.add("hidden");
    void init();
    return;
  }

  if (authenticated) {
    if (authPanel) authPanel.classList.add("hidden");
    void init();
    return;
  }

  if (!authPanel || !authInput || !authSubmit) {
    window.showToast?.("Auth is enabled but unlock UI is missing.");
    hideLoadingScreen();
    return;
  }

  authPanel.classList.remove("hidden");

  const attemptUnlock = async () => {
    const value = authInput.value || "";
    if (!value.trim()) {
      setAuthError("Enter password.");
      authInput.focus();
      return;
    }

    authSubmit.disabled = true;
    try {
      const ok = await login(value);
      if (!ok) {
        setAuthError("Incorrect password.");
        authInput.focus();
        authInput.select();
        return;
      }
      setAuthError("");
      authInput.disabled = true;
      authPanel.classList.add("hidden");
      void init();
      return;
    } catch (error) {
      console.error("Login failed:", error);
      setAuthError("Login failed.");
    } finally {
      authSubmit.disabled = false;
    }
  };

  authSubmit.onclick = async (e) => {
    e.preventDefault();
    await attemptUnlock();
  };
  authInput.addEventListener("keydown", async (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      await attemptUnlock();
    }
  });
  authInput.focus();
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", start);
} else {
  start();
}
