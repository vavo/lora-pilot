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
    if (!nodes.has(id)) nodes.set(id,{value:'',textContent:'',hidden:false,reportValidity(){return true;},addEventListener(){},classList:{toggle(){}},replaceChildren(){},append(){}});
    return nodes.get(id);
  };
  const submitted={family:'sdxl',profile:'regular',dataset_name:'portraits',output_name:'Monday',source_run_id:null};
  context.createTrainingDraft(store).save(submitted);
  let rejectSubmission=true;
  const page=vm.createContext({URLSearchParams,AbortController,clearModelDownloadUI(){},window:{localStorage:store},document:{getElementById:node,querySelectorAll:()=>[],createElement:tag=>node(tag)},
    tpStarting:false,tpStatusKnown:true,tpDismissedRunId:null,
    setTimeout:()=>1,clearTimeout(){},normalizeOutputName:v=>v,updateEpochExample(){},updateTpSummary(){},syncTpActions(){},showTpError(){},
    ensureTrainpilotModelsPresent:async()=>true,
    fetchJson:async(path,options)=>{
      if(path==='/api/trainpilot/toml')return {path:'/tmp/config.toml'};
      if(path==='/api/training/preflight')return {missing:[],conflicts:[],warnings:['ComfyUI has running or queued generation jobs.']};
      if(path==='/api/training/runs' && options.method==='POST'){
        if(rejectSubmission)throw Error('queue unavailable');
        return {id:'a'.repeat(32)};
      }
      return {runs:[],paused:false,conflicts:[],active_id:null};
    },
  });
  page.window.fetchJson = page.fetchJson;
  page.window.reviewDataset = async () => true;
  for(const file of ['screen-lifecycle','training-draft','training-workspace'])vm.runInContext(fs.readFileSync(`apps/Portal/static/js/${file}.js`,'utf8'),page);
  await page.window.trainingWorkspace.init();
  assert.equal(node('tp-output').value,'Monday');
  await page.window.trainingWorkspace.preflight();
  assert.match(node('tp-check-service').textContent,/Ready to share the GPU with ComfyUI/);
  assert.match(node('tp-check-service').textContent,/Advisory: ComfyUI/);
  assert.doesNotMatch(node('tp-check-service').textContent,/queue will wait/);
  await page.window.trainingWorkspace.submit();
  assert.equal(context.createTrainingDraft(store).read().output_name,'Monday');
  rejectSubmission=false;
  page.window.reviewDataset = async () => false;
  await page.window.trainingWorkspace.submit();
  assert.equal(context.createTrainingDraft(store).read().output_name,'Monday');
  page.window.reviewDataset = async () => true;
  await page.window.trainingWorkspace.submit();
  assert.equal(context.createTrainingDraft(store).read(),null);
});

