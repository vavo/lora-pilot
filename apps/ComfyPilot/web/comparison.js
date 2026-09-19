import { app } from '../../scripts/app.js';

const allowedNodes = new Set(['CheckpointLoaderSimple', 'UNETLoader', 'DualCLIPLoader', 'VAELoader',
  'LoraLoader', 'EmptyLatentImage', 'EmptySD3LatentImage', 'CLIPTextEncode', 'FluxGuidance',
  'KSampler', 'VAEDecode', 'SaveImage']);
let loading = false;
async function loadComparison() {
  const encoded = new URLSearchParams(location.hash.slice(1)).get('controlpilot-comparison');
  if (!encoded || loading) return;
  loading = true;
  try {
    if (encoded.length > 100000) throw new Error('Comparison workflow is too large');
    const graph = JSON.parse(encoded);
    const nodes = Object.values(graph);
    if (!nodes.length || nodes.length > 32 || nodes.some(node => !allowedNodes.has(node.class_type))) {
      throw new Error('Unsupported comparison workflow');
    }
    history.replaceState(null, '', location.pathname + location.search);
    await app.loadApiJson(graph, 'ControlPilot LoRA comparison');
  } catch (error) {
    alert(`Could not open the ControlPilot comparison: ${error.message}. Download the prepared workflow from ControlPilot and open it manually.`);
  } finally { loading = false; }
}
app.registerExtension({
  name: 'LoRA-Pilot.Comparison',
  setup() { window.addEventListener('hashchange', loadComparison); },
  afterConfigureGraph() { requestAnimationFrame(loadComparison); },
});
