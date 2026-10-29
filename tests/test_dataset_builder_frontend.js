const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor(tag = 'div') { Object.assign(this, {tag, children: [], dataset: {}, handlers: {}, value: '', checked: false, hidden: false}); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(name, callback) { this.handlers[name] = callback; }
  setAttribute() {}
  get options() { return this.children; }
  querySelectorAll() { return this.children.flatMap(child => [child, ...child.querySelectorAll()]); }
}
const settle = () => new Promise(resolve => setImmediate(resolve));
function fixture(ready = true) {
  const nodes = new Map();
  const el = name => { const id = name.startsWith('db-') || name === 'dataset-builder' ? name : 'db-' + name;
    if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); };
  el('dataset-builder').hidden = true; el('source').value = 'prompt'; el('clothes').checked = true;
  let job = {id: 'a'.repeat(32), spec: {name: 'sample', count: 4}, phase: 'variations', status: 'review',
    message: 'Review your images', references: ['reference.png'], reference: 'reference.png', accepted_count: 3,
    items: Array.from({length: 4}, (_, slot) => ({slot, shot: 'portrait', file: `image-${slot}.png`, attempts: 1,
      accepted: slot !== 0, caption: 'trigger, a portrait', review: {identity: 'consistent'}, warnings: []}))};
  const calls = [], handoffs = [];
  const page = vm.createContext({window: {}, document: {getElementById: el, createElement: tag => new Element(tag)},
    Option: function (textContent, value) { return Object.assign(new Element('option'), {textContent, value}); },
    FormData, AbortController, DOMException, setTimeout: () => 0, clearTimeout() {},
    openTrainingDataset: name => handoffs.push(name)});
  page.window.fetchJson = async (url, options = {}) => {
    calls.push([url, options]);
    if (url.includes('preflight')) return {ready, problems: ready ? [] : ['Install required models']};
    if (options.method === 'PATCH') {
      const slot = Number(url.split('/').pop());
      Object.assign(job.items[slot], JSON.parse(options.body));
      job.accepted_count = job.items.filter(item => item.accepted).length;
    }
    if (url.endsWith('/finish')) job = {...job, status: 'saved', dataset: '1_sample'};
    return structuredClone(url.endsWith('/jobs') ? [job] : job);
  };
  vm.runInContext(fs.readFileSync('apps/Portal/static/js/screen-lifecycle.js', 'utf8'), page);
  vm.runInContext(fs.readFileSync('apps/Portal/static/js/dataset-builder.js', 'utf8'), page);
  page.window.initDatasetBuilder(page.window.createScreenLifecycle());
  el('open').onclick();
  return {el, calls, handoffs};
}
function card(el, slot) {
  const children = el('images').children[slot].querySelectorAll();
  return {caption: children.find(child => child.tag === 'textarea'),
    button: text => children.find(child => child.tag === 'button' && child.textContent === text)};
}

test('dataset name patterns work with modern browser Unicode-set validation', () => {
  const html = fs.readFileSync('apps/Portal/static/views/datasets.html', 'utf8');
  const pattern = html.match(/id="db-name"[^>]*pattern="([^"]+)"/)[1];
  const regex = new RegExp(`^(?:${pattern})$`, 'v');
  assert.equal(regex.test('person-01_test'), true);
  assert.equal(regex.test('../escape'), false);
});

test('builder preserves other caption drafts and gates the exact-count training handoff', async () => {
  const {el, handoffs} = fixture(); await settle();
  const second = card(el, 1); second.caption.value = 'trigger, edited second image'; second.caption.handlers.input();
  await card(el, 0).button('Keep image & caption').onclick();
  assert.equal(card(el, 1).caption.value, 'trigger, edited second image');
  el('reviewed').checked = true; el('reviewed').onchange();
  assert.equal(el('finish').disabled, true);
  assert.match(el('accepted').textContent, /Save your edited captions/);
  await card(el, 1).button('Save caption').onclick();
  assert.equal(el('reviewed').checked, false);
  el('reviewed').checked = true; el('reviewed').onchange();
  assert.equal(el('finish').disabled, false);
  await el('finish').onclick();
  assert.deepEqual(handoffs, ['1_sample']);
  assert.equal(card(el, 0).caption.disabled, true);
});

test('missing dependencies disable creation and photo/fixed-look inputs stay consistent', async () => {
  const {el} = fixture(false); await settle();
  assert.equal(el('create').disabled, true);
  assert.match(el('preflight').textContent, /Install required models/);
  el('source').value = 'photo'; el('source').onchange(); await settle();
  assert.equal(el('prompt').required, false); assert.equal(el('prompt-label').hidden, true);
  assert.equal(el('photo').required, true); assert.equal(el('photo-label').hidden, false);
  el('goal').value = 'character'; el('goal').onchange();
  assert.equal(el('clothes').disabled, true); assert.equal(el('clothes').checked, false);
  assert.equal(el('hair').disabled, true); assert.equal(el('hair').checked, false);
});
