let allModels = [];
let filterCat = "ALL";
let searchText = "";

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
  const table = document.getElementById("models-table");
  const tbody = document.getElementById("models-body");
  if (!status || !table || !tbody) return;
  status.textContent = "Loading models...";
  table.style.display = "none";
  tbody.innerHTML = "";
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
      status.textContent = "No models found in manifest.";
      return;
    }
    data.forEach(m => {
      const tr = document.createElement("tr");
      const size = m.size_bytes ? formatBytes(m.size_bytes) : "—";
      const srcDisplay = m.source && m.source.length > 15 ? `${m.source.slice(0,15)}…` : (m.source || "—");
      const nameCell = m.info_url ? `<a href="${m.info_url}" target="_blank">${m.name}</a>` : m.name;
      const installedPill = `<span class="pill ${m.installed ? "ok" : "miss"}">${m.installed ? "Installed" : "Not Installed"}</span>`;
      const safePath = (m.primary_path || "").replace(/'/g, "\\'");
      const copyBtn = m.installed && m.primary_path
        ? ` <button onclick="copyModelPath('${safePath}')" style="margin-left:6px; background:var(--pill); color:var(--text); border:1px solid var(--border); border-radius:6px; padding:2px 6px; font-size:11px;">Copy path</button>`
        : "";
      tr.innerHTML = `
        <td>${nameCell}</td>
        <td><span class="pill">${m.category}</span></td>
        <td>${m.type}</td>
        <td><code title="${m.source || ''}">${srcDisplay}</code></td>
        <td>${size}</td>
        <td>${installedPill}${copyBtn}</td>
        <td>
          <button onclick="pullModel('${m.name}', this)">Install</button>
          <button class="danger" onclick="deleteModel('${m.name}', this)">Delete</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
    status.textContent = "";
    table.style.display = "";
  } catch (e) {
    status.textContent = `Error: ${e.message || e}`;
  }
}

window.pullModel = async function (name, btn) {
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Installing...";
  try {
    await fetchJson(`/api/models/${encodeURIComponent(name)}/pull`, { method: "POST" });
    await loadModelsTable(true);
  } catch (e) {
    alert(`Pull failed: ${e.message || e}`);
  } finally {
    btn.disabled = false;
    btn.textContent = original;
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

window.applyModelSearch = function () {
  const search = document.getElementById("models-search");
  searchText = search ? (search.value.trim().toLowerCase()) : "";
  loadModelsTable(false);
};
