const DOC_TAB_CONFIG = {
  readme: {
    url: "/api/docs",
    loading: "Loading README...",
    defaultSource: "README.md",
  },
  documentation: {
    url: "/api/docs/sitemap",
    loading: "Loading documentation sitemap...",
    defaultSource: "docs/README.md",
  },
  changelog: {
    url: "/api/changelog",
    loading: "Loading changelog...",
    defaultSource: "CHANGELOG",
  },
};

const ALLOWED_TAGS = new Set([
  "a",
  "blockquote",
  "br",
  "code",
  "del",
  "em",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "hr",
  "img",
  "input",
  "li",
  "ol",
  "p",
  "pre",
  "strong",
  "sub",
  "sup",
  "table",
  "tbody",
  "td",
  "th",
  "thead",
  "tr",
  "ul",
]);

const DROP_CONTENT_TAGS = new Set([
  "script",
  "style",
  "iframe",
  "object",
  "embed",
  "link",
  "meta",
]);

const ALLOWED_ATTRS = {
  a: new Set(["href", "title"]),
  img: new Set(["src", "alt", "title"]),
  code: new Set(["class"]),
  pre: new Set(["class"]),
  th: new Set(["align"]),
  td: new Set(["align"]),
  input: new Set(["type", "checked", "disabled"]),
};

let currentDocSource = "";

window.initDocs = async function () {
  const nodes = getDocsNodes();
  if (!nodes) return;
  const { content, tabReadme, tabDocumentation, tabChangelog } = nodes;

  tabReadme.onclick = () => loadDocsTab("readme");
  tabDocumentation.onclick = () => loadDocsTab("documentation");
  tabChangelog.onclick = () => loadDocsTab("changelog");

  if (!content.dataset.docsClickBound) {
    content.addEventListener("click", onDocsContentClick);
    content.dataset.docsClickBound = "1";
  }

  await loadDocsTab("readme");
};

function getDocsNodes() {
  const status = document.getElementById("docs-status");
  const content = document.getElementById("docs-content");
  const tabReadme = document.getElementById("docs-tab-readme");
  const tabDocumentation = document.getElementById("docs-tab-documentation");
  const tabChangelog = document.getElementById("docs-tab-changelog");
  if (!status || !content || !tabReadme || !tabDocumentation || !tabChangelog) {
    return null;
  }
  return { status, content, tabReadme, tabDocumentation, tabChangelog };
}

function normalizeDocsTab(kind) {
  if (kind === "documentation" || kind === "changelog") return kind;
  return "readme";
}

async function loadDocsTab(kind) {
  const nodes = getDocsNodes();
  if (!nodes) return;
  const { status, content, tabReadme, tabDocumentation, tabChangelog } = nodes;
  const tab = normalizeDocsTab(kind);
  const tabConfig = DOC_TAB_CONFIG[tab];

  tabReadme.classList.toggle("active", tab === "readme");
  tabDocumentation.classList.toggle("active", tab === "documentation");
  tabChangelog.classList.toggle("active", tab === "changelog");

  status.textContent = tabConfig.loading;
  content.classList.add("is-hidden");

  try {
    const data = await fetchJson(tabConfig.url);
    const raw = data.content || "No docs found.";
    const source = data.source || tabConfig.defaultSource;
    renderDocIntoContent(content, raw, source);
    status.textContent = "";
    content.classList.remove("is-hidden");
  } catch (error) {
    status.textContent = `Error: ${error.message || error}`;
  }
}

async function loadDocsPath(path, fragment = "") {
  const nodes = getDocsNodes();
  if (!nodes) return;
  const { status, content, tabReadme, tabDocumentation, tabChangelog } = nodes;

  tabReadme.classList.remove("active");
  tabDocumentation.classList.add("active");
  tabChangelog.classList.remove("active");

  status.textContent = `Loading ${path}...`;
  content.classList.add("is-hidden");

  try {
    const apiPath = path.startsWith("docs/") ? path.slice(5) : path;
    const data = await fetchJson(`/api/docs/file?path=${encodeURIComponent(apiPath)}`);
    const raw = data.content || "No docs found.";
    const source = data.source || path;
    renderDocIntoContent(content, raw, source);
    status.textContent = "";
    content.classList.remove("is-hidden");
    if (fragment) {
      requestAnimationFrame(() => applyFragmentNavigation(fragment, content));
    }
  } catch (error) {
    status.textContent = `Error: ${error.message || error}`;
  }
}

function renderDocIntoContent(contentNode, markdown, sourcePath) {
  currentDocSource = sourcePath || "";
  contentNode.innerHTML = renderMarkdown(markdown, currentDocSource);
}

