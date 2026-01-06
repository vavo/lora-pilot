window.initDatasets = async function () {
  wireUpload();
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
      const link = tagpilotUrl(d.name);
      const nameCell = link ? `<a href="${link}" class="ds-link" data-ds="${d.name}">${d.display || d.name}</a>` : (d.display || d.name);
      tr.innerHTML = `<td>${nameCell}</td><td>${d.images || 0}</td><td>${size}</td><td>${d.has_tags ? "Yes" : "No"}</td>`;
      list.appendChild(tr);
    });
    // wire inline navigation
    list.querySelectorAll(".ds-link").forEach(a => {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        const name = a.getAttribute("data-ds");
        if (name) openTagpilotDataset(name);
      });
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

async function uploadDatasetFile(file) {
  const status = document.getElementById("ds-upload-status");
  const bar = document.getElementById("ds-upload-bar");
  if (bar) bar.style.width = "0%";
  if (!file) {
    if (status) status.textContent = "Select a ZIP first.";
    return;
  }
  if (status) status.textContent = "Uploading...";
  const fd = new FormData();
  fd.append("file", file);
  try {
    await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/datasets/upload");
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && bar) {
          const pct = Math.round((e.loaded / e.total) * 100);
          bar.style.width = `${pct}%`;
        }
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve(xhr.responseText);
        else reject(xhr.responseText || xhr.statusText);
      };
      xhr.onerror = () => reject("Upload failed");
      xhr.send(fd);
    });
    if (status) status.textContent = "Uploaded.";
    closeUploadModal();
    await loadDatasets();
  } catch (e) {
    if (status) status.textContent = `Error: ${e}`;
  }
}

window.uploadDataset = async function () {
  const fileInput = document.getElementById("ds-zip");
  if (!fileInput || !fileInput.files || !fileInput.files.length) return;
  const file = fileInput.files[0];
  await uploadDatasetFile(file);
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
  const bar = document.getElementById("ds-upload-bar");
  if (bar) bar.style.width = "0%";
};

function tagpilotUrl(datasetName) {
  return `${window.location.origin}/tagpilot/?dataset=${encodeURIComponent(datasetName)}`;
}

function openTagpilotDataset(name) {
  window.pendingTagDataset = name;
  const iframe = document.querySelector("iframe[src^=\"/tagpilot\"]");
  if (iframe) {
    iframe.src = `/tagpilot/?dataset=${encodeURIComponent(name)}`;
    if (window.loadSection) window.loadSection("tagpilot");
  } else if (window.loadSection) {
    window.loadSection("tagpilot").then(() => {
      const ifr = document.querySelector("iframe[src^=\"/tagpilot\"]");
      if (ifr) ifr.src = `/tagpilot/?dataset=${encodeURIComponent(name)}`;
    });
  } else {
    window.location.href = tagpilotUrl(name);
  }
}

function wireUpload() {
  const input = document.getElementById("ds-zip");
  const dz = document.getElementById("ds-dropzone");
  if (input) {
    input.addEventListener("change", () => {
      if (input.files && input.files.length) uploadDatasetFile(input.files[0]);
    });
  }
  if (dz) {
    ["dragenter", "dragover"].forEach(ev => dz.addEventListener(ev, e => {
      e.preventDefault();
      dz.style.borderColor = "var(--accent)";
    }));
    ["dragleave", "drop"].forEach(ev => dz.addEventListener(ev, e => {
      e.preventDefault();
      dz.style.borderColor = "var(--border)";
    }));
    dz.addEventListener("drop", e => {
      const files = e.dataTransfer?.files;
      if (files && files.length) uploadDatasetFile(files[0]);
    });
  }
}
