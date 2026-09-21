/* Persistent guided runs and comparison controls. */
window.trainingWorkspace = (() => {
  let trainingScreen = null, selected = null, current = null, paused = false;
  let historySearch = '', historyFamily = '', historyState = '', offset = 0, filterTimer;
  let comparisonError = '', preparation = null;
  let comparisonFormRun = null;
  let draft = null, preferSetup = false;
  let sourceRun = null, comparisonBusy = false, historySignature = '';
  const $ = id => document.getElementById(id);
  const api = (screen, path, body) => screen.json(`/api/training${path}`, body === undefined ? {} : {
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
  function saveDraft() {
    try {
      draft.save({...spec(), dataset_name: $('tp-dataset').value, output_name: $('tp-output').value});
      $('tp-draft-status').textContent = 'Draft saved in this browser.';
    } catch { $('tp-draft-status').textContent = 'Browser storage is unavailable. Keep this page open to retain your setup.'; }
  }
  function applyDraft(value, explicitDataset) {
    $('tp-family').value = value.family; $('tp-profile').value = value.profile;
    document.querySelectorAll('[name="tp-profile-choice"]').forEach(input => input.checked = input.value === value.profile);
    if (!explicitDataset) {
      $('tp-dataset').value = value.dataset_name;
      $('tp-output').value = normalizeOutputName(value.output_name);
    }
    sourceRun = value.source_run_id;
    updateEpochExample($('tp-output').value);
    $('tp-draft-status').textContent = !explicitDataset && value.dataset_name && !$('tp-dataset').value
      ? 'Draft restored. Its dataset is unavailable; choose a dataset before training.' : 'Draft restored from this browser.';
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
    if (!trainingScreen?.active || !$('tp-page')) return;
    formState();
    const screen = trainingScreen.latest("preflight");
    $('tp-check-model').textContent = 'Checking model requirements…';
    try {
      const result = await api(screen, '/preflight', spec());
      if (!screen.active || !$('tp-page')) return;
      $('tp-check-model').textContent = result.missing.length
        ? `Missing ${result.missing.length} model file(s). You can download them before queuing.` : 'Required model files found';
      $('tp-check-model').classList.toggle('verified', !result.missing.length);
      $('tp-check-service').textContent = result.conflicts.length
        ? `The queue will wait: ${result.conflicts.join(' ')}` : 'No GPU conflicts detected. Checked again before launch.';
    } catch (error) {
      if (!screen.active) return;
      if (screen.active && $('tp-check-model')) $('tp-check-model').textContent = `Model check unavailable: ${error.message || error}`;
    }
  }
  function compatible(run) {
    return { run_id: run.id, running: ['running', 'stopping'].includes(run.status),
      exit_code: run.status === 'succeeded' ? 0 : run.exit_code,
      run: { dataset: run.spec.dataset_name, profile: run.spec.profile, finished_at: run.finished_at,
        stopped: ['stopped', 'cancelled', 'interrupted'].includes(run.status) },
      artifacts: run.artifacts || [], moved: !!run.artifacts?.length && run.artifacts.every(file => file.in_output === false),
      move_available: run.status === 'succeeded' && !!run.artifacts?.length,
      output_dir: run.output_dir, lora_destination: run.library_destination || 'Shared LoRA library',
      lines: run.lines || [] };
  }
  function renderHistory(data) {
    paused = data.paused;
    $('tp-queue-pause').textContent = paused ? 'Resume queue' : 'Pause queue';
    const waiting = data.queued_count ?? data.runs.filter(run => run.status === 'queued').length;
    const total = data.total ?? data.runs.length;
    $('tp-history-count').textContent = total ? `${offset + 1}–${Math.min(offset + data.runs.length, total)} of ${total} matching runs` : 'No matching runs';
    $('tp-history-prev').disabled = offset === 0; $('tp-history-next').disabled = offset + data.runs.length >= total;
    $('tp-queue-status').textContent = paused ? `Queue paused · ${waiting} waiting. Resume when you are ready.`
      : data.conflicts.length && waiting ? `Waiting · ${data.conflicts.join(' ')}`
      : data.active_id ? `Training in progress · ${waiting} waiting` : `${waiting} waiting · queue ready`;
    const signature = JSON.stringify(data.runs.map(run => [run.id, run.status, run.error, run.finished_at])) + selected;
    if (signature === historySignature) return;
    historySignature = signature;
    const list = $('tp-history-list'); list.replaceChildren();
    if (!data.runs.length) list.append(element('p', historySearch || historyFamily || historyState ? 'No runs match these filters.' : 'Your first training run will appear here.', 'journey-note'));
    for (const run of data.runs) {
      const row = element('article', '', 'tp-history-row');
      row.classList.toggle('selected', run.id === selected);
      const info = element('div', '', 'tp-history-info');
      info.append(element('strong', run.spec.output_name), element('span', `${familyName(run.spec.family)} · ${run.spec.dataset_name} · ${tpProfiles[run.spec.profile]}`, 'journey-note'));
      info.append(element('span', `${run.status} · ${new Date(run.created_at).toLocaleString()}`, 'tp-run-state'));
      if (run.error) info.append(taskError(run.error));
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
    $('tp-run-timing').textContent = trainingTimeLabel(run.timing);
    const errorBox = $('tp-run-error');
    if (errorBox.dataset.error !== (run.error || '')) { errorBox.dataset.error = run.error || ''; errorBox.replaceChildren(...(run.error ? [taskError(run.error + '\n' + lines.slice(-30).join('\n'))] : [])); }
    const downloads = $('tp-checkpoint-downloads');
    const downloadSignature = JSON.stringify([run.id, run.status, run.artifacts]);
    if (downloads.dataset.signature !== downloadSignature) {
      downloads.dataset.signature = downloadSignature; downloads.replaceChildren();
      if (!['queued','running','stopping','succeeded'].includes(run.status)) for (const file of run.artifacts || []) {
        const link = element('a', `Download ${file.name}`, 'journey-link');
        link.href = `/api/training/runs/${run.id}/artifacts/${encodeURIComponent(file.name)}`;
        downloads.append(element('p', 'Saved checkpoint'), link);
      }
    }
    $('tp-compare-download').href = `/api/training/runs/${run.id}/comparison/workflow`;
    $('tp-compare-download').hidden = !run.comparison_workflow;
    updateProgressUI(findLatestProgress(lines), tpRunning, run.status === 'succeeded');
    syncTpActions();
    const choices = $('tp-compare-artifact');
    const signature = JSON.stringify(run.artifacts || []);
    if (choices.dataset.signature !== signature || choices.dataset.run !== run.id) {
      choices.dataset.signature = signature; choices.dataset.run = run.id;
      choices.replaceChildren(new Option('All checkpoints · baseline first', ''), ...(run.artifacts || []).map(file => new Option(file.name, file.name)));
    }
  }
  function renderComparison(data) {
    if (current && comparisonFormRun !== current.id) {
      comparisonFormRun = current.id;
      $('tp-compare-prompt').value = data.request?.prompt || '';
      $('tp-compare-seed').value = data.request?.seed ?? 31337;
      $('tp-compare-strength').value = data.request?.strength ?? 1;
      $('tp-compare-artifact').value = data.request?.all_checkpoints ? '' : (data.request?.artifact || '');
    }
    const active = ['queued', 'running', 'submitting', 'unknown'].includes(data.status);
    $('tp-compare-generate').disabled = comparisonBusy || active || !current?.artifacts?.length;
    $('tp-compare-open').disabled = comparisonBusy || !current?.artifacts?.length;
    $('tp-compare-reset').hidden = !['unknown', 'submitting', 'unavailable'].includes(data.status);
    $('tp-compare-status').textContent = data.error || comparisonError || ({ none: '', queued: 'Comparison queued in ComfyUI…', running: 'Generating the baseline and checkpoint images…', succeeded: 'Same prompt and seed. Baseline first, then each checkpoint in training order.' }[data.status] ?? data.status);
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
  async function poll(screen) {
    try {
      const data = await api(screen, `/runs?${new URLSearchParams({search:historySearch, family:historyFamily, status:historyState, offset:String(offset)})}`);
      if (!screen.active || !$('tp-page')) return;
      if (!selected && data.runs.length) selected = data.active_id || data.runs[0].id;
      if (offset && !data.runs.length && data.total) { offset = 0; refresh(); return; }
      renderHistory(data); tpStatusKnown = true;
      if (selected) {
        const id = selected;
        const run = await api(screen, `/runs/${id}`);
        if (!screen.active || id !== selected || !$('tp-page')) return;
        if (preferSetup) tpDismissedRunId = id;
        renderCurrent(run);
        if (run.status === 'succeeded' && !comparisonBusy) {
          try {
            const comparison = await api(screen, `/runs/${id}/comparison`);
            if (screen.active && selected === id && $('tp-page')) renderComparison(comparison);
          } catch (error) {
            if (!screen.active) return;
            if (screen.active && $('tp-compare-status')) $('tp-compare-status').textContent = error.message || String(error);
          }
        }
      } else { $('tp-status').textContent = 'Ready to set up your first run'; syncTpActions(); }
    } catch (error) {
      if (!screen.active) return;
      if (screen.active && $('tp-queue-status')) {
        $('tp-queue-status').textContent = `History unavailable: ${error.message || error}. Retrying…`;
        tpStatusKnown = false; syncTpActions();
      }
    }
  }
  function refresh() {
    if (!trainingScreen?.active) return;
    const screen = trainingScreen.latest('history');
    screen.poll(() => poll(screen), 3000);
  }
  async function submit() {
    const screen = trainingScreen;
    if (!screen?.active) return;
    if (tpStarting || !tpStatusKnown) return;
    const request = spec();
    if (!$('tp-dataset').value || !$('tp-output').value.trim()) { showTpError('Choose a dataset and give your LoRA a name.'); return; }
    const controller = screen.latest("preparation"); preparation = controller;
    tpStarting = true; syncTpActions(); showTpError('');
    try {
      if (!await ensureTrainpilotModelsPresent(request, controller.signal)) return;
      controller.signal.throwIfAborted();
      const run = await api(screen, '/runs', request);
      try { draft.clear(); } catch {}
      preferSetup = false;
      if ($('tp-draft-status')) $('tp-draft-status').textContent = 'Run queued. The submitted draft has been cleared.';
      selected = run.id; tpDismissedRunId = null; refresh();
    } catch (error) { if (!screen.active) return; if (!controller.signal.aborted) showTpError(`Could not queue training: ${error.message || error}`); }
    finally { if (!screen.active) return; if (preparation === controller) preparation = null; clearModelDownloadUI(); tpStarting = false; if ($('tp-page')) syncTpActions(); }
  }
  async function historyAction(event) {
    const screen = trainingScreen;
    if (!screen?.active) return;
    const control = event.target.closest('[data-run-action]'); if (!control) return;
    const id = control.dataset.runId; control.disabled = true;
    try {
      if (control.dataset.runAction === 'view') {
        preferSetup = false; selected = id; comparisonError = ''; tpDismissedRunId = null;
        $('tp-run-config').textContent = 'Loading saved run configuration…';
        $('tp-logs').textContent = 'Loading run logs…';
        const details = $('tp-run-config').closest('details');
        details.open = true; $('tp-diagnostics').open = true;
        details.scrollIntoView({ block: 'start', behavior: 'smooth' });
        details.querySelector('summary').focus({ preventScroll: true });
      }
      if (control.dataset.runAction === 'settings') {
        const run = await api(screen, `/runs/${id}`);
        $('tp-family').value = run.spec.family; $('tp-dataset').value = run.spec.dataset_name;
        $('tp-output').value = run.spec.output_name; $('tp-profile').value = run.spec.profile;
        document.querySelectorAll('[name="tp-profile-choice"]').forEach(input => input.checked = input.value === run.spec.profile);
        sourceRun = id; preferSetup = true; saveDraft();
        tpDismissedRunId = selected; if (tpLastData) renderTpResult(tpLastData);
        preflight(); $('tp-setup').scrollIntoView({ block: 'start', behavior: 'smooth' });
      }
      if (control.dataset.runAction === 'repeat') {
        if (!confirm('Queue a new run using this saved configuration? It uses the dataset as it exists now.')) return;
        const run = await api(screen, `/runs/${id}/repeat`, {}); selected = run.id; tpDismissedRunId = null;
      }
      if (control.dataset.runAction === 'cancel') {
        if (!confirm('Stop or cancel this run? Already saved files remain in your workspace.')) return;
        await api(screen, `/runs/${id}/cancel`, {});
      }
      refresh();
    } catch (error) { if (!screen.active) return; showTpError(error.message || String(error)); }
    finally { if (!screen.active) return; control.disabled = false; }
  }
  async function stopRun() {
    const screen = trainingScreen;
    if (!screen?.active) return;
    if (!current || !confirm('Stop this run? Saved checkpoints remain in your workspace.')) return;
    try { await api(screen, `/runs/${current.id}/cancel`, {}); refresh(); }
    catch (error) { if (!screen.active) return; showTpError(error.message || String(error)); }
  }
  async function publish(action = 'move') {
    const screen = trainingScreen;
    if (!screen?.active) return;
    if (!current || tpMoving) return;
    const id = current.id;
    tpMoving = action; renderTpResult(tpLastData);
    try {
      await api(screen, `/runs/${id}/library`, {action});
      if (current?.id !== id) return;
      $('tp-move-status').textContent = action === 'move' ? 'Moved to your library. Downloads and comparisons still work here.' : 'Copied to your library. Original run files remain saved.'; refresh();
    } catch (error) { if (!screen.active) return; $('tp-move-status').textContent = error.message || String(error); }
    finally { if (!screen.active) return; tpMoving = false; if (tpLastData) renderTpResult(tpLastData); }
  }
  async function compare(open = false) {
    const screen = trainingScreen;
    if (!screen?.active) return;
    if (!current || comparisonBusy) return;
    const artifact = $('tp-compare-artifact').value;
    const request = { artifact: artifact || null, all_checkpoints: !artifact, prompt: $('tp-compare-prompt').value.trim(), seed: Number($('tp-compare-seed').value), strength: Number($('tp-compare-strength').value) };
    if (!request.prompt) { $('tp-compare-status').textContent = 'Enter a prompt, including your trigger word.'; $('tp-compare-prompt').focus(); return; }
    const id = current.id; comparisonError = ''; comparisonBusy = true; renderComparison({status: 'submitting'});
    try {
      const result = await api(screen, `/runs/${id}/comparison${open ? '/prepare' : ''}`, request);
      if (open) {
        window.pendingComfyWorkflow = {workflow: result.workflow, runId: id, token: crypto.randomUUID()};
        window.loadSection('comfyui');
      } else if ($('tp-page') && current.id === id) {
        renderComparison(result);
        $('tp-compare-download').href = `/api/training/runs/${id}/comparison/workflow`;
        $('tp-compare-download').hidden = false;
      }
    } catch (error) {
      if (!screen.active) return;
      comparisonError = error.message || String(error);
      if ($('tp-compare-status')) $('tp-compare-status').textContent = comparisonError;
    } finally {
      if (!screen.active) return;
      comparisonBusy = false;
      if ($('tp-page')) { $('tp-compare-generate').disabled = false; $('tp-compare-open').disabled = false; refresh(); }
    }
  }
  async function init(explicitDataset, screen = window.createScreenLifecycle()) {
    trainingScreen = screen;
    comparisonBusy = false; tpStarting = false; tpMoving = false;
    const linkedRun = window.pendingTrainingRun;
    if (linkedRun) { selected = linkedRun; window.pendingTrainingRun = null; tpDismissedRunId = null; }
    comparisonFormRun = null;
    historySignature = ''; sourceRun = null;
    preferSetup = !!explicitDataset && !linkedRun;
    try {
      draft = createTrainingDraft(window.localStorage);
      const saved = draft.read();
      if (saved) { applyDraft(saved, explicitDataset); preferSetup = !linkedRun; }
    } catch { if (!screen.active) return; $('tp-draft-status').textContent = 'Saved draft could not be read. You can still set up training.'; }
    if (explicitDataset) saveDraft();
    $('tp-fields').addEventListener('input', saveDraft);
    $('tp-fields').addEventListener('change', saveDraft);
    $('tp-clear-draft').onclick = () => {
      try {
        draft.clear();
        applyDraft({family:'sdxl', profile:'regular', dataset_name:'', output_name:'', source_run_id:null});
        $('tp-draft-status').textContent = 'Draft cleared.';
        preferSetup = true; preflight();
      } catch { $('tp-draft-status').textContent = 'Browser storage is unavailable; the saved draft could not be cleared.'; }
    };
    $('tp-family').onchange = () => { sourceRun = null; preflight(); };
    $('tp-current-defaults').onclick = () => { sourceRun = null; saveDraft(); preflight(); };
    $('tp-history-search').value = historySearch; $('tp-history-family').value = historyFamily; $('tp-history-state').value = historyState;
    const filter = () => { historySearch = $('tp-history-search').value; historyFamily = $('tp-history-family').value; historyState = $('tp-history-state').value; offset = 0; historySignature = ''; refresh(); };
    $('tp-history-search').oninput = () => { clearTimeout(filterTimer); filterTimer = screen.timeout(filter, 250); };
    $('tp-history-family').onchange = filter; $('tp-history-state').onchange = filter;
    $('tp-history-prev').onclick = () => { offset = Math.max(0, offset - 50); refresh(); };
    $('tp-history-next').onclick = () => { offset += 50; refresh(); };
    $('tp-history-list').onclick = historyAction;
    $('tp-new-run').onclick = () => { preferSetup = true; tpDismissedRunId = selected; if (tpLastData) renderTpResult(tpLastData); $('tp-setup').hidden = false; $('tp-setup').scrollIntoView({block:'start'}); };
    $('tp-queue-pause').onclick = async () => {
      try { await api(screen, '/queue', {paused: !paused}); refresh(); }
      catch (error) { if (!screen.active) return; showTpError(error.message || String(error)); }
    };
    $('tp-compare-reset').onclick = async () => {
      if (!current || !confirm('Check ComfyUI for an earlier result before resetting. The ComfyUI queue must be empty.')) return;
      try { await api(screen, `/runs/${current.id}/comparison/reset`, {}); comparisonError = ''; refresh(); }
      catch (error) { if (!screen.active) return; comparisonError = error.message || String(error); $('tp-compare-status').textContent = comparisonError; }
    };
    $('tp-compare-generate').onclick = () => compare(false);
    $('tp-compare-open').onclick = () => compare(true);
    $('tp-copy-loras').onclick = () => publish('copy');
    try {
      const config = await screen.json('/api/trainpilot/toml');
      if (!screen.active || !$('tp-page')) return;
      $('tp-toml').value = config.path;
      $('toml-config-path').textContent = config.path;
    } catch (error) { if (!screen.active) return; if (screen.active) showTpError(`SDXL configuration unavailable: ${error.message || error}`); }
    if (screen.active && $('tp-page')) { preflight(); refresh(); }
  }
  function stop() { trainingScreen?.dispose(); clearTimeout(filterTimer); preparation = null; }
  return {init, stop, spec, preflight, submit, stopRun, publish};
})();
