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

test('only a successful queue submission clears the unfinished draft', async () => {
  const store=storage();
  const nodes=new Map();
  const node=id=>{
    if (!nodes.has(id)) nodes.set(id,{value:'',textContent:'',hidden:false,addEventListener(){},classList:{toggle(){}},replaceChildren(){},append(){}});
    return nodes.get(id);
  };
  const submitted={family:'sdxl',profile:'regular',dataset_name:'portraits',output_name:'Monday',source_run_id:null};
  context.createTrainingDraft(store).save(submitted);
  let rejectSubmission=true;
  const page=vm.createContext({URLSearchParams,window:{localStorage:store},document:{getElementById:node,querySelectorAll:()=>[],createElement:tag=>node(tag)},
    tpStarting:false,tpStatusKnown:true,tpDismissedRunId:null,
    setTimeout:()=>1,clearTimeout(){},normalizeOutputName:v=>v,updateEpochExample(){},updateTpSummary(){},syncTpActions(){},showTpError(){},
    ensureTrainpilotModelsPresent:async()=>true,
    fetchJson:async(path,options)=>{
      if(path==='/api/trainpilot/toml')return {path:'/tmp/config.toml'};
      if(path==='/api/training/preflight')return {missing:[],conflicts:[]};
      if(path==='/api/training/runs' && options.method==='POST'){
        if(rejectSubmission)throw Error('queue unavailable');
        return {id:'a'.repeat(32)};
      }
      return {runs:[],paused:false,conflicts:[],active_id:null};
    },
  });
  for(const file of ['training-draft','training-workspace'])vm.runInContext(fs.readFileSync(`apps/Portal/static/js/${file}.js`,'utf8'),page);
  await page.window.trainingWorkspace.init();
  assert.equal(node('tp-output').value,'Monday');
  await page.window.trainingWorkspace.submit();
  assert.equal(context.createTrainingDraft(store).read().output_name,'Monday');
  rejectSubmission=false;
  await page.window.trainingWorkspace.submit();
  assert.equal(context.createTrainingDraft(store).read(),null);
});

vm.runInContext(fs.readFileSync('apps/Portal/static/js/task-feedback.js','utf8'),context);
test('failure advice offers the correct action and leaves unknown failures unclassified',()=>{
  assert.equal(context.taskAdvice('CUDA out of memory').section,'trainpilot');
  assert.equal(context.taskAdvice('No space left on device').section,'storage');
  assert.equal(context.taskAdvice('403 Forbidden gated repo').section,'settings');
  assert.equal(context.taskAdvice('A required model was removed').section,'models');
  assert.equal(context.taskAdvice('No module named torch').section,'services');
  assert.equal(context.taskAdvice('Unexpected exit 7').section,undefined);
});
test('timing labels avoid estimates when the trainer has not reported one',()=>{
  assert.equal(context.trainingTimeLabel({stage:'Preparing caches',elapsed_seconds:70,remaining_seconds:null}),'Preparing caches · 1m 10s elapsed');
  assert.match(context.trainingTimeLabel({stage:'Training',elapsed_seconds:400,remaining_seconds:90}),/about 1m 30s remaining/);
});
