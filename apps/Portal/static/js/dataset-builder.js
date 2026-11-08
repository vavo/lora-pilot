/* Dataset creation stays on the backend when the user leaves this screen. */
window.initDatasetBuilder = function (screen) {
  const root = document.getElementById('dataset-builder');
  if (!root) return;
  const el = id => document.getElementById('db-' + id);
  const api = '/api/dataset-builder';
  const running = job => ['preparing', 'generating_reference', 'generating', 'checking', 'pausing'].includes(job?.status);
  let selected = null, busy = false, planReady = false, comparisonSlot = null;
  const error = message => { if (screen.active) {
    el('error').textContent = message; el('compare-error').textContent = message;
  } };
  const imageUrl = (job, file) => `${api}/jobs/${job.id}/images/${encodeURIComponent(file)}`;

  function controls() {
    el('create').disabled = busy || !planReady || running(selected);
    el('jobs').disabled = busy;
    const kept = selected?.items.filter(x => x.file && x.accepted && (x.review || x.user_reviewed)).length || 0;
    el('finish').disabled = busy || !kept || !el('reviewed').checked || !!selected?.finish_requested;
    el('finish').textContent = `${running(selected) ? 'Stop & save' : 'Save'} ${kept} kept image${kept === 1 ? '' : 's'} to TagPilot`;
    if (selected) el('accepted').textContent = `${selected.accepted_count} of ${selected.spec.count} images kept. ` +
      'Only kept images will be saved. Caption and tag them in TagPilot.';
    el('pause').disabled = busy;
    el('resume').disabled = busy;
    el('approve-trial').disabled = busy || running(selected) || !!selected?.pending || !!selected?.regenerate_slots?.length ||
      selected?.items.slice(0, 3).length !== 3 || !selected?.items.slice(0, 3).every(x => x.file && x.accepted);
  }

  async function action(callback) {
    if (busy) return;
    busy = true; error(''); controls();
    root.querySelectorAll('[data-db-action]').forEach(button => { button.disabled = true; });
    try { await callback(); }
    catch (exc) { if (screen.active) error(exc.message || String(exc)); }
    finally { if (screen.active) { busy = false; if (selected) render(selected); controls(); } }
  }

  async function showPlan() {
    const request = screen.latest('builder-plan');
    planReady = false; controls();
    el('plan').textContent = 'Updating the planned image mix…';
    const params = new URLSearchParams({count: el('count').value, goal: el('goal').value,
      subject: el('subject').value, vary_clothes: el('clothes').checked, vary_hair: el('hair').checked});
    try {
      const plan = await request.json(`${api}/plan?${params}`);
      if (!request.active) return;
      const framing = Object.entries(plan.framing).map(([label, count]) => `${count} × ${label}`).join(' · ');
      const angles = Object.keys(plan.angles).join(', ');
      el('plan').textContent = `${plan.count} images: ${framing}. Views: ${angles}. ` +
        (plan.subject === 'character' ? 'Keep the same character design, materials and colours.' :
        (plan.vary_clothes ? 'Vary clothes. ' : 'Keep reference clothes. ') +
        (plan.vary_hair ? 'Include hairstyle changes.' : 'Keep reference hairstyle.')) +
        ' Start with three trial images.';
      planReady = true;
    } catch (exc) { if (request.active) el('plan').textContent = 'The image plan could not load. Select an image count to retry.'; }
    if (request.active) controls();
  }

  function sourceChanged() {
    const photo = el('source').value === 'photo';
    el('prompt-label').hidden = photo; el('prompt').required = !photo;
    el('photo-label').hidden = !photo; el('photo').required = photo;
    el('style-label').hidden = photo;
    el('create').textContent = photo ? 'Use this photo' : 'Create reference';
  }

  function button(label, callback, disabled = false, reason = '') {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'btn ghost'; button.textContent = label;
    button.dataset.dbAction = ''; button.disabled = disabled || busy;
    if (reason) button.title = reason;
    button.onclick = () => action(callback);
    return button;
  }

  async function post(suffix, body) {
    return screen.json(`${api}/jobs/${selected.id}/${suffix}`, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body || {})
    });
  }

  function friendlyWarning(warning) {
    if (warning.startsWith('Identity uncertain:')) return 'The subject could not be matched confidently. Compare with your reference before keeping.';
    if (warning.startsWith('Identity different:') || warning.startsWith('Identity inconsistent:')) return 'The subject may look different from your reference. Check its defining features.';
    return warning;
  }

  function imageActions(job, item) {
    const saved = job.status === 'saved', queued = job.regenerate_slots?.includes(item.slot);
    const changing = job.busy_slot === item.slot;
    const reason = saved ? 'This dataset is already saved.' : changing ? 'Waiting for this image to be regenerated.' : '';
    const update = async accepted => {
      if (saved || changing || job.finish_requested) throw new Error(reason || 'Saving your selection. Please wait.');
      const unchecked = !item.review || !!item.warnings?.length;
      if (accepted && unchecked && !window.confirm('Automatic checks are unavailable or raised concerns. Compare this image with your reference. Keep it anyway?')) return;
      selected = await screen.json(`${api}/jobs/${job.id}/images/${item.slot}`, {
        method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({accepted, file: item.file, confirm_unchecked: accepted && unchecked})
      });
      el('reviewed').checked = false;
    };
    return [button('Keep image', () => update(true), false, reason || (item.accepted ? 'Already kept. You can exclude it if you change your mind.' : '')),
      button('Exclude', () => update(false), false, reason || (item.user_reviewed && !item.accepted ? 'Already excluded. You can keep it if you change your mind.' : '')),
      button(queued ? 'Regeneration queued' : 'Regenerate', async () => {
        if (saved || changing || job.finish_requested) throw new Error(reason || 'Saving your selection. Please wait.');
        if (queued) throw new Error('Regeneration is already queued. Keep or exclude this image to cancel the queued replacement.');
        if (item.attempts >= 3) throw new Error('Three attempts used for this image. Keep it, exclude it, or start a new dataset.');
        selected = await post(`images/${item.slot}/regenerate`, {file: item.file}); el('reviewed').checked = false;
      }, false, reason || 'Uses one generation attempt. Queued safely if another image is running.')];
  }

  function renderComparison() {
    const item = selected?.items.find(item => item.slot === comparisonSlot);
    if (!item?.file || !selected.reference) return;
    const available = selected.items.filter(item => item.file);
    const index = available.findIndex(item => item.slot === comparisonSlot);
    el('compare-position').textContent = `${index + 1} of ${available.length}`;
    el('compare-prev').disabled = index <= 0;
    el('compare-next').disabled = index >= available.length - 1;
    el('compare-reference').src = imageUrl(selected, selected.reference);
    el('compare-image').src = imageUrl(selected, item.file);
    el('compare-shot').textContent = `${item.slot + 1}. ${item.shot}`;
    el('compare-state').textContent = (item.accepted ? 'Kept for training. ' : 'Not kept yet. ') +
      (item.review ? 'Your decision matters more than the automatic check.' : 'Automatic checks are not available yet. You can still decide.');
    el('compare-warnings').replaceChildren();
    for (const warning of item.warnings || []) {
      const li = document.createElement('li'); li.textContent = friendlyWarning(warning); el('compare-warnings').append(li);
    }
    const restoreFocus = el('compare-actions').contains(document.activeElement);
    el('compare-actions').replaceChildren(...imageActions(selected, item));
    if (restoreFocus) el('compare-close').focus();
  }

  function render(job) {
    selected = job;
    el('job').hidden = false;
    el('job-title').textContent = job.spec.name;
    el('progress').textContent = job.message;
    el('job-summary').textContent = `${job.spec.subject === 'character' ? 'Non-human character' : 'Person'} · ${job.spec.count} images · ${job.spec.source === 'photo' ? 'Uploaded reference' : (job.spec.style === 'illustration' ? 'Illustration reference' : 'Photo reference')}`;
    const active = running(job), saved = job.status === 'saved';
    root.querySelectorAll('[data-prepare-step]').forEach(step => {
      if (step.dataset.prepareStep === (job.reference ? '2' : '1')) step.setAttribute('aria-current', 'step');
      else step.removeAttribute('aria-current');
    });
    const option = Array.from(el('jobs').options).find(option => option.value === job.id);
    if (option) option.textContent = `${job.spec.name} · ${job.status.replaceAll('_', ' ')}`;
    el('pause').hidden = !active;
    el('pause').textContent = job.phase === 'setup' ? 'Pause setup' : 'Pause after current image';
    el('resume').hidden = active || saved || ['reference_review', 'trial_review', 'review'].includes(job.status);
    el('trial-wrap').hidden = job.trial_approved !== false || !job.items.some(x => x.file) || saved;
    el('reference').replaceChildren(); el('images').replaceChildren();
    el('finish-wrap').hidden = job.phase !== 'variations' || !job.items.some(x => x.file) || saved;
    el('train').hidden = !saved;
    const references = job.reference ? [job.reference] : job.references;
    for (const file of references) {
      const card = document.createElement('figure');
      const img = document.createElement('img'); img.src = imageUrl(job, file); img.alt = 'Identity reference';
      const caption = document.createElement('figcaption'); caption.textContent = job.reference ? 'Approved reference' : 'Reference candidate';
      card.append(img, caption);
      if (!job.reference) card.append(button('Use this reference', async () => {
        selected = await post('reference', {file}); el('reviewed').checked = false;
      }, active || job.phase !== 'reference' || !!job.pending));
      el('reference').append(card);
    }
    for (const item of job.items) {
      if (!item.file) continue;
      const card = document.createElement('article'); card.className = 'db-image';
      const heading = document.createElement('h4'); heading.textContent = `${item.slot + 1}. ${item.shot}`;
      const link = document.createElement('a'); link.href = imageUrl(job, item.file); link.target = '_blank'; link.rel = 'noopener';
      const img = document.createElement('img'); img.src = link.href; img.alt = item.shot; img.loading = 'lazy'; link.append(img);
      const state = document.createElement('p'); state.className = 'journey-note';
      state.textContent = (item.accepted ? 'Kept' : item.user_reviewed ? 'Excluded' : 'Ready for your review') +
        ` · ${item.attempts}/3 attempts used`;
      if (job.regenerate_slots?.includes(item.slot) || job.busy_slot === item.slot) state.textContent += ' · Regeneration queued or running';
      else if (!item.review) state.textContent += ' · Automatic checks pending or unavailable';
      const warnings = document.createElement('ul');
      for (const warning of item.warnings || []) { const li = document.createElement('li'); li.textContent = friendlyWarning(warning); warnings.append(li); }
      const actions = document.createElement('div'); actions.className = 'row wrap gap-8';
      const compare = button('Compare with reference', () => {}, !job.reference);
      compare.dataset.compareSlot = item.slot;
      compare.onclick = () => { comparisonSlot = item.slot; renderComparison(); el('compare').showModal(); };
      actions.append(compare, ...imageActions(job, item));
      card.append(heading, link, state, warnings, actions); el('images').append(card);
    }
    if (el('compare').open) renderComparison();
    controls();
  }

  async function listJobs() {
    const jobs = await screen.json(`${api}/jobs`);
    el('jobs').replaceChildren(new Option('Choose a job', ''));
    for (const job of jobs) el('jobs').append(new Option(`${job.spec.name} · ${job.status.replaceAll('_', ' ')}`, job.id));
    el('jobs-label').hidden = !jobs.length;
    if (!selected && jobs.length) { render(jobs[0]); el('jobs').value = jobs[0].id; }
  }

  el('open').onclick = () => {
    root.hidden = !root.hidden; el('open').setAttribute('aria-expanded', String(!root.hidden));
    if (!root.hidden) { el('name').focus(); sourceChanged(); void showPlan(); void action(listJobs); }
  };
  el('source').onchange = sourceChanged;
  function subjectChanged() {
    const character = el('subject').value === 'character';
    const fixed = character || el('goal').value === 'character';
    el('goal-label').hidden = character; el('options').hidden = character;
    el('clothes').disabled = fixed; el('hair').disabled = fixed;
    if (fixed) { el('clothes').checked = false; el('hair').checked = false; }
    void showPlan();
  }
  el('goal').onchange = subjectChanged;
  el('subject').onchange = subjectChanged;
  for (const name of ['count', 'clothes', 'hair']) el(name).onchange = showPlan;

  el('form').onsubmit = event => {
    event.preventDefault();
    void action(async () => {
      const body = new FormData();
      body.append('spec', JSON.stringify({name: el('name').value, trigger: el('trigger').value,
        count: Number(el('count').value), source: el('source').value, prompt: el('prompt').value,
        goal: el('goal').value, subject: el('subject').value, style: el('style').value,
        vary_clothes: el('clothes').checked, vary_hair: el('hair').checked}));
      if (el('source').value === 'photo') {
        const file = el('photo').files[0];
        if (!file || file.size > 32 * 1024 * 1024) throw new Error('Choose a photo smaller than 32 MB.');
        body.append('photo', file);
      }
      selected = await screen.json(`${api}/jobs`, {method: 'POST', body});
      el('reviewed').checked = false; await listJobs(); el('jobs').value = selected.id;
    });
  };
  el('jobs').onchange = () => { if (el('jobs').value) void action(async () => {
    selected = await screen.json(`${api}/jobs/${el('jobs').value}`); el('reviewed').checked = false;
  }); };
  el('pause').onclick = () => action(async () => { const result = await post('pause'); selected.message = result.message; });
  el('resume').onclick = () => action(async () => { selected = await post('resume'); el('reviewed').checked = false; });
  el('approve-trial').onclick = () => action(async () => { selected = await post('approve-trial'); el('reviewed').checked = false; });
  el('reviewed').onchange = controls;
  el('finish').onclick = () => action(async () => {
    selected = await post('finish', {files: selected.items.filter(x => x.file && x.accepted).map(x => x.file)});
    if (selected.status === 'saved') openTagpilotDataset(selected.dataset);
  });
  el('train').onclick = () => openTagpilotDataset(selected.dataset);
  el('compare-close').onclick = () => el('compare').close();
  function moveComparison(offset) {
    const images = selected?.items.filter(item => item.file) || [];
    const index = images.findIndex(item => item.slot === comparisonSlot);
    const next = images[index + offset];
    if (next) { comparisonSlot = next.slot; error(''); renderComparison(); }
  }
  el('compare-prev').onclick = () => moveComparison(-1);
  el('compare-next').onclick = () => moveComparison(1);
  el('compare').onkeydown = event => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault(); moveComparison(event.key === 'ArrowLeft' ? -1 : 1);
    }
  };
  el('compare').onclick = event => { if (event.target === el('compare')) el('compare').close(); };
  el('compare').onclose = () => {
    el('images').querySelector(`[data-compare-slot="${comparisonSlot}"]`)?.focus();
    comparisonSlot = null;
  };
  screen.onCleanup(() => { if (el('compare').open) el('compare').close(); });
  screen.poll(async () => {
    if (!selected || !running(selected) || busy || root.hidden) return;
    const jobId = selected.id;
    const updated = await screen.json(`${api}/jobs/${jobId}`);
    if (selected?.id === jobId && !busy) {
      const saving = selected.finish_requested;
      const keptFiles = job => job.items.filter(x => x.accepted).map(x => x.file).join('|');
      if (keptFiles(selected) !== keptFiles(updated)) el('reviewed').checked = false;
      render(updated);
      if (saving && updated.status === 'saved') openTagpilotDataset(updated.dataset);
    }
  }, 3000);
};