function onDocsContentClick(event) {
  const anchor = event.target?.closest?.("a");
  if (!anchor) return;

  const tab = anchor.getAttribute("data-doc-tab") || "";
  if (tab) {
    event.preventDefault();
    const fragment = anchor.getAttribute("data-doc-fragment") || "";
    void (async () => {
      await loadDocsTab(tab);
      if (fragment) {
        const nodes = getDocsNodes();
        if (nodes) {
          requestAnimationFrame(() => applyFragmentNavigation(fragment, nodes.content));
        }
      }
    })();
    return;
  }

  const docPath = anchor.getAttribute("data-doc-path") || "";
  if (docPath) {
    event.preventDefault();
    const fragment = anchor.getAttribute("data-doc-fragment") || "";
    void loadDocsPath(docPath, fragment);
    return;
  }

  const fragmentOnly = anchor.getAttribute("data-doc-fragment-only") || "";
  if (fragmentOnly) {
    event.preventDefault();
    const nodes = getDocsNodes();
    if (nodes) applyFragmentNavigation(fragmentOnly, nodes.content);
  }
}

function renderMarkdown(markdown, sourcePath) {
  const markedApi = window.marked;
  if (!markedApi || typeof markedApi.parse !== "function") {
    return `<pre><code>${escapeHtml(String(markdown || ""))}</code></pre>`;
  }

  try {
    const parsed = markedApi.parse(String(markdown || ""), {
      async: false,
      breaks: true,
      gfm: true,
    });
    const html = typeof parsed === "string" ? parsed : "";
    return sanitizeAndDecorateHtml(html, sourcePath);
  } catch (error) {
    console.error("Markdown rendering failed:", error);
    return `<pre><code>${escapeHtml(String(markdown || ""))}</code></pre>`;
  }
}

function sanitizeAndDecorateHtml(rawHtml, sourcePath) {
  const parser = new DOMParser();
  const parsedDoc = parser.parseFromString(rawHtml, "text/html");
  const container = document.createElement("div");

  for (const node of Array.from(parsedDoc.body.childNodes)) {
    appendSanitizedNode(container, sanitizeNode(node, sourcePath));
  }

  assignHeadingIds(container);
  return container.innerHTML;
}

function appendSanitizedNode(parent, node) {
  if (!node) return;
  parent.appendChild(node);
}

function sanitizeNode(node, sourcePath) {
  if (node.nodeType === Node.TEXT_NODE) {
    return document.createTextNode(node.textContent || "");
  }

  if (node.nodeType !== Node.ELEMENT_NODE) {
    return null;
  }

  const tag = node.tagName.toLowerCase();
  if (DROP_CONTENT_TAGS.has(tag)) {
    return null;
  }

  if (!ALLOWED_TAGS.has(tag)) {
    const fragment = document.createDocumentFragment();
    for (const child of Array.from(node.childNodes)) {
      appendSanitizedNode(fragment, sanitizeNode(child, sourcePath));
    }
    return fragment;
  }

  const safeEl = document.createElement(tag);
  applyAllowedAttributes(node, safeEl, tag, sourcePath);

  for (const child of Array.from(node.childNodes)) {
    appendSanitizedNode(safeEl, sanitizeNode(child, sourcePath));
  }

  if (tag === "input") {
    const inputType = (safeEl.getAttribute("type") || "").toLowerCase();
    if (inputType !== "checkbox") {
      return null;
    }
    safeEl.setAttribute("disabled", "");
  }

  return safeEl;
}

function applyAllowedAttributes(sourceEl, targetEl, tag, sourcePath) {
  const allowedForTag = ALLOWED_ATTRS[tag] || new Set();
  for (const attr of Array.from(sourceEl.attributes)) {
    const name = attr.name.toLowerCase();
    const value = attr.value || "";
    if (!allowedForTag.has(name)) continue;

    if (name === "href") {
      const link = sanitizeLinkReference(value, sourcePath);
      if (!link) continue;
      if (link.kind === "doc") {
        targetEl.setAttribute("href", "#");
        targetEl.setAttribute("data-doc-path", link.path);
        if (link.fragment) {
          targetEl.setAttribute("data-doc-fragment", link.fragment);
        }
      } else if (link.kind === "tab") {
        targetEl.setAttribute("href", "#");
        targetEl.setAttribute("data-doc-tab", link.tab);
        if (link.fragment) {
          targetEl.setAttribute("data-doc-fragment", link.fragment);
        }
      } else if (link.kind === "anchor") {
        const fragmentHref = link.fragment ? `#${link.fragment}` : "#";
        targetEl.setAttribute("href", fragmentHref);
        if (link.fragment) {
          targetEl.setAttribute("data-doc-fragment-only", link.fragment);
        }
      } else {
        targetEl.setAttribute("href", link.href);
        if (link.kind === "external") {
          targetEl.setAttribute("target", "_blank");
          targetEl.setAttribute("rel", "noopener noreferrer");
        }
      }
      continue;
    }

    if (name === "src") {
      const safeSrc = sanitizeImageReference(value);
      if (!safeSrc) continue;
      targetEl.setAttribute("src", safeSrc);
      continue;
    }

    if (name === "class") {
      const safeClass = sanitizeClassValue(value);
      if (!safeClass) continue;
      targetEl.setAttribute("class", safeClass);
      continue;
    }

    if (name === "checked" || name === "disabled") {
      targetEl.setAttribute(name, "");
      continue;
    }

    targetEl.setAttribute(name, value);
  }
}

function sanitizeClassValue(rawValue) {
  return String(rawValue || "")
    .split(/\s+/)
    .filter((token) => token && /^(language-[a-z0-9_-]+|task-list-item|contains-task-list)$/i.test(token))
    .join(" ");
}

