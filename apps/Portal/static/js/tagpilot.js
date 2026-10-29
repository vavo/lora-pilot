window.initTagpilot = function (screen) {
  const iframe = document.querySelector("iframe[src^=\"/tagpilot\"]");
  if (!iframe) return;
  const handoff = event => {
    if (event.origin !== window.location.origin || event.source !== iframe.contentWindow || !screen.active) return;
    if (event.data?.type === 'tagpilot:train' && typeof event.data.dataset === 'string') {
      window.pendingTrainDataset = event.data.dataset;
      window.loadSection('trainpilot');
    }
  };
  window.addEventListener('message', handoff);
  screen.onCleanup(() => window.removeEventListener('message', handoff));
  const ds = window.pendingTagDataset;
  if (ds) {
    const params = new URLSearchParams({dataset:ds});
    if (window.pendingTagImage) params.set('image', window.pendingTagImage);
    if (window.pendingTagTrigger) params.set('trigger', window.pendingTagTrigger);
    iframe.src = `/tagpilot/?${params}`;
    window.pendingTagDataset = null;
    window.pendingTagImage = null;
    window.pendingTagTrigger = null;
  }
};
