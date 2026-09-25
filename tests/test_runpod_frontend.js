const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup() {
  const elements = new Map();
  const document = {getElementById(id) {
    if (!elements.has(id)) elements.set(id, {hidden: true, textContent: ''});
    return elements.get(id);
  }};
  const context = vm.createContext({window: {}, document, Intl, Number});
  vm.runInContext(fs.readFileSync('apps/Portal/static/js/dashboard.js', 'utf8'), context);
  return {context, elements, document};
}

test('RunPod card distinguishes estimates, recorded charges and permission failures', async () => {
  const {context, document} = setup();
  const data = {enabled: true, available: true, pod_id: '<script>pod</script>', status: 'RUNNING',
    hourly_usd: 2, session_estimate_usd: 1, billing: {available: false, message: 'Billing permission unavailable'},
    storage: {available: true, kind: 'network', size_gb: 100, mount: '/workspace', tier: 'HIGH_PERFORMANCE'}};
  await context.refreshRunpod({active: true, json: async () => data, check() {}});
  assert.equal(document.getElementById('dash-runpod').hidden, false);
  assert.equal(document.getElementById('dash-runpod-rate').textContent, '$2.00 / hour');
  assert.equal(document.getElementById('dash-runpod-session').textContent, '$1.00');
  assert.equal(document.getElementById('dash-runpod-billed').textContent, 'Unavailable');
  assert.match(document.getElementById('dash-runpod-storage').textContent, /100 GB allocated/);
  assert.equal(document.getElementById('dash-runpod-status').textContent, '<script>pod</script> · RUNNING');
  assert.equal(document.getElementById('dash-runpod-status').innerHTML, undefined);
  data.billing = {available: true, total_usd: 0, gpu_usd: 0, cpu_usd: 0, disk_usd: 0, date_utc: '2026-09-25'};
  await context.refreshRunpod({active: true, json: async () => data, check() {}});
  assert.equal(document.getElementById('dash-runpod-billed').textContent, '$0.00');
});

test('non-RunPod installs hide the panel and stale navigation cannot update it', async () => {
  const {context, document} = setup();
  await context.refreshRunpod({active: true, json: async () => ({enabled: false}), check() {}});
  assert.equal(document.getElementById('dash-runpod').hidden, true);
  await context.refreshRunpod({active: false, json: async () => ({enabled: true}), check() {throw Error('disposed');}});
  assert.equal(document.getElementById('dash-runpod').hidden, true);
});
