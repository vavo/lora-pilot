function normalizePathname(pathname) {
  const raw = typeof pathname === "string" && pathname ? pathname : "/";
  const noIndex = raw.endsWith("/index.html")
    ? raw.slice(0, -"/index.html".length)
    : raw;
  if (noIndex === "/") return "";
  return noIndex.endsWith("/") ? noIndex.slice(0, -1) : noIndex;
}

const APP_BASE_PATH = normalizePathname(window.location.pathname);

export function appBasePath() {
  return APP_BASE_PATH;
}

export function appUrl(path = "") {
  const value = String(path || "");
  if (!value) return APP_BASE_PATH || "/";
  if (/^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(value)) return value;
  const rel = value.replace(/^\/+/, "");
  return `${APP_BASE_PATH}/${rel}`;
}

