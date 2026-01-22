window.initDocs = async function () {
  const status = document.getElementById("docs-status");
  const content = document.getElementById("docs-content");
  const tabReadme = document.getElementById("docs-tab-readme");
  const tabChangelog = document.getElementById("docs-tab-changelog");
  if (!status || !content) return;
  if (tabReadme && tabChangelog) {
    tabReadme.onclick = () => loadDocsTab("readme");
    tabChangelog.onclick = () => loadDocsTab("changelog");
  }
  await loadDocsTab("readme");
};

async function loadDocsTab(kind) {
  const status = document.getElementById("docs-status");
  const content = document.getElementById("docs-content");
  const tabReadme = document.getElementById("docs-tab-readme");
  const tabChangelog = document.getElementById("docs-tab-changelog");
  if (!status || !content) return;
  const isReadme = kind !== "changelog";
  if (tabReadme) tabReadme.classList.toggle("active", isReadme);
  if (tabChangelog) tabChangelog.classList.toggle("active", !isReadme);
  status.textContent = isReadme ? "Loading README..." : "Loading changelog...";
  content.style.display = "none";
  try {
    const url = isReadme ? "/api/docs" : "/api/changelog";
    const data = await fetchJson(url);
    const raw = data.content || "No docs found.";
    content.innerHTML = renderMarkdown(raw);
    status.textContent = "";
    content.style.display = "";
  } catch (e) {
    status.textContent = `Error: ${e.message || e}`;
  }
}

function renderMarkdown(md) {
  const parts = String(md || "").split("```");
  let html = "";
  for (let i = 0; i < parts.length; i += 1) {
    if (i % 2 === 0) {
      html += renderMarkdownBlock(parts[i]);
    } else {
      html += renderCodeBlock(parts[i]);
    }
  }
  return html;
}

function renderCodeBlock(raw) {
  let content = raw || "";
  if (content.startsWith("\n")) content = content.slice(1);
  let lang = "";
  const firstNewline = content.indexOf("\n");
  if (firstNewline !== -1) {
    const firstLine = content.slice(0, firstNewline).trim();
    if (firstLine && /^[a-z0-9_-]+$/i.test(firstLine)) {
      lang = firstLine;
      content = content.slice(firstNewline + 1);
    }
  }
  const safe = escapeHtml(content);
  const klass = lang ? ` class="language-${lang}"` : "";
  return `<pre><code${klass}>${safe}</code></pre>`;
}

function renderMarkdownBlock(raw) {
  const lines = String(raw || "").split("\n");
  let html = "";
  let inList = false;
  let listType = "";
  let inPara = false;

  const closePara = () => {
    if (inPara) {
      html += "</p>";
      inPara = false;
    }
  };
  const closeList = () => {
    if (inList) {
      html += `</${listType}>`;
      inList = false;
      listType = "";
    }
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      closePara();
      closeList();
      continue;
    }
    if (/^#{1,6}\s+/.test(trimmed)) {
      closePara();
      closeList();
      const level = trimmed.match(/^#{1,6}/)[0].length;
      const text = trimmed.replace(/^#{1,6}\s+/, "");
      html += `<h${level}>${renderInline(text)}</h${level}>`;
      continue;
    }
    if (/^---+$/.test(trimmed)) {
      closePara();
      closeList();
      html += "<hr>";
      continue;
    }
    const ulMatch = trimmed.match(/^[-*]\s+(.+)/);
    const olMatch = trimmed.match(/^\d+\.\s+(.+)/);
    if (ulMatch || olMatch) {
      const type = olMatch ? "ol" : "ul";
      const itemText = (olMatch ? olMatch[1] : ulMatch[1]) || "";
      if (!inList || listType !== type) {
        closePara();
        closeList();
        inList = true;
        listType = type;
        html += `<${type}>`;
      }
      html += `<li>${renderInline(itemText)}</li>`;
      continue;
    }
    if (!inPara) {
      closeList();
      html += "<p>";
      inPara = true;
    } else {
      html += "<br>";
    }
    html += renderInline(trimmed);
  }
  closePara();
  closeList();
  return html;
}

function renderInline(text) {
  const escaped = escapeHtml(text);
  const parts = escaped.split("`");
  return parts
    .map((part, idx) => {
      if (idx % 2 === 1) {
        return `<code>${part}</code>`;
      }
      let out = part;
      out = out.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (m, alt, url) => {
        const safe = safeUrl(url);
        if (!safe) return m;
        return `<img alt="${alt}" src="${safe}">`;
      });
      out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (m, label, url) => {
        const safe = safeUrl(url);
        if (!safe) return label;
        const target = safe.startsWith("http") ? ' target="_blank" rel="noopener"' : "";
        return `<a href="${safe}"${target}>${label}</a>`;
      });
      return out;
    })
    .join("");
}

function safeUrl(raw) {
  const url = (raw || "").trim();
  if (!url) return "";
  if (/^(https?:\/\/|\/|#|mailto:)/i.test(url)) {
    return url;
  }
  return "";
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
