window.initTagpilot = function () {
  const iframe = document.querySelector("iframe[src^=\"/tagpilot\"]");
  if (!iframe) return;
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
