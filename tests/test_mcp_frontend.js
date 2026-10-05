const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('apps/Portal/static/views/settings.html', 'utf8');
class Element {
  constructor(tag = 'div') { this.tag = tag; this.children = []; this.events = {}; this.attributes = {}; this.dataset = {}; this.style = {}; this.value = ''; this.textContent = ''; }
  addEventListener(name, fn) { (this.events[name] ||= []).push(fn); }
  async fire(name, event = {}) { for (const fn of this.events[name] || []) await fn(event); }
  setAttribute(name, value) { this.attributes[name] = value; }
  getAttribute(name) { return this.attributes[name]; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  querySelectorAll(selector) {
    return this.children.flatMap(child => [child, ...child.querySelectorAll(selector)])
      .filter(child => child.tag === selector || (selector.startsWith('input') && child.tag === 'input' && (!selector.includes(':checked') || child.checked)));
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || new Element(selector); }
  focus() {} scrollIntoView() {} select() { this.selected = true; }
}
const ready = () => ({password_required: false, available: true, enabled: false, url: '', csrf: 'csrf-fixture',
  scopes: ['datasets:inspect', 'models:read', 'operations:read', 'runs:read', 'workspace:read'],
  datasets: ['1_selected', '2_private'], runs: [], clients: [], approvals: []});
async function page(state = ready(), mutation = async () => ({token: 'lp_fixture_only', url: 'https://pilot.example/mcp'})) {
  const nodes = new Map();
  for (const match of html.matchAll(/<([a-z]+)[^>]*id="([^"]+)"[^>]*>/g)) {
    const element = new Element(match[1]); element.id = match[2];
    element.value = match[0].match(/value="([^"]*)"/)?.[1] || '';
    element.hidden = /\bhidden\b/.test(match[0]); nodes.set(element.id, element);
  }
  const get = id => nodes.get(id), mcp = name => get('settings-mcp-' + name);
  const tabs = ['general', 'access', 'connections', 'mcp', 'shutdown'].map(name => {
    const el = get('settings-tab-' + name); el.setAttribute('aria-controls', 'settings-panel-' + name); return el;
  });
  const requests = [], copied = [];
  const context = {AbortController, URL, console, location: {origin: 'https://pilot.example'},
    document: {getElementById: get, createElement: tag => new Element(tag), createTextNode: text => new Element('text'),
      querySelectorAll: selector => selector.includes('settings-theme') ? [] : selector.includes('settings-mcp-') ? [...nodes.values()].filter(el => el.id.startsWith('settings-mcp-')) : tabs},
    navigator: {clipboard: {writeText: async text => copied.push(text)}},
    fetchJson: async (url, options = {}) => {
      if (!options.method) return url === '/api/settings/mcp' ? state : url === '/api/settings' ? {comfy_access: {}} : {};
      const body = JSON.parse(options.body); requests.push({url, body, headers: options.headers});
      if (url === '/api/settings/password') { Object.assign(state, ready()); return {}; }
      return mutation(url, body);
    }};
  context.window = context;
  vm.createContext(context);
  for (const name of ['screen-lifecycle', 'settings']) vm.runInContext(fs.readFileSync(`apps/Portal/static/js/${name}.js`, 'utf8'), context);
  const screen = context.createScreenLifecycle();
  await context.initSettings(screen); await mcp('refresh').onclick();
  return {mcp, get, context, screen, state, requests, copied};
}

