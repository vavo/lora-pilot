window.initSupport = function () {
  // Dynamically inject BuyMeACoffee script (scripts inside injected HTML don't execute automatically)
  const container = document.getElementById("bmc-container");
  if (container && !container.dataset.loaded) {
    const script = document.createElement("script");
    script.type = "text/javascript";
    script.src = "https://cdnjs.buymeacoffee.com/1.0.0/button.prod.min.js";
    script.setAttribute("data-name", "bmc-button");
    script.setAttribute("data-slug", "vavo");
    script.setAttribute("data-color", "#5F7FFF");
    script.setAttribute("data-emoji", "💻");
    script.setAttribute("data-font", "Cookie");
    script.setAttribute("data-text", "buy me Docker subscription");
    script.setAttribute("data-outline-color", "#000000");
    script.setAttribute("data-font-color", "#ffffff");
    script.setAttribute("data-coffee-color", "#FFDD00");
    container.appendChild(script);
    container.dataset.loaded = "1";
  }
};
