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
  assert.equal(document.getElementById('dash-runpod-rate').innerHTML, undefined);
  data.billing = {available: true, total_usd: 0, gpu_usd: 0, cpu_usd: 0, disk_usd: 0, date_utc: '2026-09-25'};
  await context.refreshRunpod({active: true, json: async () => data, check() {}});
  assert.equal(document.getElementById('dash-runpod-billed').textContent, '$0.00');
});

test('storage meters distinguish measured workspace use from free space', () => {
  const context = vm.createContext({});
  context.window = context;
  vm.runInContext(fs.readFileSync('apps/Portal/static/js/utils.js', 'utf8'), context);
  const label = {}, fill = {style: {}}, meter = {dataset: {}, setAttribute(key,value) { this[key]=value; }, querySelector: () => fill};
  const gb = 1024 ** 3;
  context.renderStorageUsage(label, meter, {total: 100*gb, used: 52*gb, free: null, capacity_source: 'runpod'});
  assert.equal(fill.style.width, '52%');
  assert.equal(label.textContent, '52 GB of 100 GB in workspace');
  assert.doesNotMatch(label.textContent, /free/);
  assert.match(meter['aria-label'], /52% of capacity/);
  context.renderStorageUsage(label, meter, {total: 100*gb, used: 52*gb, free: 48*gb});
  assert.equal(label.textContent, '48 GB free of 100 GB');
  assert.equal(fill.style.width, '52%');
});

test('storage meters handle zero, full, and missing capacity without inventing usage', () => {
  const context = vm.createContext({});
  context.window = context;
  vm.runInContext(fs.readFileSync('apps/Portal/static/js/utils.js', 'utf8'), context);
  const label = {}, fill = {style: {}}, meter = {dataset: {}, setAttribute(key,value) { this[key]=value; }, querySelector: () => fill};
  context.renderStorageUsage(label, meter, {total: 100, used: 0});
  assert.equal(fill.style.width, '0%');
  assert.equal(meter.dataset.state, 'normal');
  assert.match(label.textContent, /^0 B/);
  context.renderStorageUsage(label, meter, {total: 100, used: 120});
  assert.equal(fill.style.width, '100%');
  assert.equal(meter.dataset.state, 'full');
  for (const disk of [{used: 52}, {total: 100}, null]) {
    context.renderStorageUsage(label, meter, disk);
    assert.equal(meter.dataset.state, 'unknown');
    assert.equal(fill.style.width, '0%');
    assert.doesNotMatch(meter['aria-label'], /%/);
  }
});

test('non-RunPod installs hide the panel and stale navigation cannot update it', async () => {
  const {context, document} = setup();
  await context.refreshRunpod({active: true, json: async () => ({enabled: false}), check() {}});
  assert.equal(document.getElementById('dash-runpod').hidden, true);
  await context.refreshRunpod({active: false, json: async () => ({enabled: true}), check() {throw Error('disposed');}});
  assert.equal(document.getElementById('dash-runpod').hidden, true);
});
