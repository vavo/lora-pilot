window.initMediapilot = async function () {
  const statusEl = document.getElementById("mediapilot-status");
  const iframe = document.getElementById("mediapilot-iframe");
  if (!statusEl || !iframe) return;
  const targetSrc = iframe.dataset.src || "/mediapilot/";

  statusEl.style.display = "none";
  iframe.style.display = "none";
  iframe.src = "about:blank";

  try {
    const res = await fetch("/api/mediapilot/status", { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const status = await res.json();
    if (!status.available) {
      statusEl.style.display = "block";
      statusEl.textContent = `MediaPilot is not available. ${status.error || ""}`.trim();
      return;
    }
    iframe.src = targetSrc;
    iframe.style.display = "";
  } catch (err) {
    statusEl.style.display = "block";
    statusEl.textContent = `MediaPilot status check failed: ${err?.message || err}`;
  }
};
