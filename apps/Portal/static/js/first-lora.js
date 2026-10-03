/* The guide follows real dataset/run state and reuses the existing screens. */
window.firstLora = (() => {
  let current = null;
  function init(screen) {
    const host = document.getElementById('first-lora-guide');
    if (!host) return;
    const details = document.createElement('details'); details.className = 'tp-disclosure';
    const summary = document.createElement('summary'); summary.textContent = 'Your first LoRA · meet the orange robot';
    const body = document.createElement('div'); body.className = 'first-lora-body';
    const image = document.createElement('img'); image.src = '/api/training/first-lora/preview'; image.alt = 'Orange robot sample from the LoRA Pilot videos';
    const content = document.createElement('div');
    const copy = document.createElement('p'); copy.className = 'journey-note';
    copy.textContent = 'Try the eight robot images from our videos. Review captions, train a quick test, then compare your checkpoints.';
    const steps = document.createElement('p'); steps.className = 'journey-note';
    const progress = document.createElement('progress'); progress.max = 4; progress.setAttribute('aria-label', 'First LoRA progress');
    const status = document.createElement('p'); status.className = 'journey-note'; status.setAttribute('role', 'status');
    const actions = document.createElement('div'); actions.className = 'row wrap gap-12';
    const action = document.createElement('button'); action.className = 'btn ghost'; action.type = 'button';
    const reviewed = document.createElement('button'); reviewed.className = 'journey-link'; reviewed.type = 'button'; reviewed.textContent = 'I reviewed the captions'; reviewed.hidden = true;
    const note = document.createElement('p'); note.className = 'journey-note'; note.textContent = 'Sample inputs, not trained results. Trigger word: pilotceramic.';
    actions.append(action, reviewed); content.append(copy, steps, progress, status, actions, note); body.append(image, content); details.append(summary, body); host.replaceChildren(details);
    let busy = false;
    function render(data) {
      current = data;
      const done = [!!data.dataset, data.reviewed, data.trained, data.compared];
      progress.value = done.filter(Boolean).length;
      const next = done.indexOf(false);
      steps.textContent = ['Images', 'Captions', 'Training', 'Comparison'].map((label, index) => `${label}: ${done[index] ? 'done' : index === next ? 'next' : 'later'}`).join(' · ');
      reviewed.hidden = !data.dataset || data.reviewed;
      action.disabled = busy;
      action.textContent = !data.dataset ? 'Use orange robot dataset' : !data.reviewed ? 'Review captions'
        : data.run_id ? data.compared ? 'Open your result' : data.trained ? 'Compare checkpoints' : 'View training run' : 'Set up quick training';
      status.textContent = data.run_status && !data.trained ? `Training: ${data.run_status}` : data.compared ? 'Your first experiment is ready to explore or export.' : '';
    }
    async function load() {
      if (busy) return;
      const request = screen.latest('first-lora');
      try { render(await request.json('/api/training/first-lora')); }
      catch (error) { if (request.active) { status.textContent = `Guide unavailable: ${error.message || error}`; action.disabled = true; } }
    }
    async function change(path) {
      busy = true; action.disabled = true; reviewed.disabled = true;
      const request = screen.latest('first-lora');
      try {
        render(await request.json('/api/training/first-lora/' + path, {method:'POST'}));
        if (document.getElementById('ds-list')) await loadDatasets();
      } catch (error) { if (request.active) status.textContent = error.message || String(error); }
      finally { if (screen.active) { busy = false; action.disabled = false; reviewed.disabled = false; } }
    }
    action.onclick = async () => {
      if (!current || busy) return;
      if (!current.dataset) { await change('install'); return; }
      if (!current.reviewed) { openTagpilotDataset(current.dataset); return; }
      if (current.run_id) window.pendingTrainingRun = current.run_id;
      else { window.pendingTrainDataset = current.dataset; window.pendingFirstLora = {...current}; }
      window.loadSection('trainpilot');
    };
    reviewed.onclick = () => change('reviewed');
    const loaded = load();
    screen.timeout(() => screen.poll(load, 8000), 8000);
    return loaded;
  }
  return {init, get current() { return current; }};
})();
