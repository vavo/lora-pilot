let allModels = [];
let filterCat = "ALL";
let searchText = "";

window.initModels = async function () {
  const hf = document.getElementById("hf-token");
  if (hf && !hf.dataset.bound) {
    hf.dataset.bound = "1";
  }
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
  const token = document.getElementById("hf-token").value.trim();
  if (!token) { alert("Enter a token"); return; }
  try {
    await fetchJson("/api/hf-token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    alert("HF_TOKEN saved.");
  } catch (e) {
    alert(`Failed to save token: ${e.message || e}`);
  }
};

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
      tr.innerHTML = `
        <td>${m.name}</td>
        <td><span class="pill">${m.category}</span></td>
        <td>${m.type}</td>
        <td><code>${m.source}</code></td>
        <td>${size}</td>
        <td><span class="pill ${m.installed ? "ok" : "miss"}">${m.installed ? "Installed" : "Not Installed"}</span></td>
        <td>${m.info_url ? `<a href="${m.info_url}" target="_blank">Info</a>` : "—"}</td>
        <td>
          <button onclick="pullModel('${m.name}', this)">Install</button>
          <button onclick="deleteModel('${m.name}', this)">Delete</button>
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
