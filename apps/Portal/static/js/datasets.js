window.initDatasets = async function () {
  await loadDatasets();
};

async function loadDatasets() {
  const status = document.getElementById("ds-status");
  const list = document.getElementById("ds-list");
  const table = document.getElementById("ds-table");
  if (!status || !list) return;
  status.textContent = "Loading datasets...";
  list.innerHTML = "";
  if (table) table.style.display = "none";
  try {
    const data = await fetchJson("/api/datasets");
    if (!data.length) {
      status.textContent = "No datasets found (expecting folders prefixed with 1_ under /workspace/datasets).";
      return;
    }
    data.forEach(d => {
      const tr = document.createElement("tr");
      const size = d.size_bytes ? formatBytes(d.size_bytes) : "—";
      tr.innerHTML = `<td>${d.display || d.name}</td><td>${d.images || 0}</td><td>${size}</td><td>${d.has_tags ? "Yes" : "No"}</td>`;
      list.appendChild(tr);
    });
    if (table) table.style.display = "";
    status.textContent = "";
  } catch (e) {
    status.textContent = `Error: ${e.message || e}`;
  }
}

window.createDatasetPrompt = async function () {
  const name = prompt("Enter dataset name (will create /workspace/datasets/1_<name>)", "");
  if (name === null) return;
  const status = document.getElementById("ds-status");
  if (status) status.textContent = "Creating...";
  try {
    await fetchJson("/api/datasets/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name }),
    });
    if (status) status.textContent = "Created.";
    await loadDatasets();
  } catch (e) {
    if (status) status.textContent = `Error: ${e.message || e}`;
  }
};

window.uploadDataset = async function () {
  const fileInput = document.getElementById("ds-zip");
  const status = document.getElementById("ds-upload-status");
  if (!fileInput || !fileInput.files || !fileInput.files.length) {
    if (status) status.textContent = "Select a ZIP first.";
    return;
  }
  const file = fileInput.files[0];
  if (status) status.textContent = "Uploading...";
  const fd = new FormData();
  fd.append("file", file);
  try {
    await fetchJson("/api/datasets/upload", {
      method: "POST",
      body: fd,
    });
    if (status) status.textContent = "Uploaded.";
    fileInput.value = "";
    await loadDatasets();
  } catch (e) {
    if (status) status.textContent = `Error: ${e.message || e}`;
  }
};

window.openUploadModal = function () {
  const modal = document.getElementById("ds-modal");
  if (modal) modal.style.display = "flex";
};

window.closeUploadModal = function () {
  const modal = document.getElementById("ds-modal");
  if (modal) modal.style.display = "none";
  const status = document.getElementById("ds-upload-status");
  if (status) status.textContent = "";
  const inp = document.getElementById("ds-zip");
  if (inp) inp.value = "";
};
