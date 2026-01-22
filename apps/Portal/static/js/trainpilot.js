let tpLogTimer = null;

window.initTrainpilot = function () {
  bindTpControls();
  loadTpDatasets();
  startTpLogPoll();
};

function bindTpControls() {
  const status = document.getElementById("tp-status");
  if (status) status.textContent = "";
}

async function loadTpDatasets() {
  const sel = document.getElementById("tp-dataset");
  const status = document.getElementById("tp-status");
  if (!sel) return;
  sel.innerHTML = `<option>Loading datasets...</option>`;
  try {
    const data = await fetchJson("/api/datasets");
    sel.innerHTML = "";
    if (!data.length) {
      sel.innerHTML = `<option value="">No datasets found</option>`;
      return;
    }
    data.forEach(d => {
      const label = `${d.display || d.name} (${d.images || 0} images)`;
      const val = d.path || d.name;
      const opt = document.createElement("option");
      opt.value = val;
      opt.textContent = label;
      sel.appendChild(opt);
    });
    // Pre-fill output with selected dataset name (friendly)
    if (sel.options.length) {
      const firstVal = sel.options[0].textContent || "";
      autoFillOutput(firstVal);
      sel.addEventListener("change", () => {
        const txt = sel.options[sel.selectedIndex]?.textContent || "";
        autoFillOutput(txt);
      });
    }
  } catch (e) {
    if (status) status.textContent = `Error loading datasets: ${e.message || e}`;
  }
}

window.openDatasets = function (evt) {
  if (evt) evt.preventDefault();
  if (window.loadSection) {
    window.loadSection("datasets");
  } else {
    window.location.href = "/#datasets";
  }
};

window.startTrainPilot = async function () {
  const dataset = document.getElementById("tp-dataset")?.value.trim() || "";
  const output = document.getElementById("tp-output")?.value.trim() || "";
  const profile = document.getElementById("tp-profile")?.value || "regular";
  const toml = document.getElementById("tp-toml")?.value.trim() || "";
  const status = document.getElementById("tp-status");
  if (status) status.textContent = "Starting...";
  try {
    await fetchJson("/api/trainpilot/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset_name: dataset,
        output_name: output,
        profile,
        toml_path: toml,
      }),
    });
    if (status) status.textContent = "Running...";
  } catch (e) {
    if (status) status.textContent = `Error: ${e.message || e}`;
  }
};

window.stopTrainPilot = async function () {
  const status = document.getElementById("tp-status");
  if (status) status.textContent = "Stopping...";
  try {
    await fetchJson("/api/trainpilot/stop", { method: "POST" });
    if (status) status.textContent = "Stopped.";
  } catch (e) {
    if (status) status.textContent = `Error: ${e.message || e}`;
  }
};

