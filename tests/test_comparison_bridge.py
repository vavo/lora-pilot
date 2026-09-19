import shutil
import subprocess
import unittest
from pathlib import Path


class ComparisonBridgeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is required for the frontend lifecycle test')
    def test_leaving_training_during_dataset_fetch_does_not_initialize_detached_page(self):
        script_path = Path(__file__).resolve().parents[1] / 'apps/Portal/static/js/trainpilot.js'
        script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
let page = {}, complete, initialized = 0;
const context = {window:{addEventListener(){},trainingWorkspace:{init(){ initialized++; }}}, document:{getElementById(){return page}}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
context.bindTpControls = () => {};
context.loadTpDatasets = () => new Promise(resolve => { complete = resolve; });
(async () => {
  const pending = context.window.initTrainpilot();
  page = null;
  complete();
  await pending;
  assert.equal(initialized, 0);
  page = {};
  const active = context.window.initTrainpilot();
  complete();
  await active;
  assert.equal(initialized, 1);
})().catch(error => { console.error(error); process.exit(1); });
'''
        result = subprocess.run(['node', '-e', script, str(script_path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node.js is required for the frontend bridge test')
    def test_prepared_graph_loads_once_without_queueing_and_rejects_custom_nodes(self):
        bridge = Path(__file__).resolve().parents[1] / 'apps/ComfyPilot/web/comparison.js'
        script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync(process.argv[1], 'utf8').replace(/^import .*;\n/, '');
let extension, loads = [], errors = [];
const location = { hash: '', pathname: '/', search: '' };
const listeners = {};
const context = {
  URLSearchParams, location,
  app: { registerExtension(value) { extension = value; }, async loadApiJson(...args) { loads.push(args); } },
  window: { addEventListener(name, fn) { listeners[name] = fn; } },
  history: { replaceState() { location.hash = ''; } },
  alert(message) { errors.push(message); },
  requestAnimationFrame(fn) { return fn(); }
};
vm.runInNewContext(source, context);
(async () => {
  extension.setup();
  const graph = {'1': {class_type:'KSampler', inputs:{seed:42}}};
  location.hash = '#controlpilot-comparison=' + encodeURIComponent(JSON.stringify(graph));
  extension.afterConfigureGraph();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(loads.length, 1);
  assert.equal(loads[0][0]['1'].inputs.seed, 42);
  assert.equal(location.hash, '');
  await listeners.hashchange();
  assert.equal(loads.length, 1);
  location.hash = '#controlpilot-comparison=' + encodeURIComponent(JSON.stringify({'1': {class_type:'UnknownCustomNode'}}));
  await listeners.hashchange();
  assert.equal(loads.length, 1);
  assert.equal(errors.length, 1);
  assert.match(errors[0], /Unsupported comparison workflow/);
})().catch(error => { console.error(error); process.exit(1); });
'''
        result = subprocess.run(['node', '-e', script, str(bridge)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
