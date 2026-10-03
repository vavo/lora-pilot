const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const read = name => fs.readFileSync(`apps/Portal/static/js/${name}.js`, 'utf8');
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; };
function page(fetchJson) {
  const nodes = new Map();
  const document = { getElementById: id => nodes.get(id) || null };
  const context = vm.createContext({ AbortController, console, document, fetchJson, setTimeout, clearTimeout, alert() {} });
  context.window = context;
  vm.runInContext(read('screen-lifecycle') + '\n' + read('services'), context);
  vm.runInContext('servicesScreen = createScreenLifecycle()', context);
  return { context, nodes, run: source => vm.runInContext(source, context) };
}
function element() {
  const classes = new Set();
  return { textContent: '', disabled: false, checked: false, classList: {
    add: (...names) => names.forEach(name => classes.add(name)),
    remove: (...names) => names.forEach(name => classes.delete(name)),
    toggle: (name, enabled) => enabled ? classes.add(name) : classes.delete(name),
    contains: name => classes.has(name),
  } };
}

test('late log responses cannot overwrite the newly selected service, even if transport ignores abort', async () => {
  const requests = [];
  const { context, nodes, run } = page(() => { const request = deferred(); requests.push(request); return request.promise; });
  const oldPreview = element(), nextPreview = element();
  nodes.set('svc-log-preview', oldPreview);
  const first = context.loadServiceLogPreview('comfy', run('servicesScreen.latest("detail")'));
  nodes.set('svc-log-preview', nextPreview);
  const second = context.loadServiceLogPreview('kohya', run('servicesScreen.latest("detail")'));
  requests[1].resolve({ log: '<script>new log stays text</script>' });
  await second;
  requests[0].resolve({ log: 'STALE COMFY LOG' });
  await first;
  assert.equal(nextPreview.textContent, '<script>new log stays text</script>');
  assert.equal(oldPreview.textContent, '');
});

test('an update continues tracking while its service detail is not mounted', () => {
  const { context, nodes, run } = page(async () => ({}));
  context.renderServiceUpdateStatus('comfy', { state: 'running', last_line: 'Installing' });
  const status = element(), button = element();
  nodes.set('svc-update-status-comfy', status);
  nodes.set('svc-update-comfy', button);
  nodes.set('svc-version-comfy', element());
  context.renderServiceVersion('comfy', { installed: 'old', latest: 'new', update_supported: true, update_available: true });
  assert.equal(button.disabled, true);
  run('renderServiceUpdateStatus("comfy", serviceUpdateStatuses.comfy)');
  assert.match(status.textContent, /Installing/);
  context.renderServiceUpdateStatus('comfy', { state: 'done', installed_after: 'new' });
  assert.equal(button.disabled, false);
  assert.match(status.textContent, /new/);
});

test('auto-start survives changing service selection during save and prevents duplicate writes', async () => {
  const pending = deferred(); let calls = 0;
  const { context, nodes, run } = page(() => { calls++; return pending.promise; });
  run('servicesData = [{name:"comfy", autostart:false}]; selectedService="comfy"');
  const toggle = element(); toggle.checked = true;
  const saving = context.toggleServiceAutostart('comfy', toggle);
  await context.toggleServiceAutostart('comfy', toggle);
  assert.equal(calls, 1);
  const remountedToggle = element(); remountedToggle.disabled = true;
  nodes.set('svc-autostart-toggle', remountedToggle);
  pending.resolve({ status: 'ok' }); await saving;
  assert.equal(remountedToggle.checked, true);
  assert.equal(remountedToggle.disabled, false);
  assert.equal(run('servicesData[0].autostart'), true);
});

test('failed auto-start save restores the server value and releases the pending state', async () => {
  const { context, nodes, run } = page(async () => { throw Error('offline'); });
  run('servicesData = [{name:"comfy", autostart:false}]; selectedService="comfy"');
  const toggle = element(); toggle.checked = true; nodes.set('svc-autostart-toggle', toggle);
  await context.toggleServiceAutostart('comfy', toggle);
  assert.equal(toggle.checked, false); assert.equal(toggle.disabled, false);
  assert.equal(run('serviceAutostartPending.size'), 0);
});

test('filters do not mislabel starting, stopping or failed services as stopped', () => {
  const { run } = page(async () => ({}));
  run('servicesData = ["RUNNING", "STOPPED", "STARTING", "STOPPING", "FATAL", "EXITED"].map(state_raw => ({state_raw}))');
  assert.equal(run('visibleServices().length'), 6);
  assert.equal(run('serviceFilter="running"; visibleServices().length'), 1);
  assert.equal(run('serviceFilter="stopped"; visibleServices().length'), 2);
  assert.equal(run('stateBadge({state_raw:"STOPPED"}).cls'), 'stopped');
  assert.equal(run('stateBadge({state_raw:"FATAL"}).cls'), 'error');
});
