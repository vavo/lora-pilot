(() => {
  let models = [], jobs = [];
  let tab = "catalog", task = "video", query = "", familyId = null;
  let timer = null, generation = 0, statusUnavailable = false;
  const starting = new Set();
  const $ = id => document.getElementById(id);
  const families = () => window.modelFamilies;
  const members = family => models.filter(m => window.modelFamilyFor(m).id === family.id);
  const jobFor = name => jobs.find(j => j.name === name);
  const matches = m => [m.name, m.source, m.subdir, window.modelFamilyFor(m).title].some(v => String(v).toLowerCase().includes(query));

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }
  function button(label, action, value, className = "btn ghost") {
    const node = element("button", className, label);
    node.type = "button";
    node.dataset.modelAction = action;
    node.dataset.modelValue = value;
    return node;
  }
  function link(label, url) {
    const node = element("a", "models-text-button", label);
    const safe = window.sanitizeHttpUrl(url);
    if (safe) { node.href = safe; node.target = "_blank"; node.rel = "noopener noreferrer"; }
    return node;
  }
  function message(text, error = false) {
    const node = $("models-message");
    if (!node) return;
    node.className = error ? "models-error" : "models-note";
    node.textContent = text;
    const detail = $("models-detail-message");
    if (detail) { detail.textContent = text; detail.className = error ? "models-error" : "models-note"; detail.hidden = !text; }
  }
  function requirements(family) {
    return (window.modelWorkflowFiles[family.workflow] || []).map(file => ({
      ...file,
      model: models.find(m => m.kind === "hf_file" && m.source === file.url.replace("https://huggingface.co/", "").replace("/resolve/main/", ":")),
    }));
  }
  function summary(family) {
    const required = requirements(family).filter(r => !r.optional);
    if (required.length) return `${required.filter(r => r.model?.installed).length} of ${required.length} required files installed`;
    const list = members(family);
    return `${list.filter(m => m.installed).length} installed · ${list.length} catalog entries`;
  }
  function progress(job) {
    const bar = element("progress", "models-progress");
    bar.max = 100;
    bar.setAttribute("aria-label", `Download progress for ${job.name}`);
    if (typeof job.progress_pct === "number") bar.value = Math.max(0, Math.min(100, job.progress_pct));
    return bar;
  }
  function fileRow(model) {
    const row = element("div", "models-file-row");
    const info = element("div", "models-file-info");
    info.append(element("strong", "", model.name));
    const size = model.installed ? model.size_bytes : model.expected_size_bytes;
    info.append(element("small", "", `${model.type.replaceAll("_", " ")} · ${size ? `${model.installed ? "" : "Estimated "}${formatBytes(size)}` : "Size unknown"} · ${model.installed ? "Installed" : "Not installed"}`));
    const details = element("details");
    details.dataset.modelDetails = model.name;
    details.append(element("summary", "", "File details"));
    details.append(element("code", "models-path", model.primary_path || model.target_path));
    details.append(link("View source", model.info_url));
    if (model.installed) details.append(button("Copy path", "copy", model.name, "models-text-button"));
    info.append(details);
    const actions = element("div", "models-file-actions");
    const job = jobFor(model.name);
    if (starting.has(model.name) || job?.state === "running") {
      const pending = button(starting.has(model.name) ? "Starting…" : "Downloading…", "download", model.name);
      pending.disabled = true;
      actions.append(pending);
      if (job) info.append(progress(job));
    } else if (model.installed) {
      actions.append(button("Remove", "remove", model.name));
    } else {
      actions.append(button(job?.state === "error" ? "Retry download" : "Download", "download", model.name, "btn primary"));
    }
    if (job?.state === "error") info.append(element("p", "models-error", job.error || job.last_line || "Download failed. Retry when ready."));
    row.append(info, actions);
    return row;
  }
  function renderCatalog(container) {
    const selected = families().filter(f => members(f).some(matches) && (query || f.task === task || (task === "editing" && f.editing) || (task === "training" && f.training)));
    if (!selected.length) { container.append(element("p", "models-empty", "No models match. Try another task or search.")); return; }
    if (query) container.append(element("p", "models-note", "Search results across all tasks"));
    if (task === "training" && !query) container.append(element("p", "models-note", "Choose a model supported by your trainer. Available variants have different training requirements."));
    const grid = element("div", "models-family-grid");
    const more = element("div", "models-family-grid");
    selected.forEach((family, index) => {
      const card = element("article", "models-family-card");
      const body = element("div", "models-family-body");
      body.append(element("h3", "", family.title), element("p", "models-family-summary", family.summary));
      const tags = element("div", "models-tags");
      family.tags.forEach(tag => tags.append(element("span", "", tag)));
      body.append(tags, element("p", "models-family-description", family.description));
      body.append(button(`Set up ${family.title}`, "setup", family.id, "btn primary"));
      const footer = element("div", "models-family-footer");
      footer.append(element("span", "", summary(family)), button("Choose variant", "variants", family.id, "models-text-button"));
      card.append(body, footer);
      (index < 2 ? grid : more).append(card);
    });
    container.append(grid);
    const partial = selected.filter(f => {
      const list = requirements(f).filter(r => !r.optional);
      const installed = list.filter(r => r.model?.installed).length;
      return installed > 0 && installed < list.length;
    });
    if (partial.length) {
      const resume = element("section", "models-continue");
      resume.append(element("h3", "", "Continue setup"));
      partial.forEach(f => {
        const row = element("div", "models-continue-row");
        const info = element("div", "models-file-info");
        info.append(element("strong", "", f.title), element("small", "", summary(f)));
        row.append(info, button("Review missing files", "setup", f.id));
        resume.append(row);
      });
      container.append(resume);
    }
    if (selected.length > 2) {
      container.append(element("h3", "models-more-title", "More model families"), more);
    }
  }
  function renderDownloads(container) {
    const visible = jobs.filter(j => !query || j.name.toLowerCase().includes(query));
    if (!visible.length) { container.append(element("p", "models-empty", query ? "No downloads match your search." : "No recent downloads. Choose a model from the catalog to get started.")); return; }
    container.append(element("p", "models-note", "Recent download activity. Finished jobs are kept for a short time; installed models stay in Installed."));
    visible.forEach(job => {
      const row = element("div", "models-job");
      const info = element("div", "models-file-info");
      info.append(element("strong", "", job.name));
      const labels = { running: "Downloading", done: "Download complete", error: "Download failed" };
      info.append(element("small", "", labels[job.state] || job.state));
      if (job.state === "running") info.append(progress(job));
      if (job.state === "error") info.append(element("p", "models-error", job.error || job.last_line || "Unknown download error"));
      const details = element("details");
      details.dataset.modelDetails = job.name;
      details.append(element("summary", "", "Download details"), element("code", "models-path", job.last_line || "Waiting for output…"));
      info.append(details);
      row.append(info);
      if (job.state === "error" && models.some(m => m.name === job.name)) row.append(button("Retry", "download", job.name));
      container.append(row);
    });
  }
  function render() {
    if (!$("models-page")) return;
    const expanded = new Set(Array.from(document.querySelectorAll("details[open][data-model-details]")).map(d => d.dataset.modelDetails));
    const active = document.activeElement;
    const focus = active?.dataset?.modelAction ? { action: active.dataset.modelAction, value: active.dataset.modelValue } : null;
    document.querySelectorAll("[data-model-tab]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.modelTab === tab)));
    document.querySelectorAll("[data-model-task]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.modelTask === task)));
    $("models-tasks").hidden = tab !== "catalog";
    const installed = models.filter(m => m.installed);
    // The manifest may contain overlapping paths; do not claim this sum is disk usage.
    $("models-storage").replaceChildren(element("strong", "", `${installed.length} installed`), button("Manage installed files", "tab", "installed", "models-text-button"), document.createTextNode(" · "), button("Refresh", "refresh", "", "models-text-button"));
    const content = $("models-content");
    content.replaceChildren();
    if (tab === "catalog") renderCatalog(content);
    else if (tab === "downloads") renderDownloads(content);
    else {
      const list = installed.filter(matches);
      if (!list.length) content.append(element("p", "models-empty", query ? "No installed models match your search." : "No models installed yet. Start with a model family in the catalog."));
      list.forEach(m => content.append(fileRow(m)));
    }
    if (familyId && $("models-detail").open) renderDetail();
    document.querySelectorAll("details[data-model-details]").forEach(d => { d.open = expanded.has(d.dataset.modelDetails); });
    if (focus) {
      const scope = $("models-detail").open ? $("models-detail") : $("models-page");
      Array.from(scope.querySelectorAll("[data-model-action]")).find(b => b.dataset.modelAction === focus.action && b.dataset.modelValue === focus.value)?.focus({ preventScroll: true });
    }
  }
  function renderDetail() {
    const family = families().find(f => f.id === familyId);
    if (!family) return;
    $("models-detail-title").textContent = `Set up ${family.title}`;
    const body = $("models-detail-body");
    body.replaceChildren(element("p", "models-note", "Review the files before downloading. Installed means files were found; it does not confirm a successful generation."));
    const refs = requirements(family);
    if (refs.length) {
      body.append(element("h4", "", "Bundled workflow requirements"));
      body.append(element("p", "models-note", "This checklist matches the bundled text-to-video workflow. Other variants may need changes to the workflow's model selections."));
      refs.forEach(ref => {
        if (ref.model) {
          const row = fileRow(ref.model);
          if (ref.optional) row.querySelector("small").prepend("Optional prompt enhancer · ");
          body.append(row);
        } else {
          const row = element("div", "models-file-row");
          const info = element("div", "models-file-info");
          info.append(element("strong", "", ref.name), element("small", "", `${ref.optional ? "Optional · " : "Required · "}Not in catalog`));
          row.append(info, link("Get from source", ref.url));
          body.append(row);
        }
      });
      body.append(link("Workflow instructions", `https://github.com/Comfy-Org/workflow_templates/blob/785127914ff0f5bddb38c5fbe20c96912e564d9b/templates/${family.workflow}`));
    }
    const requiredNames = new Set(refs.map(r => r.model?.name));
    const variants = members(family).filter(m => !requiredNames.has(m.name));
    if (variants.length) {
      const section = element("section");
      section.id = "models-variants";
      section.append(element("h4", "", refs.length ? "Other variants and components" : "Choose a model or component"));
      section.append(element("p", "models-note", "Variants are alternatives. Download the files your chosen workflow needs."));
      variants.forEach(m => section.append(fileRow(m)));
      body.append(section);
    }
  }
  async function refresh(epoch) {
    try {
      const [list, activity] = await Promise.all([fetchJson("/api/models"), fetchJson("/api/models/pulls")]);
      if (epoch !== generation || !$("models-page")) return;
      models = list; jobs = activity.jobs || [];
      message(""); render();
    } catch (error) { if (epoch === generation) message(`Could not load models: ${error.message || error}`, true); }
  }
  async function poll(epoch) {
    if (epoch !== generation || !$("models-page")) return;
    try {
      const activity = await fetchJson("/api/models/pulls");
      if (epoch !== generation) return;
      if (statusUnavailable) { statusUnavailable = false; message(""); }
      const next = activity.jobs || [];
      if (!models.length) await refresh(epoch);
      if (JSON.stringify(next) !== JSON.stringify(jobs)) {
        const completed = next.some(j => j.state === "done" && jobFor(j.name)?.state !== "done");
        jobs = next;
        if (completed) await refresh(epoch); else render();
      }
    } catch (error) {
      if (epoch === generation) { statusUnavailable = true; message(`Download status unavailable: ${error.message || error}. Retrying…`, true); }
    }
    if (epoch === generation) timer = setTimeout(() => poll(epoch), 2500);
  }
  async function download(name) {
    if (starting.has(name) || jobFor(name)?.state === "running") return;
    starting.add(name); render();
    try {
      const job = await fetchJson(`/api/models/${encodeURIComponent(name)}/pull/start`, { method: "POST" });
      jobs = jobs.filter(j => j.name !== name).concat(job);
      message(`Started download: ${name}`);
    } catch (error) { message(`Download could not start: ${error.message || error}`, true); }
    finally { starting.delete(name); render(); }
  }
  async function action(event) {
    const control = event.target.closest("button[data-model-action]");
    if (!control) return;
    const value = control.dataset.modelValue;
    switch (control.dataset.modelAction) {
      case "tab": tab = value; render(); break;
      case "refresh": await refresh(generation); break;
      case "setup": case "variants":
        familyId = value; message(""); renderDetail(); $("models-detail").showModal();
        if (control.dataset.modelAction === "variants") $("models-variants")?.scrollIntoView({ block: "start" });
        break;
      case "download": await download(value); break;
      case "copy":
        try {
          const model = models.find(m => m.name === value);
          await navigator.clipboard.writeText(model.primary_path || model.target_path);
          control.textContent = "Copied";
        } catch (error) { control.textContent = "Copy unavailable"; }
        break;
      case "remove":
        if (!confirm(`Remove downloaded files for ${value}? Workflows using these files will need them downloaded again.`)) return;
        control.disabled = true;
        try {
          await fetchJson(`/api/models/${encodeURIComponent(value)}/delete`, { method: "POST" });
          await refresh(generation);
        } catch (error) { message(`Remove failed: ${error.message || error}`, true); control.disabled = false; }
        break;
    }
  }
  window.stopModels = function () { generation++; clearTimeout(timer); timer = null; familyId = null; };
  window.initModels = async function () {
    window.stopModels();
    const epoch = generation;
    $("models-search").value = query;
    $("models-page").addEventListener("click", action);
    $("models-detail").addEventListener("click", action);
    $("models-detail-close").onclick = () => $("models-detail").close();
    $("models-detail").addEventListener("close", () => { familyId = null; });
    $("models-search").addEventListener("input", event => { query = event.target.value.trim().toLowerCase(); render(); });
    document.querySelectorAll("[data-model-tab]").forEach(b => b.onclick = () => { tab = b.dataset.modelTab; render(); });
    document.querySelectorAll("[data-model-task]").forEach(b => b.onclick = () => { task = b.dataset.modelTask; render(); });
    message("Loading models…");
    await refresh(epoch);
    if (epoch === generation) timer = setTimeout(() => poll(epoch), 2500);
  };
})();
