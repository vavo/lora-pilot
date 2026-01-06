window.initTagpilot = function () {
  const iframe = document.querySelector("iframe[src^=\"/tagpilot\"]");
  if (!iframe) return;
  const ds = window.pendingTagDataset;
  if (ds) {
    iframe.src = `/tagpilot/?dataset=${encodeURIComponent(ds)}`;
    window.pendingTagDataset = null;
  }
};
