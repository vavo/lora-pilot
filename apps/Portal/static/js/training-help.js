const TRAINING_HELP_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"></circle><path d="M12 10.5v5"></path><circle cx="12" cy="7.5" r=".7" fill="currentColor" stroke="none"></circle></svg>';

window.initTrainingHelp = function (root = document) {
  root.querySelectorAll("[data-help]").forEach(target => {
    if (target.querySelector(":scope > .field-help")) return;
    const message = target.dataset.help?.trim();
    if (!message) return;
    const label = target.textContent.trim();
    const button = document.createElement("button");
    button.type = "button";
    button.className = "field-help";
    button.setAttribute("aria-label", `More about ${label}`);
    button.dataset.tooltip = message;
    button.innerHTML = TRAINING_HELP_ICON;
    button.addEventListener("click", event => event.preventDefault());
    target.append(" ", button);
  });
};
