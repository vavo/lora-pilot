window.initDocs = async function () {
  const status = document.getElementById("docs-status");
  const content = document.getElementById("docs-content");
  if (!status || !content) return;
  status.textContent = "Loading docs...";
  content.style.display = "none";
  try {
    const data = await fetchJson("/api/docs");
    content.textContent = data.content || "No docs found.";
    status.textContent = "";
    content.style.display = "";
  } catch (e) {
    status.textContent = `Error: ${e.message || e}`;
  }
};
