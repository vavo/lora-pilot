let datasetsScreen = null;
let dsSelectedName = null;
let dsUploading = false;

window.initDatasets = async function (screen = window.createScreenLifecycle()) {
  datasetsScreen = screen;
  dsUploading = false;
  wireUpload();
  await loadDatasets();
};

async function loadDatasets() {
  const screen = datasetsScreen.latest("list");
  if (!screen?.active) return;
  const status = document.getElementById("ds-status");
  const list = document.getElementById("ds-list");
  const table = document.getElementById("ds-table");
  if (!status || !list) return;
  status.textContent = "Loading datasets...";
  list.innerHTML = "";
  if (table) table.classList.add("is-hidden");
  try {
    const data = await screen.json("/api/datasets");
    const count = document.getElementById("ds-count");
    if (count) count.textContent = `${data.length} dataset${data.length === 1 ? "" : "s"}`;
    document.getElementById("ds-next").hidden = true;
    if (!data.length) {
      status.textContent = "Your datasets will appear here. Upload a ZIP or create an empty dataset to get started.";
      return;
    }
    data.forEach(d => {
      const tr = document.createElement("tr");
      const size = d.size_bytes ? formatBytes(d.size_bytes) : "—";
      const link = tagpilotUrl(d.name);
      const nameTd = document.createElement("td");
      if (link) {
        const anchor = document.createElement("a");
        anchor.href = link;
        anchor.className = "ds-link";
        anchor.dataset.ds = d.name;
        anchor.textContent = d.display || d.name;
        nameTd.appendChild(anchor);
      } else {
        nameTd.textContent = d.display || d.name;
      }
      const nameInfo = document.createElement("div");
      nameInfo.append(...nameTd.childNodes);
      const sizeLabel = document.createElement("small");
      sizeLabel.textContent = size;
      nameInfo.append(sizeLabel);
      const nameLayout = document.createElement("div");
      nameLayout.className = "ds-name";
      const previews = document.createElement("div");
      previews.className = "ds-previews";
      (d.preview_files || []).slice(0, 3).forEach(file => {
        const img = document.createElement("img");
        img.src = `/api/datasets/${encodeURIComponent(d.name)}/preview?file=${encodeURIComponent(file)}`;
        img.alt = "";
        img.loading = "lazy";
        img.addEventListener("error", () => img.remove(), { once: true });
        previews.append(img);
      });
      nameLayout.append(previews, nameInfo);
      nameTd.append(nameLayout);
      tr.appendChild(nameTd);
      appendTextCell(tr, d.images || 0, "Images");
      const captionCell = appendTextCell(tr, `${d.captioned_images || 0} of ${d.images || 0}`, "Captions");
      const missing = Math.max(0, (d.images || 0) - (d.captioned_images || 0));
      const captionState = document.createElement("span");
      captionState.className = `ds-caption-state${missing ? " incomplete" : ""}`;
      captionState.textContent = missing ? `${missing} need captions` : d.images ? "All images captioned" : "Add your first images";
      captionCell.append(captionState);
      const actionsTd = document.createElement("td");
      const actions = document.createElement("div");
      actions.className = "ds-actions";
      const next = datasetActionButton(d.images && !missing ? "Train a LoRA" : d.images ? "Review captions" : "Add images", "ghost", "next", d.name);
      next.addEventListener("click", () => {
        dsSelectedName = d.name;
        if (d.images && !missing) openTrainingDataset(d.name);
        else openTagpilotDataset(d.name);
      });
      const menu = document.createElement("details");
      menu.className = "ds-menu";
      const summary = document.createElement("summary");
      summary.textContent = "Manage";
      menu.append(summary, datasetActionButton("Rename", "secondary", "rename", d.name), datasetActionButton("Delete", "danger", "del", d.name));
      actions.append(next, menu);
      actionsTd.append(actions);
      tr.appendChild(actionsTd);
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
    list.querySelectorAll("button[data-del]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const name = btn.getAttribute("data-del");
        if (!name) return;
        const ok = confirm(`Delete dataset ${name}? This will remove /workspace/datasets/${name} and its ZIP (if any).`);
        if (!ok) return;
        status.textContent = "Deleting...";
        try {
          await screen.json(`/api/datasets/${encodeURIComponent(name)}`, { method: "DELETE" });
          status.textContent = "Deleted.";
          await loadDatasets();
        } catch (e) {
          if (!screen.active) return;
          status.textContent = `Error: ${e.message || e}`;
        }
      });
    });
    list.querySelectorAll("button[data-rename]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const name = btn.getAttribute("data-rename");
        if (!name) return;
        const currentDisplay = name.replace(/^1_/, "").replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
        const newName = prompt(`Rename dataset "${currentDisplay}" to:`, currentDisplay);
        if (newName === null || newName.trim() === "") return;
        if (newName.trim() === currentDisplay) return;
        
        status.textContent = "Renaming...";
        try {
          await screen.json(`/api/datasets/${encodeURIComponent(name)}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: newName.trim() })
          });
          status.textContent = "Renamed.";
          await loadDatasets();
        } catch (e) {
          if (!screen.active) return;
          status.textContent = `Error: ${e.message || e}`;
        }
      });
    });
    if (table) table.classList.remove("is-hidden");
    status.textContent = "";
    showDatasetNextStep(data.find(d => d.name === dsSelectedName) || data[0]);
  } catch (e) {
    if (!screen.active) return;
    status.textContent = `Error: ${e.message || e}`;
  }
}

function appendTextCell(row, value, label) {
  const td = document.createElement("td");
  td.textContent = String(value);
  if (label) td.dataset.label = label;
  row.appendChild(td);
  return td;
}

function datasetActionButton(label, variant, action, datasetName) {
  const button = document.createElement("button");
  button.className = `btn ${variant}`;
  button.textContent = label;
  button.dataset[action] = datasetName;
  return button;
}

window.createDatasetPrompt = async function () {
  const screen = datasetsScreen;
  if (!screen?.active) return;
  const name = prompt("Name your dataset", "");
  if (name === null) return;
  const status = document.getElementById("ds-status");
  if (status) status.textContent = "Creating...";
  try {
    const created = await screen.json("/api/datasets/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name }),
    });
    dsSelectedName = created.name || created.path?.split("/").pop();
    if (status) status.textContent = "Created.";
    await loadDatasets();
    if (!screen.active) return;
  } catch (e) {
    if (!screen.active) return;
    if (status) status.textContent = `Error: ${e.message || e}`;
  }
};

async function uploadDatasetFile(file) {
  const screen = datasetsScreen;
  if (!screen?.active) return;
  const status = document.getElementById("ds-upload-status");
  const bar = document.getElementById("ds-upload-bar");
  if (bar) bar.style.width = "0%";
  if (!file) {
    if (status) status.textContent = "Select a ZIP first.";
    return;
  }
  if (dsUploading) return;
  dsUploading = true;
  const input = document.getElementById("ds-zip");
  if (input) input.disabled = true;
  if (status) status.textContent = "Uploading...";
  const fd = new FormData();
  fd.append("file", file);
  try {
    const response = await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const unlink = screen.onCleanup(() => xhr.abort());
      xhr.onloadend = unlink;
      xhr.onabort = () => reject(new DOMException('Screen left', 'AbortError'));
      xhr.open("POST", "/api/datasets/upload");
      xhr.upload.onprogress = (e) => {
        if (!screen.active) return;
        if (e.lengthComputable && bar) {
          const pct = Math.round((e.loaded / e.total) * 100);
          bar.style.width = `${pct}%`;
          if (status) status.textContent = pct === 100 ? "Upload received. Unpacking your dataset…" : `Uploading… ${pct}%`;
        }
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve(xhr.responseText);
        else reject(xhr.responseText || xhr.statusText);
      };
      xhr.onerror = () => reject("Upload failed");
      xhr.send(fd);
    });
    screen.check();
    const uploaded = JSON.parse(response);
    dsSelectedName = uploaded.extracted_to?.split("/").pop();
    if (status) status.textContent = "Uploaded.";
    dsUploading = false;
    closeUploadModal();
    await loadDatasets();
    if (!screen.active) return;
  } catch (e) {
    if (!screen.active) return;
    let message = e.message || String(e);
    try { message = JSON.parse(message).detail || message; } catch {}
    if (status) status.textContent = `Upload failed: ${message}. Choose a ZIP to retry.`;
  } finally {
    if (!screen.active) return;
    dsUploading = false;
    if (input) input.disabled = false;
  }
}

window.uploadDataset = async function () {
  const screen = datasetsScreen;
  if (!screen?.active) return;
  const fileInput = document.getElementById("ds-zip");
  if (!fileInput || !fileInput.files || !fileInput.files.length) return;
  const file = fileInput.files[0];
  await uploadDatasetFile(file);
};

window.openUploadModal = function () {
  const modal = document.getElementById("ds-modal");
  if (modal) { modal.classList.add("show"); modal.showModal(); }
};

window.closeUploadModal = function (evt) {
  if (dsUploading) return;
  if (evt && evt.target && evt.target.id !== "ds-modal" && !evt.target.closest(".modal-close")) return;
  const modal = document.getElementById("ds-modal");
  if (modal) { modal.classList.remove("show"); modal.close(); }
  document.getElementById("ds-upload-open")?.focus();
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
  const modal = document.getElementById("ds-modal");
  modal?.addEventListener("cancel", event => {
    event.preventDefault();
    closeUploadModal();
  });
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

function openTrainingDataset(name) {
  window.pendingTrainDataset = name;
  window.loadSection("trainpilot");
}

function showDatasetNextStep(dataset) {
  const panel = document.getElementById("ds-next");
  if (!panel || !dataset) return;
  const missing = Math.max(0, dataset.images - (dataset.captioned_images || 0));
  const ready = dataset.images > 0 && missing === 0;
  panel.hidden = false;
  document.getElementById("ds-next-title").textContent = ready ? "Next: choose a training profile" : missing ? "Next: finish your captions" : "Next: add your images";
  document.getElementById("ds-next-copy").textContent = ready
    ? `${dataset.display} has captions for all ${dataset.images} images. Review them before training.`
    : missing ? `${dataset.display} has ${missing} image${missing === 1 ? "" : "s"} without captions.` : `Open ${dataset.display} in Caption images to add files.`;
  const action = document.getElementById("ds-next-action");
  action.textContent = ready ? "Open training" : "Open Caption images";
  action.onclick = () => ready ? openTrainingDataset(dataset.name) : openTagpilotDataset(dataset.name);
}