function startTpLogPoll() {
  if (tpLogTimer) return;
  const poll = async () => {
    const pre = document.getElementById("tp-logs");
    const status = document.getElementById("tp-status");
    if (!pre) return;
    try {
      const response = await fetch("/api/trainpilot/logs?limit=500");
      if (!response.ok) {
        console.error("TrainPilot logs endpoint returned:", response.status, response.statusText);
        pre.textContent = `Error loading logs: ${response.status} ${response.statusText}`;
        return;
      }
      const data = await response.json();
      const lines = data.lines || [];
      const running = data.running === true;
      const finished = lines.some(line => line.includes('=== Training finished'));
      
      // Always show the latest logs, even if they're just debug info
      if (lines.length === 0) {
        pre.textContent = "No logs available yet...";
        return;
      }
      
      // Enhance log display with better formatting
      const formattedLines = lines.map(line => {
        // Highlight important log patterns
        if (line.includes('--- Kohya training logs')) {
          return `\n${line}\n${'='.repeat(50)}`;
        }
        if (line.includes('epoch') || line.includes('step')) {
          return `🔄 ${line}`;
        }
        if (line.includes('loss')) {
          return `📊 ${line}`;
        }
        if (line.includes('error') || line.includes('Error') || line.includes('ERROR')) {
          return `❌ ${line}`;
        }
        if (line.includes('warning') || line.includes('Warning') || line.includes('WARNING')) {
          return `⚠️ ${line}`;
        }
        if (line.includes('=== Starting Kohya')) {
          return `🚀 ${line}`;
        }
        if (line.includes('=== Training finished')) {
          return `✅ ${line}`;
        }
        if (line.includes('--- TrainPilot logs endpoint called')) {
          return `📡 ${line}`;
        }
        if (line.includes('--- TrainPilot process running')) {
          return `🟢 ${line}`;
        }
        if (line.includes('--- No TrainPilot process')) {
          return `🔴 ${line}`;
        }
        return line;
      });
      
      pre.textContent = formattedLines.join("\n");
      
      // Show last meaningful line as status hint
      if (status && lines.length) {
        const lastLine = lines[lines.length - 1];
        if (!running) {
          status.textContent = finished ? 'Training completed!' : 'No training process active';
        } else if (lastLine.includes('step') || lastLine.includes('epoch')) {
          status.textContent = `Training: ${lastLine.trim()}`;
        } else if (lastLine.includes('=== Training finished')) {
          status.textContent = 'Training completed!';
        } else if (lastLine.includes('error') || lastLine.includes('Error')) {
          status.textContent = `Error: ${lastLine.trim()}`;
        } else if (lastLine.includes('--- TrainPilot process running')) {
          status.textContent = 'Training process is running...';
        } else if (lastLine.includes('--- No TrainPilot process')) {
          status.textContent = 'No training process active';
        } else if (lastLine && !lastLine.includes('---')) {
          status.textContent = lastLine.trim();
        }
      }
      
      // Show training indicator if training is active
      const indicator = document.getElementById("tp-training-indicator");
      if (indicator) {
        const hasTrainingLogs = lines.some(line => 
          line.includes('=== Starting Kohya') || 
          line.includes('step') || 
          line.includes('epoch')
        );
        const hasFinished = finished;
        
        if (running && hasTrainingLogs && !hasFinished) {
          indicator.style.display = 'inline-flex';
        } else {
          indicator.style.display = 'none';
        }
      }
      
      // Auto-scroll to bottom
      pre.scrollTop = pre.scrollHeight;
    } catch (e) {
      console.error("Error polling TrainPilot logs:", e);
      // Don't show error in UI to avoid noise, just log to console
    }
  };
  poll();
  tpLogTimer = setInterval(poll, 2000);
}

window.stopTpLogPoll = function () {
  if (tpLogTimer) clearInterval(tpLogTimer);
  tpLogTimer = null;
};

function autoFillOutput(labelText) {
  const out = document.getElementById("tp-output");
  if (!out) return;
  if (!out.value || out.value.trim() === "") {
    // strip image count from label "(123 images)"
    const base = labelText.replace(/\s*\([^)]*\)\s*$/, "").trim();
    if (base) out.value = base;
  }
}

// TOML Config Modal Functions
window.showTomlConfig = async function () {
  const modal = document.getElementById("toml-modal");
  const content = document.getElementById("toml-content");
  
  if (!modal || !content) return;
  
  // Show modal with loading state
  modal.style.display = "block";
  content.className = "toml-loading";
  content.textContent = "Loading configuration...";
  
  try {
    // Fetch TOML content from backend
    const response = await fetch("/api/trainpilot/toml");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const data = await response.json();
    
    if (data.content) {
      content.className = "toml-content";
      // Apply basic TOML syntax highlighting
      content.innerHTML = highlightToml(data.content);
    } else {
      content.className = "toml-loading";
      content.textContent = "Configuration file not found or empty.";
    }
  } catch (error) {
    content.className = "toml-loading";
    content.textContent = `Error loading configuration: ${error.message}`;
  }
};

function highlightToml(tomlContent) {
  // Basic TOML syntax highlighting
  return tomlContent
    // Escape HTML
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    // Highlight keys (before =)
    .replace(/^([A-Za-z_][A-Za-z0-9_-]*)\s*=/gm, '<span class="key">$1</span> =')
    // Highlight quoted strings
    .replace(/"([^"]*)"/g, '<span class="string">"$1"</span>')
    // Highlight single-quoted strings
    .replace(/'([^']*)'/g, '<span class="string">\'$1\'</span>')
    // Highlight numbers
    .replace(/\b(\d+\.?\d*)\b/g, '<span class="number">$1</span>')
    // Highlight booleans
    .replace(/\b(true|false)\b/g, '<span class="boolean">$1</span>')
    // Highlight comments
    .replace(/(#.*$)/gm, '<span class="comment">$1</span>');
}

window.closeTomlConfig = function () {
  const modal = document.getElementById("toml-modal");
  if (modal) {
    modal.style.display = "none";
  }
};

// Close modal when clicking outside
window.onclick = function (event) {
  const modal = document.getElementById("toml-modal");
  if (modal && event.target === modal) {
    closeTomlConfig();
  }
};

// Close modal with Escape key
window.addEventListener("keydown", function (event) {
  if (event.key === "Escape") {
    closeTomlConfig();
  }
});
