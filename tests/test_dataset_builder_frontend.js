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
  removeAttribute() {}
  showModal() { this.open = true; }
  close() { this.open = false; this.onclose?.(); }
  focus() { this.focused = true; }
  contains(element) { return this === element || this.children.some(child => child.contains(element)); }
  querySelector(selector) { return this.querySelectorAll().find(child => selector === `[data-compare-slot="${child.dataset.compareSlot}"]`); }
  get options() { return this.children; }
  querySelectorAll() { return this.children.flatMap(child => [child, ...child.querySelectorAll()]); }
}
const settle = () => new Promise(resolve => setImmediate(resolve));
function fixture(ready = true) {
  const nodes = new Map();
  const el = name => { const id = name.startsWith('db-') || name === 'dataset-builder' ? name : 'db-' + name;
    if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); };
  el('dataset-builder').hidden = true; el('source').value = 'prompt'; el('clothes').checked = true;
  el('count').value = '4'; el('goal').value = 'identity';
  let job = {id: 'a'.repeat(32), spec: {name: 'sample', count: 4}, phase: 'variations', status: 'review',
    message: 'Review your images', references: ['reference.png'], reference: 'reference.png', accepted_count: 3,
    items: Array.from({length: 4}, (_, slot) => ({slot, shot: 'portrait', file: `image-${slot}.png`, attempts: 1,
      accepted: slot !== 0, caption: 'trigger, a portrait', review: {identity: 'consistent'},
      warnings: slot === 0 ? ['Identity uncertain: compare with the reference before keeping.'] : []}))};
  const calls = [], handoffs = [];
  const page = vm.createContext({window: {}, document: {getElementById: el, createElement: tag => new Element(tag)},
    Option: function (textContent, value) { return Object.assign(new Element('option'), {textContent, value}); },
    FormData, URLSearchParams, AbortController, DOMException, setTimeout: () => 0, clearTimeout() {},
    openTagpilotDataset: name => handoffs.push(name)});
  page.window.fetchJson = async (url, options = {}) => {
    calls.push([url, options]);
    if (url.includes('preflight')) return {ready, problems: ready ? [] : ['Install required models']};
    if (url.includes('/plan?')) return {count:4, framing:{'close-up portrait':2,'waist-up portrait':1,'full-body photograph':1},
      angles:{'front view':3,'front-left three-quarter view':1},vary_clothes:el('goal').value === 'identity' && el('clothes').checked,vary_hair:false};
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

test('builder has no caption editor and hands the exact reviewed count to TagPilot', async () => {
  const {el, handoffs} = fixture(); await settle();
  assert.equal(card(el, 0).caption, undefined);
  el('reviewed').checked = true; el('reviewed').onchange();
  assert.equal(el('finish').disabled, true);
  await card(el, 0).button('Keep image').onclick();
  assert.equal(el('reviewed').checked, false);
  el('reviewed').checked = true; el('reviewed').onchange();
  assert.equal(el('finish').disabled, false);
  await el('finish').onclick();
  assert.deepEqual(handoffs, ['1_sample']);
  assert.equal(card(el, 0).button('Keep image').disabled, true);
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

test('planned image mix uses backend recipe counts and follows fixed-look selection',async()=>{
  const {el,calls}=fixture(); await settle();
  assert.equal(el('create').disabled,false);
  assert.match(el('plan').textContent,/4 images: 2 × close-up portrait/);
  assert.match(el('plan').textContent,/front-left three-quarter view/);
  assert.match(el('plan').textContent,/Vary clothes/);
  el('goal').value='character';el('goal').onchange();await settle();
  assert.match(el('plan').textContent,/Keep reference clothes/);
  assert.ok(calls.some(([url])=>url.includes('/plan?') && url.includes('goal=character')));
});

test('reference comparison reuses Keep/Exclude actions and clears review confirmation',async()=>{
  const {el}=fixture(); await settle();
  card(el,0).button('Compare with reference').onclick();
  assert.equal(el('compare').open,true);
  assert.match(el('compare-reference').src,/reference.png$/);
  assert.match(el('compare-image').src,/image-0.png$/);
  assert.match(el('compare-warnings').children[0].textContent,/face could not be matched confidently/);
  el('reviewed').checked=true;
  await el('compare-actions').children.find(button=>button.textContent==='Keep image').onclick();
  assert.match(el('compare-state').textContent,/Kept for training/);
  assert.equal(el('reviewed').checked,false);
  assert.equal(card(el,0).button('Keep image').disabled,true);
  el('compare-close').onclick();assert.equal(el('compare').open,false);
  assert.equal(card(el,0).button('Compare with reference').focused,true);
});

test('each preparation screen names the same four steps and has a current step',()=>{
  for (const file of ['apps/Portal/static/views/datasets.html','apps/TagPilot/index.html','apps/Portal/static/views/trainpilot.html']) {
    const html=fs.readFileSync(file,'utf8');
    assert.match(html,/class="preparation-steps"[^>]*aria-label="Dataset to training"/);
    assert.match(html,/aria-current="step"/);
    for (const label of ['Reference','Review images','Caption in TagPilot','Train']) assert.ok(html.includes(`>${label}</li>`));
  }
});
