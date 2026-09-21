import { app } from '../../scripts/app.js';

const allowedNodes = new Set(['CheckpointLoaderSimple', 'UNETLoader', 'DualCLIPLoader', 'VAELoader',
  'LoraLoader', 'EmptyLatentImage', 'EmptySD3LatentImage', 'CLIPTextEncode', 'FluxGuidance',
  'KSampler', 'VAEDecode', 'SaveImage']);
let loading = false;
// ComfyUI rewrites the URL while restoring its initial graph.
// Capture the handoff before that restoration can remove the fragment.
let pending = new URLSearchParams(location.hash.slice(1));
async function loadComparison() {
  const encoded = pending.get('controlpilot-comparison');
  if (!encoded || loading) return;
  const token = pending.get('controlpilot-token');
  loading = true;
  const notify = error => {
    if (window.parent === window || !document.referrer) return;
    window.parent.postMessage({type: 'controlpilot-comparison', token, error}, new URL(document.referrer).origin);
  };
  try {
    if (encoded.length > 1000000) throw new Error('Comparison workflow is too large');
    const graph = JSON.parse(encoded);
    const nodes = Object.values(graph);
    if (!nodes.length || nodes.length > 512 || nodes.some(node => !node || !allowedNodes.has(node.class_type))) {
      throw new Error('Unsupported comparison workflow');
    }
    await app.loadApiJson(graph, 'ControlPilot LoRA comparison');
    pending = new URLSearchParams();
    if (location.hash.includes('controlpilot-comparison=')) history.replaceState(null, '', location.pathname + location.search);
    notify(null);
  } catch (error) {
    pending = new URLSearchParams();
    notify(error.message);
    alert(`Could not open the ControlPilot comparison: ${error.message}. Download the prepared workflow from ControlPilot and open it manually.`);
  } finally { loading = false; }
}
app.registerExtension({
  name: 'LoRA-Pilot.Comparison',
  setup() { window.addEventListener('hashchange', () => {
    const next = new URLSearchParams(location.hash.slice(1));
    if (next.has('controlpilot-comparison')) { pending = next; return loadComparison(); }
  }); },
  afterConfigureGraph() { requestAnimationFrame(loadComparison); },
});