function sanitizeLinkReference(rawHref, sourcePath) {
  const href = String(rawHref || "").trim();
  if (!href) return null;
  if (/[\u0000-\u001F\u007F]/.test(href)) return null;
  if (href.startsWith("#")) return { kind: "anchor", fragment: href.slice(1) };
  if (/^\/\//.test(href)) return { kind: "external", href };

  const schemeMatch = href.match(/^([a-zA-Z][a-zA-Z\d+\-.]*):/);
  if (schemeMatch) {
    const scheme = schemeMatch[1].toLowerCase();
    if (scheme === "http" || scheme === "https" || scheme === "mailto") {
      return { kind: scheme === "mailto" ? "relative" : "external", href };
    }
    return null;
  }

  const { path, fragment } = splitPathAndFragment(href);
  if (isChangelogLinkPath(path)) {
    return { kind: "tab", tab: "changelog", fragment };
  }
  const lowerPath = path.toLowerCase();
  const inDocsContext = (sourcePath || "").startsWith("docs/");
  const looksLikeDocsPath = path.startsWith("docs/") || path.startsWith("/docs/");
  if (lowerPath.endsWith(".md") && (inDocsContext || looksLikeDocsPath)) {
    const resolved = resolveDocPath(sourcePath, path);
    if (!resolved) return null;
    return { kind: "doc", path: resolved, fragment };
  }

  return { kind: "relative", href };
}

function normalizeSimplePath(rawPath) {
  return String(rawPath || "")
    .trim()
    .replace(/\\/g, "/")
    .replace(/^\.\/+/, "")
    .replace(/^\/+/, "");
}

function isChangelogLinkPath(rawPath) {
  const path = normalizeSimplePath(rawPath).toLowerCase();
  return path === "changelog" || path === "changelog.md";
}

function sanitizeImageReference(rawSrc) {
  const src = String(rawSrc || "").trim();
  if (!src) return "";
  if (/[\u0000-\u001F\u007F]/.test(src)) return "";
  if (/^\/\//.test(src)) return src;
  const schemeMatch = src.match(/^([a-zA-Z][a-zA-Z\d+\-.]*):/);
  if (schemeMatch) {
    const scheme = schemeMatch[1].toLowerCase();
    if (scheme === "http" || scheme === "https") return src;
    return "";
  }
  return src;
}

function splitPathAndFragment(href) {
  const idx = href.indexOf("#");
  if (idx === -1) {
    return { path: href, fragment: "" };
  }
  return {
    path: href.slice(0, idx),
    fragment: href.slice(idx + 1),
  };
}

function resolveDocPath(sourcePath, targetPath) {
  let path = String(targetPath || "").trim().replace(/\\/g, "/");
  if (!path) return "";

  const inDocsContext = (sourcePath || "").startsWith("docs/");
  if (path.startsWith("/")) {
    path = path.slice(1);
  }

  let combined = path;
  if (!combined.startsWith("docs/") && inDocsContext) {
    const sourceDir = sourcePath.includes("/") ? sourcePath.slice(0, sourcePath.lastIndexOf("/") + 1) : "";
    combined = `${sourceDir}${combined}`;
  }

  let normalized = normalizeDocPath(combined);
  if (!normalized || !normalized.toLowerCase().endsWith(".md")) {
    return "";
  }
  if (!normalized.startsWith("docs/")) {
    if (!inDocsContext) return "";
    normalized = normalizeDocPath(`docs/${normalized}`);
  }
  return normalized;
}

function normalizeDocPath(rawPath) {
  const parts = [];
  for (const segment of String(rawPath || "").split("/")) {
    const part = segment.trim();
    if (!part || part === ".") continue;
    if (part === "..") {
      if (parts.length === 0) return "";
      parts.pop();
      continue;
    }
    if (part.includes(":")) return "";
    parts.push(part);
  }
  return parts.join("/");
}

function assignHeadingIds(container) {
  const seen = new Map();
  for (const heading of Array.from(container.querySelectorAll("h1, h2, h3, h4, h5, h6"))) {
    const base = slugifyHeading(heading.textContent || "");
    if (!base) continue;
    const count = seen.get(base) || 0;
    seen.set(base, count + 1);
    heading.id = count === 0 ? base : `${base}-${count + 1}`;
  }
}

function applyFragmentNavigation(fragment, contentNode) {
  const clean = decodeURIComponent(String(fragment || "").replace(/^#/, "").trim());
  if (!clean || !contentNode) return;

  const escaped = cssEscapeValue(clean);
  let target = contentNode.querySelector(`#${escaped}`);
  if (!target) {
    const slug = slugifyHeading(clean);
    if (slug) {
      target = contentNode.querySelector(`#${cssEscapeValue(slug)}`);
    }
  }
  if (!target) return;

  target.scrollIntoView({ behavior: "smooth", block: "start" });
}

function slugifyHeading(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function cssEscapeValue(value) {
  if (window.CSS && typeof window.CSS.escape === "function") {
    return window.CSS.escape(value);
  }
  return String(value).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
