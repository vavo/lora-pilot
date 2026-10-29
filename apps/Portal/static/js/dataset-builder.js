/* Dataset creation stays on the backend when the user leaves this screen. */
window.initDatasetBuilder = function (screen) {
  const root = document.getElementById('dataset-builder');
  if (!root) return;
  const el = id => document.getElementById('db-' + id);
  const api = '/api/dataset-builder';
  const running = job => ['generating_reference', 'generating', 'checking', 'pausing'].includes(job?.status);
  let selected = null, busy = false, ready = false;
  const drafts = new Map();
  const error = message => { if (screen.active) el('error').textContent = message; };
  const imageUrl = (job, file) => `${api}/jobs/${job.id}/images/${encodeURIComponent(file)}`;

  function controls() {
    el('create').disabled = busy || !ready || running(selected);
    el('jobs').disabled = busy;
    const complete = selected?.items.length === selected?.spec.count && selected?.items.every(x => x.accepted && x.caption && x.review);
    const unsaved = selected?.items.some(item => drafts.has(`${selected.id}/${item.slot}`));
    el('finish').disabled = busy || !complete || unsaved || !el('reviewed').checked;
    if (selected) el('accepted').textContent = `${selected.accepted_count} of ${selected.spec.count} images kept. ` +
      (unsaved ? 'Save your edited captions before continuing.' : 'All requested images need a caption before saving.');
    el('pause').disabled = busy;
    el('resume').disabled = busy;
  }

  async function action(callback) {
    if (busy) return;
    busy = true; error(''); controls();
    root.querySelectorAll('[data-db-action]').forEach(button => { button.disabled = true; });
    try { await callback(); }
    catch (exc) { if (screen.active) error(exc.message || String(exc)); }
    finally { if (screen.active) { busy = false; if (selected) render(selected); controls(); } }
  }

  async function check() {
    const request = screen.latest('builder-preflight');
    ready = false; controls(); el('preflight').textContent = 'Checking models and ComfyUI…';
    try {
      const result = await request.json(`${api}/preflight?source=${el('source').value}`);
      if (!request.active) return;
      ready = result.ready;
      el('preflight').textContent = ready ? 'Models and ComfyUI are ready. Captioning and consistency checks run locally.' : result.problems.join(' ');
    } catch (exc) { if (request.active) el('preflight').textContent = exc.message; }
    if (request.active) controls();
  }

  function sourceChanged() {
    const photo = el('source').value === 'photo';
    el('prompt-label').hidden = photo; el('prompt').required = !photo;
    el('photo-label').hidden = !photo; el('photo').required = photo;
    el('create').textContent = photo ? 'Use this photo' : 'Create reference';
    void check();
  }

  function button(label, callback, disabled = false) {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'btn ghost'; button.textContent = label;
    button.dataset.dbAction = ''; button.disabled = disabled || busy;
    button.onclick = () => action(callback);
    return button;
  }

  async function post(suffix, body) {
    return screen.json(`${api}/jobs/${selected.id}/${suffix}`, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body || {})
    });
  }

  function render(job) {
    selected = job;
    el('job').hidden = false;
    el('job-title').textContent = job.spec.name;
    el('progress').textContent = job.message;
    const active = running(job), saved = job.status === 'saved';
    const option = Array.from(el('jobs').options).find(option => option.value === job.id);
    if (option) option.textContent = `${job.spec.name} · ${job.status.replaceAll('_', ' ')}`;
    el('pause').hidden = !active;
    el('resume').hidden = active || saved || job.status === 'reference_review';
    el('reference').replaceChildren(); el('images').replaceChildren();
    el('finish-wrap').hidden = job.phase !== 'variations' || active || saved;
    el('train').hidden = !saved;
    const references = job.reference ? [job.reference] : job.references;
    for (const file of references) {
      const card = document.createElement('figure');
      const img = document.createElement('img'); img.src = imageUrl(job, file); img.alt = 'Identity reference';
      const caption = document.createElement('figcaption'); caption.textContent = job.reference ? 'Approved reference' : 'Reference candidate';
      card.append(img, caption);
      if (!job.reference) card.append(button('Use this reference', async () => {
        selected = await post('reference', {file}); el('reviewed').checked = false;
      }, active || !!job.pending));
      el('reference').append(card);
    }
    for (const item of job.items) {
      if (!item.file) continue;
      const card = document.createElement('article'); card.className = 'db-image';
      const heading = document.createElement('h4'); heading.textContent = `${item.slot + 1}. ${item.shot}`;
      const link = document.createElement('a'); link.href = imageUrl(job, item.file); link.target = '_blank'; link.rel = 'noopener';
      const img = document.createElement('img'); img.src = link.href; img.alt = item.shot; img.loading = 'lazy'; link.append(img);
      const state = document.createElement('p'); state.className = 'journey-note';
      state.textContent = (item.accepted ? 'Kept' : item.review ? 'Needs your review' : 'Waiting for local captioning and checks') +
        ` · ${item.attempts}/3 attempts used`;
      const warnings = document.createElement('ul');
      for (const warning of item.warnings || []) { const li = document.createElement('li'); li.textContent = warning; warnings.append(li); }
      const label = document.createElement('label'); label.textContent = 'Caption';
      const caption = document.createElement('textarea'); caption.className = 'input'; caption.rows = 4;
      const draftKey = `${job.id}/${item.slot}`;
      caption.maxLength = 2000; caption.value = drafts.get(draftKey) ?? item.caption ?? ''; caption.disabled = active || saved || !item.review;
      caption.addEventListener('input', () => { drafts.set(draftKey, caption.value); el('reviewed').checked = false; controls(); });
      label.append(caption);
      const actions = document.createElement('div'); actions.className = 'row wrap gap-8';
      const update = async accepted => {
        selected = await screen.json(`${api}/jobs/${job.id}/images/${item.slot}`, {
          method: 'PATCH', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({accepted, caption: caption.value.trim()})
        });
        drafts.delete(draftKey);
        el('reviewed').checked = false;
      };
      actions.append(button(item.accepted ? 'Save caption' : 'Keep image & caption', () => update(true), active || saved || !item.review),
                     button('Exclude', () => update(false), active || saved || !item.review || !item.accepted),
                     button('Regenerate', async () => { selected = await post(`images/${item.slot}/regenerate`); drafts.delete(draftKey); el('reviewed').checked = false; }, active || saved || !item.review || item.attempts >= 3));
      card.append(heading, link, state, warnings, label, actions); el('images').append(card);
    }
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
    if (!root.hidden) { sourceChanged(); void action(listJobs); }
  };
  el('source').onchange = sourceChanged;
  el('goal').onchange = () => {
    const fixed = el('goal').value === 'character';
    el('clothes').disabled = fixed; el('hair').disabled = fixed;
    if (fixed) { el('clothes').checked = false; el('hair').checked = false; }
  };
  el('recheck').onclick = check;
  el('models').onclick = event => { event.preventDefault(); window.loadSection('models'); };
  el('form').onsubmit = event => {
    event.preventDefault();
    void action(async () => {
      const body = new FormData();
      body.append('spec', JSON.stringify({name: el('name').value, trigger: el('trigger').value,
        count: Number(el('count').value), source: el('source').value, prompt: el('prompt').value,
        goal: el('goal').value, vary_clothes: el('clothes').checked, vary_hair: el('hair').checked}));
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
  el('reviewed').onchange = controls;
  el('finish').onclick = () => action(async () => { selected = await post('finish'); openTrainingDataset(selected.dataset); });
  el('train').onclick = () => openTrainingDataset(selected.dataset);
  screen.poll(async () => {
    if (!selected || !running(selected) || busy || root.hidden) return;
    const jobId = selected.id;
    const updated = await screen.json(`${api}/jobs/${jobId}`);
    if (selected?.id === jobId && !busy) render(updated);
  }, 3000);
};
