/* One read-only report for Datasets and the training handoff. */
window.reviewDataset = async function (name, owner, beforeTraining = false) {
  const screen = owner.latest('dataset-review');
  const dialog = document.createElement('dialog'); dialog.className = 'modal show dataset-quality-dialog';
  dialog.setAttribute('aria-label', 'Dataset quality review');
  const card = document.createElement('div'); card.className = 'modal-card'; card.dataset.size = 'lg';
  const body = document.createElement('div'); body.className = 'modal-body';
  const title = document.createElement('h3'); title.textContent = 'Dataset quality review';
  const status = document.createElement('p'); status.setAttribute('role', 'status'); status.textContent = 'Checking images and captions…';
  const results = document.createElement('div'); results.className = 'dataset-quality-results';
  const actions = document.createElement('div'); actions.className = 'modal-actions';
  const close = document.createElement('button'); close.className = 'btn ghost'; close.textContent = beforeTraining ? 'Back to setup' : 'Close';
  const proceed = document.createElement('button'); proceed.className = 'btn primary'; proceed.textContent = 'Continue to training'; proceed.disabled = true;
  body.append(title, status, results); actions.append(close); if (beforeTraining) actions.append(proceed);
  card.append(body, actions); dialog.append(card); document.body.append(dialog); dialog.showModal();
  let finish;
  const answer = new Promise(resolve => { finish = resolve; });
  const end = value => { dialog.close(); dialog.remove(); finish(value); screen.dispose(); };
  const unlink = screen.onCleanup(() => end(false));
  close.onclick = () => { unlink(); end(false); };
  proceed.onclick = () => { unlink(); end(true); };
  dialog.addEventListener('cancel', event => { event.preventDefault(); close.click(); });
  try {
    const data = await screen.json(`/api/datasets/${encodeURIComponent(name)}/quality`);
    status.textContent = `${data.images} images checked · ${data.findings.length} findings${data.complete ? '' : ' · Review incomplete (size or time limit)'}. Your files have not been changed.`;
    if (!data.findings.length && data.complete) status.textContent = `${data.images} images checked. No issues found. Your files have not been changed.`;
    for (const item of data.findings) {
      const row = document.createElement('p');
      const file = document.createElement('strong'); file.textContent = item.file;
      row.append(file, document.createTextNode(` — ${item.message} `));
      if (/\.(png|jpe?g|webp|bmp)$/i.test(item.file) && !['unsafe','unreadable','unchecked'].includes(item.kind)) {
        const link = document.createElement('a'); link.className = 'journey-link'; link.textContent = 'View image'; link.target = '_blank'; link.rel = 'noopener';
        link.href = `/api/datasets/${encodeURIComponent(name)}/preview?file=${encodeURIComponent(item.file)}`; row.append(link);
        const edit = document.createElement('button'); edit.className = 'journey-link'; edit.textContent = 'Open in Caption images';
        edit.onclick = () => { close.click(); openTagpilotDataset(name, item.file); }; row.append(document.createTextNode(' · '), edit);
      }
      results.append(row);
    }
    const edit = document.createElement('button'); edit.className = 'btn ghost'; edit.textContent = 'Review in Caption images';
    edit.onclick = () => { close.click(); openTagpilotDataset(name); }; actions.prepend(edit);
    proceed.disabled = !data.images || !!data.counts.unsafe || !!data.counts.unreadable;
  } catch (error) {
    if (screen.active) status.textContent = `Review unavailable: ${error.message || error}`;
  }
  return answer;
};
