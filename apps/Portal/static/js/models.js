let allModels = [];
let filterCat = "ALL";
let searchText = "";

function getProgressEls(card) {
  const wrap = card.querySelector(".model-progress");
  const bar = card.querySelector(".model-progress-bar");
  const text = card.querySelector(".model-progress-text");
  return { wrap, bar, text };
}

function setProgress(card, pct, label) {
  const { wrap, bar, text } = getProgressEls(card);
  if (!wrap || !bar || !text) return;
  wrap.style.display = "flex";
  if (typeof pct === "number" && isFinite(pct)) {
    const clamped = Math.max(0, Math.min(100, Math.round(pct)));
    bar.classList.remove("indeterminate");
    bar.style.width = `${clamped}%`;
    text.textContent = label || `${clamped}%`;
  } else {
    bar.classList.add("indeterminate");
    bar.style.width = "";
    text.textContent = label || "Downloading…";
  }
}

function clearProgress(card) {
  const { wrap, bar, text } = getProgressEls(card);
  if (!wrap || !bar || !text) return;
  wrap.style.display = "none";
  bar.classList.remove("indeterminate");
  bar.style.width = "0%";
  text.textContent = "";
}

async function syncPullStatusesOnce() {
  try {
    const res = await fetchJson("/api/models/pulls");
    const jobs = (res && res.jobs) ? res.jobs : [];
    const cardsByName = new Map();
    document.querySelectorAll(".model-card").forEach(c => {
      const n = c?.dataset?.modelName;
      if (n) cardsByName.set(n, c);
    });
    jobs.forEach(j => {
      if (!j || j.state !== "running") return;
      const card = cardsByName.get(j.name);
      if (!card) return;
      const pct = (typeof j.progress_pct === "number") ? j.progress_pct : null;
      const label = j.last_line || (pct != null ? `${pct}%` : "Downloading…");
      setProgress(card, pct, label);
      const btn = card.querySelector('button[data-action="install"]');
      if (btn) {
        btn.disabled = true;
        btn.textContent = pct != null ? `Downloading ${pct}%` : "Downloading…";
      }
    });
  } catch (e) {
    // Best-effort; ignore sync errors.
  }
}

window.initModels = async function () {
  const hf = document.getElementById("hf-token");
  if (hf && !hf.dataset.bound) {
    hf.dataset.bound = "1";
  }
  await loadHFTokenStatus();
  const search = document.getElementById("models-search");
  if (search && !search.dataset.bound) {
    search.dataset.bound = "1";
    search.addEventListener("input", () => {
      searchText = search.value.trim().toLowerCase();
      loadModelsTable(false);
    });
  }
  await loadModelsTable(true);
};

window.saveHFToken = async function () {
  const hf = document.getElementById("hf-token");
  const token = hf ? hf.value.trim() : "";
  if (!token) { alert("Enter a token"); return; }
  try {
    await fetchJson("/api/hf-token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    if (hf) {
      hf.value = "";
      hf.placeholder = "HF_TOKEN saved";
    }
    alert("HF_TOKEN saved.");
  } catch (e) {
    alert(`Failed to save token: ${e.message || e}`);
  }
};

window.copyModelPath = async function (path) {
  if (!path) return;
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(path);
    } else {
      const ta = document.createElement("textarea");
      ta.value = path;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    alert("Path copied.");
  } catch (e) {
    alert(`Copy failed: ${e.message || e}`);
  }
};

async function loadHFTokenStatus() {
  const hf = document.getElementById("hf-token");
  if (!hf) return;
  try {
    const res = await fetchJson("/api/hf-token");
    if (res && res.set) {
      hf.placeholder = "HF_TOKEN saved";
    }
  } catch (e) {
    // Ignore; token status is optional UI polish.
  }
}

async function loadModelsTable(forceReload) {
  const status = document.getElementById("status");
  const lists = document.getElementById("models-lists");
  const installedWrap = document.getElementById("models-installed");
  const availableWrap = document.getElementById("models-available");
  const installedCount = document.getElementById("models-installed-count");
  const installedSize = document.getElementById("models-installed-size");
  const availableCount = document.getElementById("models-available-count");
  const summary = document.getElementById("models-summary");
  if (!status || !lists || !installedWrap || !availableWrap) return;
  status.textContent = "Loading models...";
  lists.classList.add("is-hidden");
  installedWrap.innerHTML = "";
  availableWrap.innerHTML = "";
  try {
    if (!allModels.length || forceReload) {
      allModels = await fetchJson("/api/models");
    }
    let data = filterCat === "ALL" ? allModels : allModels.filter(m => m.category === filterCat);
    if (searchText) {
      const q = searchText.toLowerCase();
      data = data.filter(m =>
        (m.name && m.name.toLowerCase().includes(q)) ||
        (m.source && m.source.toLowerCase().includes(q)) ||
        (m.subdir && m.subdir.toLowerCase().includes(q))
      );
    }
    if (!data.length) {
      status.textContent = (searchText || filterCat !== "ALL")
        ? "No models match the current filters."
        : "No models found in manifest.";
      return;
    }
    const installed = data.filter(m => m.installed);
    const available = data.filter(m => !m.installed);
    const installedBytes = installed.reduce((acc, m) => acc + (m.size_bytes || 0), 0);
    if (installedCount) installedCount.textContent = `${installed.length} installed`;
    if (installedSize) installedSize.textContent = installedBytes ? formatBytes(installedBytes) : "0 B";
    if (availableCount) availableCount.textContent = `${available.length} available`;
    if (summary) summary.textContent = `${data.length} models • ${installed.length} installed`;

    installed.forEach(m => {
      installedWrap.appendChild(renderModelCard(m));
    });
    available.forEach(m => {
      availableWrap.appendChild(renderModelCard(m));
    });
    status.textContent = "";
    lists.classList.remove("is-hidden");
    await syncPullStatusesOnce();
  } catch (e) {
    status.textContent = `Error: ${e.message || e}`;
  }
}

