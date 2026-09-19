/* Persistent guided runs and comparison controls. */
window.trainingWorkspace = (() => {
  let epoch = 0, timer = null, selected = null, current = null, paused = false;
  let comparisonError = '';
  let comparisonFormRun = null;
  let sourceRun = null, preflightEpoch = 0, comparisonBusy = false, historySignature = '';
  const $ = id => document.getElementById(id);
  const api = (path, body) => fetchJson(`/api/training${path}`, body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const familyName = family => family === 'flux1' ? 'FLUX.1 dev · Kohya' : 'SDXL · Kohya';
  const element = (tag, text, className = '') => {
    const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
  };
  const button = (text, action, id) => {
    const node = element('button', text, 'btn ghost'); node.type = 'button';
    node.dataset.runAction = action; node.dataset.runId = id; return node;
  };
  function spec() {
    return { dataset_name: $('tp-dataset')?.value || 'preflight', output_name: $('tp-output')?.value || 'preview',
      family: $('tp-family')?.value || 'sdxl', profile: $('tp-profile')?.value || 'regular',
      toml_path: $('tp-toml')?.value || '', source_run_id: sourceRun };
  }
  function formState() {
    const family = spec().family;
    $('tp-summary-engine').textContent = familyName(family);
    $('tp-family-note').textContent = family === 'flux1'
      ? 'FLUX.1 dev requires its full-size model, AE, CLIP-L and FP16 T5 encoder. Uses batch size 1 and block swapping; allow substantial GPU and system memory.'
      : 'Use your configured SDXL checkpoint and VAE.';
    $('tp-advanced').hidden = family !== 'sdxl' || !!sourceRun;
    $('tp-saved-config').hidden = !sourceRun;
    $('tp-saved-config').textContent = sourceRun ? 'Using the saved configuration from the selected run. Your profile choice is applied to a new copy.' : '';
    $('tp-current-defaults').hidden = !sourceRun;
    updateTpSummary();
  }
  async function preflight() {
    if (!$('tp-page')) return;
    formState();
    const generation = ++preflightEpoch;
    $('tp-check-model').textContent = 'Checking model requirements…';
    try {
      const result = await api('/preflight', spec());
      if (generation !== preflightEpoch || !$('tp-page')) return;
      $('tp-check-model').textContent = result.missing.length
        ? `Missing ${result.missing.length} model file(s). You can download them before queuing.` : 'Required model files found';
      $('tp-check-model').classList.toggle('verified', !result.missing.length);
      $('tp-check-service').textContent = result.conflicts.length
        ? `The queue will wait: ${result.conflicts.join(' ')}` : 'No GPU conflicts detected. Checked again before launch.';
    } catch (error) {
      if (generation === preflightEpoch && $('tp-check-model')) $('tp-check-model').textContent = `Model check unavailable: ${error.message || error}`;
    }
  }
  function compatible(run) {
    return { run_id: run.id, running: ['running', 'stopping'].includes(run.status),
      exit_code: run.status === 'succeeded' ? 0 : run.exit_code,
      run: { dataset: run.spec.dataset_name, profile: run.spec.profile, finished_at: run.finished_at,
        stopped: ['stopped', 'cancelled', 'interrupted'].includes(run.status) },
      artifacts: run.artifacts || [], moved: !!run.library_files?.length, move_available: run.status === 'succeeded' && !!run.artifacts?.length,
      output_dir: run.output_dir, lora_destination: run.library_destination || 'Shared LoRA library',
      lines: run.lines || [] };
  }
  function renderHistory(data) {
    paused = data.paused;
    $('tp-queue-pause').textContent = paused ? 'Resume queue' : 'Pause queue';
    const waiting = data.runs.filter(run => run.status === 'queued').length;
    $('tp-queue-status').textContent = paused ? `Queue paused · ${waiting} waiting. Resume when you are ready.`
      : data.conflicts.length && waiting ? `Waiting · ${data.conflicts.join(' ')}`
      : data.active_id ? `Training in progress · ${waiting} waiting` : `${waiting} waiting · queue ready`;
    const signature = JSON.stringify(data.runs.map(run => [run.id, run.status, run.error, run.finished_at])) + selected;
    if (signature === historySignature) return;
    historySignature = signature;
    const list = $('tp-history-list'); list.replaceChildren();
    if (!data.runs.length) list.append(element('p', 'Your first training run will appear here.', 'journey-note'));
    for (const run of data.runs) {
      const row = element('article', '', 'tp-history-row');
      row.classList.toggle('selected', run.id === selected);
      const info = element('div', '', 'tp-history-info');
      info.append(element('strong', run.spec.output_name), element('span', `${familyName(run.spec.family)} · ${run.spec.dataset_name} · ${tpProfiles[run.spec.profile]}`, 'journey-note'));
      info.append(element('span', `${run.status} · ${new Date(run.created_at).toLocaleString()}`, 'tp-run-state'));
      if (run.error) info.append(element('p', run.error, 'status'));
      const actions = element('div', '', 'tp-history-actions');
      actions.append(button('View run', 'view', run.id), button('Use settings', 'settings', run.id));
      if (!['queued', 'running', 'stopping'].includes(run.status)) actions.append(button('Repeat run', 'repeat', run.id));
      else actions.append(button(run.status === 'queued' ? 'Cancel' : 'Stop', 'cancel', run.id));
      row.append(info, actions); list.append(row);
    }
  }
  function renderCurrent(run) {
    current = run; tpLastData = compatible(run); tpStatusKnown = true; tpRunning = tpLastData.running;
    const lines = run.lines || [];
    $('tp-logs').textContent = lines.join('\n') || 'No logs yet. Queued runs begin when the queue is resumed and the GPU is available.';
    $('tp-run-config').textContent = run.effective_config || run.config_text || 'No saved configuration.';
    $('tp-status').textContent = run.error || `${run.spec.output_name}: ${run.status}`;
    renderTpResult(tpLastData);
    $('tp-compare-download').href = `/api/training/runs/${run.id}/comparison/workflow`;
    $('tp-compare-download').hidden = !run.comparison_workflow;
    updateProgressUI(findLatestProgress(lines), tpRunning, run.status === 'succeeded');
    syncTpActions();
    const choices = $('tp-compare-artifact');
    const signature = JSON.stringify(run.artifacts || []);
    if (choices.dataset.signature !== signature || choices.dataset.run !== run.id) {
      choices.dataset.signature = signature; choices.dataset.run = run.id;
      choices.replaceChildren(...(run.artifacts || []).map(file => new Option(file.name, file.name)));
      if (choices.options.length) choices.selectedIndex = choices.options.length - 1;
    }
  }
  function renderComparison(data) {
    if (current && comparisonFormRun !== current.id) {
      comparisonFormRun = current.id;
      $('tp-compare-prompt').value = data.request?.prompt || '';
      $('tp-compare-seed').value = data.request?.seed ?? 31337;
      $('tp-compare-strength').value = data.request?.strength ?? 1;
      if (data.request?.artifact) $('tp-compare-artifact').value = data.request.artifact;
    }
    const active = ['queued', 'running', 'submitting', 'unknown'].includes(data.status);
    $('tp-compare-generate').disabled = comparisonBusy || active || !current?.artifacts?.length;
    $('tp-compare-open').disabled = comparisonBusy || !current?.artifacts?.length;
    $('tp-compare-reset').hidden = !['unknown', 'submitting', 'unavailable'].includes(data.status);
    $('tp-compare-status').textContent = data.error || comparisonError || ({ none: '', queued: 'Comparison queued in ComfyUI…', running: 'Generating both comparison images…', succeeded: 'Same prompt and seed. Only the LoRA branch changes.' }[data.status] ?? data.status);
    const images = $('tp-compare-images');
    const signature = JSON.stringify(data.images || []);
    if (images.dataset.signature === signature) return;
    images.dataset.signature = signature; images.replaceChildren();
    for (const item of data.images || []) {
      const figure = document.createElement('figure');
      const img = document.createElement('img'); img.alt = item.label; img.loading = 'lazy';
      if (!item.url.startsWith('/proxy/comfy/view?')) continue;
      img.src = item.url; figure.append(img, element('figcaption', item.label)); images.append(figure);
    }
  }
  async function poll(generation) {
    try {
      const data = await api('/runs');
      if (generation !== epoch || !$('tp-page')) return;
      if (!selected && data.runs.length) selected = data.active_id || data.runs[0].id;
      renderHistory(data); tpStatusKnown = true;
      if (selected) {
        const id = selected;
        const run = await api(`/runs/${id}`);
        if (generation !== epoch || id !== selected || !$('tp-page')) return;
        renderCurrent(run);
        if (run.status === 'succeeded' && !comparisonBusy) {
          try {
            const comparison = await api(`/runs/${id}/comparison`);
            if (generation === epoch && selected === id && $('tp-page')) renderComparison(comparison);
          } catch (error) {
            if (generation === epoch && $('tp-compare-status')) $('tp-compare-status').textContent = error.message || String(error);
          }
        }
      } else { $('tp-status').textContent = 'Ready to set up your first run'; syncTpActions(); }
    } catch (error) {
      if (generation === epoch && $('tp-queue-status')) {
        $('tp-queue-status').textContent = `History unavailable: ${error.message || error}. Retrying…`;
        tpStatusKnown = false; syncTpActions();
      }
    } finally {
      if (generation === epoch) timer = setTimeout(() => poll(generation), 3000);
    }
  }
  function refresh() { if (!$('tp-page')) return; clearTimeout(timer); epoch++; poll(epoch); }
  async function submit() {
    if (tpStarting || !tpStatusKnown) return;
    const request = spec();
    if (!$('tp-dataset').value || !$('tp-output').value.trim()) { showTpError('Choose a dataset and give your LoRA a name.'); return; }
    tpStarting = true; syncTpActions(); showTpError('');
    try {
      if (!await ensureTrainpilotModelsPresent(request.toml_path)) return;
      const run = await api('/runs', request);
      selected = run.id; tpDismissedRunId = null; refresh();
    } catch (error) { showTpError(`Could not queue training: ${error.message || error}`); }
    finally { tpStarting = false; if ($('tp-page')) syncTpActions(); }
  }
  async function historyAction(event) {
    const control = event.target.closest('[data-run-action]'); if (!control) return;
    const id = control.dataset.runId; control.disabled = true;
    try {
      if (control.dataset.runAction === 'view') { selected = id; comparisonError = ''; tpDismissedRunId = null; }
      if (control.dataset.runAction === 'settings') {
        const run = await api(`/runs/${id}`);
        $('tp-family').value = run.spec.family; $('tp-dataset').value = run.spec.dataset_name;
        $('tp-output').value = run.spec.output_name; $('tp-profile').value = run.spec.profile;
        document.querySelectorAll('[name="tp-profile-choice"]').forEach(input => input.checked = input.value === run.spec.profile);
        sourceRun = id;
        tpDismissedRunId = selected; if (tpLastData) renderTpResult(tpLastData);
        preflight(); $('tp-setup').scrollIntoView({ block: 'start', behavior: 'smooth' });
      }
      if (control.dataset.runAction === 'repeat') {
        if (!confirm('Queue a new run using this saved configuration? It uses the dataset as it exists now.')) return;
        const run = await api(`/runs/${id}/repeat`, {}); selected = run.id; tpDismissedRunId = null;
      }
      if (control.dataset.runAction === 'cancel') {
        if (!confirm('Stop or cancel this run? Already saved files remain in your workspace.')) return;
        await api(`/runs/${id}/cancel`, {});
      }
      refresh();
    } catch (error) { showTpError(error.message || String(error)); }
    finally { control.disabled = false; }
  }
  async function stopRun() {
    if (!current || !confirm('Stop this run? Saved checkpoints remain in your workspace.')) return;
    try { await api(`/runs/${current.id}/cancel`, {}); refresh(); }
    catch (error) { showTpError(error.message || String(error)); }
  }
  async function publish() {
    if (!current || tpMoving) return;
    tpMoving = true; renderTpResult(tpLastData);
    try {
      await api(`/runs/${current.id}/library`, {});
      $('tp-move-status').textContent = 'Copied to your library. Original run files remain saved.'; refresh();
    } catch (error) { $('tp-move-status').textContent = error.message || String(error); }
    finally { tpMoving = false; if (tpLastData) renderTpResult(tpLastData); }
  }
  async function compare(open = false) {
    if (!current || comparisonBusy) return;
    const request = { artifact: $('tp-compare-artifact').value, prompt: $('tp-compare-prompt').value.trim(), seed: Number($('tp-compare-seed').value), strength: Number($('tp-compare-strength').value) };
    if (!request.prompt) { $('tp-compare-status').textContent = 'Enter a prompt, including your trigger word.'; $('tp-compare-prompt').focus(); return; }
    const id = current.id; comparisonError = ''; comparisonBusy = true; renderComparison({status: 'submitting'});
    try {
      const result = await api(`/runs/${id}/comparison${open ? '/prepare' : ''}`, request);
      if (open) {
        window.pendingComfyWorkflow = result.workflow;
        window.loadSection('comfyui');
      } else if ($('tp-page') && current.id === id) {
        renderComparison(result);
        $('tp-compare-download').href = `/api/training/runs/${id}/comparison/workflow`;
        $('tp-compare-download').hidden = false;
      }
    } catch (error) {
      comparisonError = error.message || String(error);
      if ($('tp-compare-status')) $('tp-compare-status').textContent = comparisonError;
    } finally {
      comparisonBusy = false;
      if ($('tp-page')) { $('tp-compare-generate').disabled = false; $('tp-compare-open').disabled = false; refresh(); }
    }
  }
  async function init() {
    const generation = ++epoch;
    comparisonFormRun = null;
    historySignature = ''; sourceRun = null;
    $('tp-family').onchange = () => { sourceRun = null; preflight(); };
    $('tp-current-defaults').onclick = () => { sourceRun = null; preflight(); };
    $('tp-history-list').onclick = historyAction;
    $('tp-new-run').onclick = () => { tpDismissedRunId = selected; if (tpLastData) renderTpResult(tpLastData); $('tp-setup').hidden = false; $('tp-setup').scrollIntoView({block:'start'}); };
    $('tp-queue-pause').onclick = async () => {
      try { await api('/queue', {paused: !paused}); refresh(); }
      catch (error) { showTpError(error.message || String(error)); }
    };
    $('tp-compare-reset').onclick = async () => {
      if (!current || !confirm('Check ComfyUI for an earlier result before resetting. The ComfyUI queue must be empty.')) return;
      try { await api(`/runs/${current.id}/comparison/reset`, {}); comparisonError = ''; refresh(); }
      catch (error) { comparisonError = error.message || String(error); $('tp-compare-status').textContent = comparisonError; }
    };
    $('tp-compare-generate').onclick = () => compare(false);
    $('tp-compare-open').onclick = () => compare(true);
    try {
      const config = await fetchJson('/api/trainpilot/toml');
      if (generation !== epoch || !$('tp-page')) return;
      $('tp-toml').value = config.path;
      $('toml-config-path').textContent = config.path;
    } catch (error) { if (generation === epoch) showTpError(`SDXL configuration unavailable: ${error.message || error}`); }
    if (generation === epoch && $('tp-page')) { preflight(); refresh(); }
  }
  function stop() { epoch++; preflightEpoch++; clearTimeout(timer); timer = null; }
  return {init, stop, spec, preflight, submit, stopRun, publish};
})();
