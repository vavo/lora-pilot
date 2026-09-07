(() => {
  let models = [], jobs = [];
  let tab = "catalog", task = "all", query = "", familyFilter = "all", familyId = "ltx25";
  let timer = null, generation = 0, statusUnavailable = false;
  const starting = new Set();
  const $ = id => document.getElementById(id);
  const families = () => window.modelFamilies;
  const members = family => models.filter(m => window.modelFamilyFor(m).id === family.id);
  const jobFor = name => jobs.find(j => j.name === name);
  const matches = m => {
    const family = window.modelFamilyFor(m);
    return [m.name, m.source, m.subdir, family.title, family.task, family.summary, ...family.tags].some(v => String(v).toLowerCase().includes(query));
  };

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
  function familyStatus(family) {
    const list = members(family);
    if (list.some(m => starting.has(m.name) || jobFor(m.name)?.state === "running")) return ["Downloading", "pending"];
    const required = requirements(family).filter(r => !r.optional);
    if (required.length) return required.every(r => r.model?.installed) ? ["Files installed", "installed"] : ["Missing components", "missing"];
    return list.some(m => m.installed) ? ["Files installed", "installed"] : ["Available", "available"];
  }
  function badge(label, state) { return element("span", `models-badge models-badge--${state}`, label); }
  function icon(section = "models") {
    const node = document.querySelector(`.nav [data-section="${section}"] .nav-icon`).cloneNode(true);
    node.className = "models-icon";
    return node;
  }
  function chevron() {
    const node = $("sidebar-compact-toggle").querySelector("svg").cloneNode(true);
    node.classList.add("models-chevron");
    node.setAttribute("aria-hidden", "true");
    return node;
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
    const selected = families().filter(f => members(f).some(matches) &&
      (familyFilter === "all" || f.id === familyFilter) &&
      (task === "all" || f.task === task || (task === "editing" && f.editing) || (task === "training" && f.training)));
    const featured = ["ltx25", "minimax", "flux", "qwen", "sdxl"];
    selected.sort((a, b) => (featured.includes(a.id) ? featured.indexOf(a.id) : 5) - (featured.includes(b.id) ? featured.indexOf(b.id) : 5));
    if (familyId && !selected.some(f => f.id === familyId)) familyId = selected[0]?.id || null;
    if (!selected.length) { container.append(element("p", "models-empty", "No models match. Try another filter or search.")); return; }
    if (task === "training") container.append(element("p", "models-note", "Choose a variant supported by your trainer."));
    const headings = element("div", "models-list-heading");
    ["Model", "Task", "Status", ""].forEach(label => headings.append(element("span", "", label)));
    container.append(headings);
    const list = element("div", "models-family-list");
    const taskNames = { images: "Image generation", video: "Video generation", editing: "Image editing", components: "Components" };
    const thumbnails = { ltx25: "ltx25", minimax: "minimax", flux: "flux", qwen: "qwen", sdxl: "sdxl" };
    selected.forEach(family => {
      const row = button("", "select", family.id, "models-family-row");
      row.setAttribute("aria-label", `View ${family.title}`);
      row.setAttribute("aria-pressed", String(family.id === familyId));
      row.setAttribute("aria-controls", "models-detail");
      const identity = element("span", "models-family-identity");
      if (thumbnails[family.id]) {
        const image = element("img", "models-family-image");
        image.src = `/model-icons/${thumbnails[family.id]}.png`;
        image.alt = "";
        identity.append(image);
      } else identity.append(icon());
      const description = element("span", "models-family-copy");
      description.append(element("strong", "", family.title), element("small", "", family.summary));
      identity.append(description);
      const label = family.id === "minimax" ? "Video + audio" : taskNames[family.task];
      row.append(identity, element("span", "models-task-label", label), badge(...familyStatus(family)), chevron());
      list.append(row);
    });
    container.append(list, element("p", "models-count", `${selected.length} model families`));
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
    const expanded = new Map(Array.from(document.querySelectorAll("details[data-model-details]")).map(d => [d.dataset.modelDetails, d.open]));
    const active = document.activeElement;
    const focus = active?.dataset?.modelAction ? { action: active.dataset.modelAction, value: active.dataset.modelValue } : null;
    document.querySelectorAll("[data-model-tab]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.modelTab === tab)));
    $("models-filters").hidden = tab !== "catalog";
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
    const showDetail = tab === "catalog" && !!familyId && models.length > 0;
    $("models-workspace").classList.toggle("models-workspace--detail", showDetail);
    $("models-detail").hidden = !showDetail;
    if (showDetail) renderDetail();
    document.querySelectorAll("details[data-model-details]").forEach(d => { if (expanded.has(d.dataset.modelDetails)) d.open = expanded.get(d.dataset.modelDetails); });
    if (focus) {
      const scope = $("models-page");
      Array.from(scope.querySelectorAll("[data-model-action]")).find(b => b.dataset.modelAction === focus.action && b.dataset.modelValue === focus.value)?.focus({ preventScroll: true });
    }
  }
  function renderDetail() {
    const family = families().find(f => f.id === familyId);
    if (!family) return;
    $("models-detail-title").textContent = family.title;
    $("models-detail-subtitle").textContent = family.tags.join(" · ");
    const body = $("models-detail-body");
    const changedFamily = body.dataset.family !== familyId;
    body.dataset.family = familyId;
    body.replaceChildren(element("p", "models-detail-description", family.description));
    const refs = requirements(family);
    if (refs.length) {
      body.append(element("h4", "", "Required files"));
      const groups = new Map();
      refs.filter(ref => !ref.optional).forEach(ref => {
        if (!groups.has(ref.directory)) groups.set(ref.directory, []);
        groups.get(ref.directory).push(ref);
      });
      const labels = { diffusion_models: "Diffusion model", text_encoders: "Text encoder", vae: "Video + audio VAEs", latent_upscale_models: "Spatial upscaler", loras: "Turbo LoRA" };
      const groupList = element("div", "models-requirements");
      const groupOrder = ["diffusion_models", "text_encoders", "vae", "latent_upscale_models", "loras"];
      Array.from(groups).sort((a, b) => groupOrder.indexOf(a[0]) - groupOrder.indexOf(b[0])).forEach(([directory, files]) => {
        const details = element("details", "models-requirement");
        details.dataset.modelDetails = `${family.id}:${directory}`;
        const heading = element("summary");
        const installed = files.every(ref => ref.model?.installed);
        heading.append(icon(directory === "text_encoders" ? "settings" : "models"), element("span", "models-requirement-title", labels[directory] || directory), badge(installed ? "Installed" : "Missing", installed ? "installed" : "missing"), chevron());
        details.append(heading);
        files.forEach(ref => details.append(requirementRow(ref)));
        groupList.append(details);
      });
      body.append(groupList);
      const optional = refs.filter(ref => ref.optional);
      if (optional.length) {
        const details = element("details", "models-optional");
        details.dataset.modelDetails = `${family.id}:optional`;
        details.append(element("summary", "", "Optional · Prompt enhancer"));
        optional.forEach(ref => details.append(requirementRow(ref)));
        body.append(details);
      }
    }
    const requiredNames = new Set(refs.map(r => r.model?.name));
    const variants = members(family).filter(m => !requiredNames.has(m.name) && (!query || matches(m)));
    if (variants.length) {
      const section = element("details", "models-variants");
      section.dataset.modelDetails = `${family.id}:variants`;
      section.open = !refs.length;
      section.append(element("summary", "", refs.length ? "Other variants and components" : "Models and components"));
      section.append(element("p", "models-note", "Choose the files your workflow needs. Variants are alternatives."));
      variants.forEach(m => section.append(fileRow(m)));
      body.append(section);
    }
    const access = element("div", "models-access");
    access.append(element("strong", "", "Hugging Face access"), element("p", "models-note", "Some sources require access approval and a token. Review the source if a download fails."), button("Access settings", "settings", "", "models-text-button"));
    body.append(access);
    if (refs.length) {
      body.append(button("Review installation", "review", family.id, "btn primary models-review"));
      body.append(element("p", "models-count", "Review missing files before downloading."));
      body.append(link("Workflow instructions", `https://github.com/Comfy-Org/workflow_templates/blob/785127914ff0f5bddb38c5fbe20c96912e564d9b/templates/${family.workflow}`));
    }
    body.append(element("p", "models-note", "Installed means files were found. Generation has not been verified."));
    if (changedFamily) body.scrollTop = 0;
  }
  function requirementRow(ref) {
    if (ref.model) return fileRow(ref.model);
    const row = element("div", "models-file-row");
    const info = element("div", "models-file-info");
    info.append(element("strong", "", ref.name), element("small", "", "Not in catalog"));
    row.append(info, link("Get from source", ref.url));
    return row;
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
      case "select":
        familyId = value; message(""); render();
        if (window.matchMedia("(max-width: 1000px)").matches) $("models-detail").scrollIntoView({ block: "start", behavior: "smooth" });
        break;
      case "review":
        $("models-detail").querySelectorAll("details.models-requirement").forEach(d => { d.open = true; });
        $("models-detail-body").scrollTop = 0;
        $("models-detail-body").querySelector("summary")?.focus();
        break;
      case "settings": document.querySelector('.nav [data-section="settings"]').click(); break;
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
  window.stopModels = function () { generation++; clearTimeout(timer); timer = null; };
  window.initModels = async function () {
    window.stopModels();
    const epoch = generation;
    if (window.matchMedia("(max-width: 1000px)").matches) familyId = null;
    $("models-search").value = query;
    $("models-page").addEventListener("click", action);
    $("models-detail-close").onclick = () => {
      const selected = familyId;
      familyId = null; render();
      Array.from($("models-content").querySelectorAll("[data-model-action]")).find(b => b.dataset.modelValue === selected)?.focus({ preventScroll: true });
    };
    $("models-task-filter").value = task;
    $("models-family-filter").replaceChildren(new Option("All families", "all"));
    families().forEach(f => $("models-family-filter").add(new Option(f.title, f.id)));
    $("models-family-filter").value = familyFilter;
    $("models-task-filter").onchange = event => { task = event.target.value; render(); };
    $("models-family-filter").onchange = event => { familyFilter = event.target.value; render(); };
    $("models-search").addEventListener("input", event => { query = event.target.value.trim().toLowerCase(); render(); });
    document.querySelectorAll("[data-model-tab]").forEach(b => b.onclick = () => { tab = b.dataset.modelTab; render(); });
    message("Loading models…");
    await refresh(epoch);
    if (epoch === generation) timer = setTimeout(() => poll(epoch), 2500);
  };
})();