function renderModelCard(m) {
  const card = document.createElement("div");
  card.className = "model-card";
  card.dataset.modelName = m.name || "";
  const size = m.size_bytes ? formatBytes(m.size_bytes) : "—";
  const nameCell = m.info_url ? `<a href="${m.info_url}" target="_blank">${m.name}</a>` : m.name;
  const safePath = (m.primary_path || m.target_path || "").replace(/'/g, "\\'");
  const copyIcon = `
    <svg class="model-path-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="9" y="9" width="11" height="11" rx="2" stroke="currentColor" stroke-width="1.6"></rect>
      <rect x="4" y="4" width="11" height="11" rx="2" stroke="currentColor" stroke-width="1.6"></rect>
    </svg>
  `;
  const installBtn = !m.installed
    ? `<button class="btn primary" data-action="install" onclick="pullModel('${m.name}', this)">Install</button>`
    : "";
  const deleteBtn = m.installed
    ? `<button class="btn danger" onclick="deleteModel('${m.name}', this)">Delete</button>`
    : "";
  const src = m.source || "—";
  const target = m.primary_path || m.target_path || "";
  const pathRow = target
    ? (m.installed
      ? `<button class="model-path" type="button" onclick="copyModelPath('${safePath}')"><code>${target}</code>${copyIcon}</button>`
      : `<div class="model-path"><code>${target}</code></div>`)
    : "";
  card.innerHTML = `
    <div class="model-title">
      <div class="model-name">${nameCell}</div>
      <span class="pill">${m.category || "OTHER"}</span>
    </div>
    <div class="model-meta">
      <div>Type: <strong>${m.type || "—"}</strong></div>
      <div>Size: <strong>${size}</strong></div>
      <div>Kind: <strong>${m.kind || "—"}</strong></div>
    </div>
    <div class="model-source" title="${src}">${src}</div>
    ${pathRow}
    <div class="model-actions">
      ${installBtn}
      ${deleteBtn}
    </div>
    <div class="model-progress">
      <div class="model-progress-track"><div class="model-progress-bar"></div></div>
      <div class="model-progress-text"></div>
    </div>
  `;
  return card;
}

window.pullModel = async function (name, btn) {
  const original = btn.textContent;
  const card = btn.closest(".model-card");
  btn.disabled = true;
  btn.textContent = "Starting…";
  try {
    await fetchJson(`/api/models/${encodeURIComponent(name)}/pull/start`, { method: "POST" });
    if (card) setProgress(card, null, "Downloading…");

    while (true) {
      const st = await fetchJson(`/api/models/${encodeURIComponent(name)}/pull/status`);
      if (st && st.state === "running") {
        const pct = (typeof st.progress_pct === "number") ? st.progress_pct : null;
        const label = st.last_line || (pct != null ? `${pct}%` : "Downloading…");
        if (card) setProgress(card, pct, label);
        btn.textContent = pct != null ? `Downloading ${pct}%` : "Downloading…";
        await new Promise(r => setTimeout(r, 1000));
        continue;
      }
      if (st && st.state === "done") {
        if (card) clearProgress(card);
        break;
      }
      if (st && st.state === "error") {
        const msg = st.error || "Unknown error";
        if (card) setProgress(card, null, `Failed: ${msg}`);
        throw new Error(msg);
      }
      // idle or unexpected response
      await new Promise(r => setTimeout(r, 1000));
    }

    await loadModelsTable(true);
  } catch (e) {
    alert(`Pull failed: ${e.message || e}`);
  } finally {
    // If the table re-rendered, this button may no longer exist.
    if (btn && btn.isConnected) {
      btn.disabled = false;
      btn.textContent = original;
    }
  }
};

window.deleteModel = async function (name, btn) {
  if (!confirm(`Delete files for ${name}?`)) return;
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Deleting...";
  try {
    await fetchJson(`/api/models/${encodeURIComponent(name)}/delete`, { method: "POST" });
    await loadModelsTable(true);
  } catch (e) {
    alert(`Delete failed: ${e.message || e}`);
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
};

window.setFilter = function (btn) {
  const cat = btn?.dataset?.cat || "ALL";
  filterCat = cat;
  document.querySelectorAll(".filter button").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  loadModelsTable(false);
};
