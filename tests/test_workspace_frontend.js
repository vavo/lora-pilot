const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({window:{}, document:{}, Set, Map, Date});
for (const file of ['workspace-status', 'training-draft']) {
  vm.runInContext(fs.readFileSync(`apps/Portal/static/js/${file}.js`, 'utf8'), context);
}
function storage() {
  const values = new Map();
  return {getItem:key=>values.get(key) || null, setItem:(key,value)=>values.set(key,value), removeItem:key=>values.delete(key)};
}
const item = (state, id='job') => ({id, state, created_at:1});
test('activity reports transitions once and keeps state across navigation/refresh', () => {
  const store=storage();
  let tracker=context.createActivityTracker(store, ()=>2000);
  assert.equal(tracker.update([item('succeeded')]).length,0);
  assert.equal(tracker.update([item('running')]).length,0);
  tracker=context.createActivityTracker(store, ()=>3000);
  assert.equal(tracker.update([item('failed')]).length,1);
  assert.equal(tracker.update([item('failed')]).length,0);
  assert.equal(tracker.update([]).length,0);
  assert.equal(tracker.update([item('failed')]).length,0);
});
test('activity catches short tasks but does not announce historical completions', () => {
  const tracker=context.createActivityTracker(storage(), ()=>2000);
  assert.equal(tracker.update([{...item('succeeded'),created_at:3}]).length,1);
  assert.equal(tracker.update([item('failed','old')]).length,0);
});
test('malformed or blocked activity storage cannot disable activity', () => {
  const store=storage();store.setItem('lora-pilot.activity.v1', '{"seen":[null,2,"bad",["job","running"]]}');
  assert.equal(context.createActivityTracker(store,()=>2000).update([item('failed')]).length,1);
  const blocked={getItem(){throw Error('blocked')},setItem(){throw Error('blocked')}};
  const tracker=context.createActivityTracker(blocked,()=>2000);
  tracker.update([item('running')]);assert.equal(tracker.update([item('failed')]).length,1);
});
test('draft survives a new page, preserves deliberate empty values and excludes unrelated fields', () => {
  const store=storage();const draft=context.createTrainingDraft(store);
  draft.save({family:'flux1',profile:'high_quality',dataset_name:'portraits',output_name:'',source_run_id:'a'.repeat(32),token:'SECRET',toml_path:'/private'});
  const saved=context.createTrainingDraft(store).read();
  assert.equal(saved.output_name,'');assert.equal(saved.family,'flux1');assert.equal(saved.profile,'high_quality');
  assert.equal(saved.dataset_name,'portraits');assert.equal(saved.source_run_id,'a'.repeat(32));
  assert.equal(JSON.stringify(saved).includes('SECRET'),false);assert.equal('toml_path' in saved,false);
  draft.clear();assert.equal(draft.read(),null);
});
test('invalid drafts are not restored; storage failures are available to the UI', () => {
  const store=storage();const draft=context.createTrainingDraft(store);
  store.setItem('lora-pilot.training-draft.v1','{"version":2}');assert.equal(draft.read(),null);
  store.setItem('lora-pilot.training-draft.v1','{bad');assert.throws(()=>draft.read());
  const blocked=context.createTrainingDraft({getItem(){throw Error('blocked')},removeItem(){throw Error('blocked')}});
  assert.throws(()=>blocked.read());assert.throws(()=>blocked.clear());
});