test('GPU overrides persist in drafts and exclude unsupported settings', () => {
  const store = storage(), draft = context.createTrainingDraft(store);
  draft.save({family:'flux1', profile:'quick_test', dataset_name:'robot', output_name:'Robot',
    hardware:{train_batch_size:2, network_dim:32, blocks_to_swap:0, api_key:'PRIVATE', gradient_accumulation_steps:99}});
  const saved = draft.read();
  assert.deepEqual(JSON.parse(JSON.stringify(saved.hardware)), {train_batch_size:2, network_dim:32, blocks_to_swap:0});
  assert.equal(JSON.stringify(saved).includes('PRIVATE'), false);
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

function notificationPage(session=storage()) {
  const nodes=new Map(), timers=new Map(), listeners=new Map(), paths=[], opened=[];
  let activity=[{id:'job',kind:'training',state:'running',section:'dpipe',label:'Fixture training',created_at:1}], timerId=0;
  const get=id=>{
    if(!nodes.has(id))nodes.set(id,{hidden:false,children:[],dataset:{},textContent:'',attributes:{},
      replaceChildren(){this.children=[];},append(...children){this.children.push(...children);},
      focus(){this.focused=true;},contains(target){return this===target;},setAttribute(key,value){this.attributes[key]=value;}});
    return nodes.get(id);
  };
  const page=vm.createContext({window:{sessionStorage:session,loadSection:section=>opened.push(section)},
    document:{getElementById:get,createElement:tag=>({...get(tag),children:[]}),addEventListener:(name,fn)=>listeners.set(name,fn),removeEventListener:name=>listeners.delete(name)},
    setTimeout:(callback,delay)=>{timers.set(++timerId,{callback,delay});return timerId;},clearTimeout:id=>timers.delete(id),
    fetchJson:async path=>{paths.push(path);return {items:activity};},
  });
  vm.runInContext(fs.readFileSync('apps/Portal/static/js/workspace-status.js','utf8'),page);
  return {page,get,timers,listeners,paths,opened,setItems:items=>activity=items,
    transition:state=>{activity=[{...activity[0],state}];},
    tick:async()=>{const entries=[...timers];timers.clear();for(const [,timer] of entries)await timer.callback();},
    start:async()=>{page.window.workspaceStatus.start();await new Promise(resolve=>setImmediate(resolve));}};
}

test('bell shows unread count, preview expires, and history survives refresh without repeating notices', async()=>{
  const session=storage(), first=notificationPage(session); await first.start();
  assert.equal(first.get('workspace-bell').hidden,false);
  assert.equal(first.get('workspace-notifications').hidden,true);
  assert.equal(first.paths.includes('/api/build'),false);
  first.transition('failed');await first.tick();
  assert.equal(first.get('workspace-unread').textContent,'1');
  assert.equal(first.get('workspace-notice').hidden,false);
  assert.match(first.get('workspace-notice-text').textContent,/Failed/);
  assert.ok([...first.timers.values()].every(timer=>timer.delay===5000));
  await first.tick();
  assert.equal(first.get('workspace-notice').hidden,true);
  assert.equal(first.get('workspace-unread').textContent,'1');
  const reloaded=notificationPage(session);reloaded.transition('failed');await reloaded.start();
  assert.equal(reloaded.get('workspace-unread').textContent,'1');
  assert.equal(reloaded.get('workspace-notice').hidden,true);
  reloaded.get('workspace-bell').onclick();
  assert.equal(reloaded.get('workspace-notifications').hidden,false);
  assert.equal(reloaded.get('workspace-unread').hidden,true);
  assert.equal(reloaded.get('workspace-bell').attributes['aria-expanded'],'true');
  assert.equal(reloaded.get('workspace-activity-list').children.length,1);
  const readAgain=notificationPage(session);readAgain.transition('failed');await readAgain.start();
  assert.equal(readAgain.get('workspace-unread').hidden,true);
});

test('open panel reads incoming notices, task links work, and locking hides everything', async()=>{
  const ui=notificationPage();await ui.start();ui.get('workspace-bell').onclick();
  ui.transition('succeeded');await ui.tick();
  assert.equal(ui.get('workspace-unread').hidden,true);
  assert.equal(ui.get('workspace-notice').hidden,true);
  ui.listeners.get('keydown')({key:'Escape'});
  assert.equal(ui.get('workspace-notifications').hidden,true);
  assert.equal(ui.get('workspace-bell').focused,true);
  ui.get('workspace-bell').onclick();ui.listeners.get('pointerdown')({target:{}});
  assert.equal(ui.get('workspace-notifications').hidden,true);
  ui.transition('running');await ui.tick();ui.transition('failed');await ui.tick();
  ui.get('workspace-notice-view').onclick();
  assert.deepEqual(ui.opened,['dpipe']);
  assert.equal(ui.get('workspace-unread').hidden,true);
  ui.page.window.workspaceStatus.stop();
  for(const id of ['workspace-bell','workspace-notice','workspace-notifications'])assert.equal(ui.get(id).hidden,true);
  assert.equal(ui.timers.size,0);assert.equal(ui.listeners.size,0);
});

test('preview interaction pauses its timeout and dismissal retains unread history', async()=>{
  const ui=notificationPage();await ui.start();ui.transition('failed');await ui.tick();
  assert.equal(ui.timers.size,2);
  ui.get('workspace-notice').onfocusin();assert.equal(ui.timers.size,1);
  ui.get('workspace-notice').onfocusout();assert.equal(ui.timers.size,2);
  ui.get('workspace-notice-dismiss').onclick();
  assert.equal(ui.get('workspace-notice').hidden,true);
  assert.equal(ui.get('workspace-unread').textContent,'1');
  assert.equal(ui.timers.size,1);
});

test('notification history is bounded and corrupt stored entries are ignored',()=>{
  const session=storage();session.setItem('lora-pilot.activity.v1',JSON.stringify({notifications:[null,{},'bad']}));
  const tracker=context.createActivityTracker(session,()=>2000);
  assert.equal(tracker.notifications.length,0);
  tracker.update(Array.from({length:30},(_,i)=>({...item('failed',String(i)),label:'Model '+i,created_at:3})));
  assert.equal(tracker.notifications.length,20);
  tracker.markRead();
  assert.ok(tracker.notifications.every(notice=>!notice.unread));
});


test('guided drafts retain each newly supported model family', () => {
  const draft = context.createTrainingDraft(storage());
  for (const family of ['sd15', 'sd35_medium', 'sd35_large', 'anima', 'lumina2', 'hunyuan_image21']) {
    draft.save({family, profile:'regular', dataset_name:'1_sample', output_name:'portrait'});
    assert.equal(draft.read().family, family);
  }
});


test('base model choices survive drafts without accepting paths or unrelated fields', () => {
  const store = storage(), draft = context.createTrainingDraft(store);
  const spec = {family:'sdxl', profile:'regular', dataset_name:'portraits', output_name:'Portrait'};
  draft.save({...spec, base_model:'realvisxl-v5'});
  assert.equal(context.createTrainingDraft(store).read().base_model, 'realvisxl-v5');
  draft.save({...spec, base_model:'/outside/model.safetensors'});
  assert.equal(draft.read().base_model, '');
  draft.save(spec);
  assert.equal(draft.read().base_model, '');
});