test('first connection defaults to reads and only explicitly selected objects, with atomic enable', async () => {
  const p = await page();
  assert.equal(p.mcp('url').value, 'https://pilot.example/mcp');
  assert.equal(p.mcp('scopes').querySelectorAll('input:checked').length, 5);
  assert.equal(p.mcp('datasets').querySelectorAll('input:checked').length, 0);
  await p.mcp('create').onclick();
  assert.equal(p.requests.length, 0);
  p.mcp('datasets').querySelectorAll('input')[0].checked = true;
  await p.mcp('refresh').onclick();
  p.mcp('password').value = 'owner-fixture';
  await p.mcp('create').onclick();
  const request = p.requests[0];
  assert.equal(request.body.enable, true);
  assert.deepEqual(request.body.datasets, ['1_selected']);
  assert.equal(request.body.policy.enabled, false);
  assert.equal(request.headers['X-MCP-CSRF'], 'csrf-fixture');
  assert.equal(p.mcp('password').value, '');
  assert.equal(p.mcp('token-result').hidden, false);
  assert.doesNotMatch(p.mcp('instructions').value, /lp_fixture_only/);
  await p.mcp('copy-setup').onclick();
  assert.match(p.copied[0], /Streamable HTTP\nURL: https:\/\/pilot.example\/mcp\nAuthorization header: Bearer lp_fixture_only/);
  assert.match(p.copied[0], /private configuration/);
  p.screen.dispose(); assert.equal(p.mcp('token').value, ''); assert.equal(p.mcp('instructions').value, '');
});

test('missing password is guided, validates confirmation and continues with the newly authenticated session', async () => {
  const p = await page({password_required: true, enabled: false, url: ''});
  assert.equal(p.mcp('password-setup').hidden, false);
  assert.equal(p.mcp('connection-form').hidden, true);
  p.mcp('new-password').value = 'short'; p.mcp('confirm-password').value = 'different';
  await p.mcp('set-password').onclick(); assert.equal(p.requests.length, 0);
  p.mcp('new-password').value = p.mcp('confirm-password').value = 'test-only-password';
  await p.mcp('set-password').onclick();
  assert.equal(p.requests[0].url, '/api/settings/password');
  assert.equal(p.mcp('password-setup').hidden, true);
  assert.equal(p.mcp('connection-form').hidden, false);
  assert.equal(p.mcp('password').value, 'test-only-password');
  assert.equal(p.mcp('new-password').value, '');
  await p.get('settings-tab-general').fire('click');
  assert.equal(p.mcp('password').value, '');
});

test('unavailable transport and rejected mutation are recoverable without pretending a token exists', async () => {
  const p = await page({...ready(), available: false}, async () => { throw Error('{"detail":"NOT_AUTHORIZED"}'); });
  assert.equal(p.mcp('create').disabled, true);
  assert.match(p.mcp('status').textContent, /unavailable/);
  p.state.available = true; await p.mcp('refresh').onclick();
  p.mcp('password').value = 'wrong'; await p.mcp('create').onclick();
  assert.match(p.mcp('status').textContent, /NOT_AUTHORIZED/);
  assert.equal(p.mcp('token-result').hidden, true); assert.equal(p.mcp('create').disabled, false);
});

test('late token response does not leak after tab departure and duplicate submission is suppressed', async () => {
  let finish;
  const p = await page(ready(), () => new Promise(resolve => { finish = resolve; }));
  p.mcp('password').value = 'fixture'; const pending = p.mcp('create').onclick();
  await p.mcp('create').onclick(); assert.equal(p.requests.length, 1);
  await p.get('settings-tab-general').fire('click');
  finish({token: 'late-secret'}); await pending;
  assert.equal(p.mcp('token').value, ''); assert.equal(p.mcp('token-result').hidden, true);
});

test('clipboard fallback exposes credentials only for manual copying and clears them on navigation', async () => {
  const p = await page(); p.context.navigator.clipboard.writeText = async () => { throw Error('denied'); };
  p.mcp('password').value = 'fixture'; await p.mcp('create').onclick(); await p.mcp('copy-setup').onclick();
  assert.match(p.mcp('instructions').value, /Bearer lp_fixture_only/); assert.equal(p.mcp('instructions').selected, true);
  await p.get('settings-tab-general').fire('click'); assert.equal(p.mcp('instructions').value, '');
  const examples = html.split('id="settings-mcp-examples"')[1].split('</div>')[0].match(/<button[^>]*>(.*?)<\/button>/g);
  assert.equal(examples.length, 4);
  p.context.navigator.clipboard.writeText = async text => p.copied.push(text);
  await p.mcp('examples').fire('click', {target: {closest: () => ({textContent: 'Review my shared datasets.'})}});
  assert.equal(p.copied.at(-1), 'Review my shared datasets.');
});
