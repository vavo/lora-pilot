const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const read = name => fs.readFileSync(`apps/Portal/static/js/${name}.js`, 'utf8');
function extract(name, start, end) {
  const text=read(name), a=text.indexOf(start), b=text.indexOf(end,a+start.length);
  assert.ok(a>=0 && b>a); return text.slice(a,b);
}
function lifecycle(page) {
  Object.assign(page, {AbortController, DOMException});
  page.window.fetchJson = page.fetchJson;
  vm.runInContext(read('screen-lifecycle'), page);
}
function dom() {
  const nodes=new Map();
  const node=id=>{
    if(!nodes.has(id))nodes.set(id,{id,value:'',checked:false,disabled:false,dataset:{},handlers:{},textContent:'',
      addEventListener(event,handler){this.handlers[event]=handler;},setAttribute(){},focus(){},select(){},
      classList:{add(){},remove(){},toggle(){}},querySelectorAll:()=>[]});
    return nodes.get(id);
  };
  return {node,document:{getElementById:node,querySelectorAll:()=>[]}};
}

test('the latest navigation wins even when older fetches finish later',async()=>{
  const pending={},links=['models','datasets'].map(name=>({name,classList:{remove(){},add(){page.highlight=name;}},removeAttribute(){},setAttribute(){}}));
  const page=vm.createContext({activeScreen:null,controlPilotUnlocked:true,contentEl:{innerHTML:'',querySelectorAll:()=>[]},currentSection:'dashboard',viewCache:{},
    viewMap:{models:{view:'models',init(){}},datasets:{view:'datasets',init(){}}},window:{stopDashboard(){},scrollTo(){}},
    document:{querySelectorAll:()=>links,querySelector:s=>links.find(l=>s.includes(l.name))},history:{replaceState(a,b,hash){page.hash=hash;}},
    setCopilotSectionVisibility(){},closeSidebar(){},fetch:path=>new Promise(resolve=>pending[path]=resolve)});
  lifecycle(page);
  vm.runInContext(extract('main','async function loadSection(section) {','\nfunction setCopilotSectionVisibility'),page);
  const first=page.loadSection('models'),last=page.loadSection('datasets');
  pending.datasets({ok:true,text:async()=>'DATASETS'});await last;
  pending.models({ok:true,text:async()=>'MODELS'});await first;
  assert.equal(page.contentEl.innerHTML,'DATASETS');assert.equal(page.hash,'#datasets');assert.equal(page.highlight,'datasets');
});

test('login loads saved settings before unlocking and opening a screen',async()=>{
  const calls=[];const page=vm.createContext({authPassword:{value:'fixture'},authLoginBtn:{},authStatus:{},currentSection:null,initialSection:'dashboard',controlPilotUnlocked:false,
    fetchJson:async()=>{calls.push('login');return{};},setAuthGateVisible:()=>calls.push('unlock'),initShutdownNotice(){},loadSection:()=>calls.push('screen'),
    window:{workspaceStatus:{start(){}},refreshControlPilotSettings:async()=>calls.push('settings')}});
  const body=extract('main','  authLoginBtn.addEventListener("click", async () => {','\n  });').replace('  authLoginBtn.addEventListener("click", async () => {','async function loginProbe(){')+'\n}';
  vm.runInContext(body,page);await page.loginProbe();assert.deepEqual(calls,['login','settings','unlock','screen']);
  page.window.refreshControlPilotSettings=async()=>{throw Error('Settings unavailable');};calls.length=0;
  await page.loginProbe();assert.deepEqual(calls,['login']);assert.match(page.authStatus.textContent,/Settings unavailable/);
});

test('saving a credential or shutdown defaults preserves edits in other settings groups',async()=>{
  const {node,document}=dom();const themes=[{value:'dark',checked:false},{value:'light',checked:true}];document.querySelectorAll=s=>s.includes('settings-theme')?themes:[];
  const page=vm.createContext({window:{refreshControlPilotSettings(){throw Error('Must not reset appearance');}},document,URL,location:{origin:'http://localhost'},
    fetchJson:async path=>path==='/api/settings'?{theme:'light',shutdown_default_hours:0,comfy_access:{}}:{set:true}});
  lifecycle(page);
  vm.runInContext(read('settings'),page);await page.window.initSettings();
  themes[0].checked=true;themes[1].checked=false;node('settings-shutdown-hours').value='6';node('settings-copilot-token').value='unfinished';node('settings-hf-token').value='fixture';
  await node('settings-hf-save').handlers.click();assert.equal(node('settings-hf-token').value,'');
  assert.equal(node('settings-copilot-token').value,'unfinished');assert.equal(node('settings-shutdown-hours').value,'6');assert.equal(themes[0].checked,true);
  await node('settings-shutdown-save').handlers.click();assert.equal(themes[0].checked,true);assert.equal(node('settings-copilot-token').value,'unfinished');
});

function advancedPage() {
  const {node,document}=dom(),requests=[];let finish;
  const page=vm.createContext({window:{},document,localStorage:{setItem(){}},setTimeout:()=>1,clearTimeout(){},
    refreshDpipeTensorBoardStatus:async()=>{},confirm:()=>false,fetchJson:async(path,options)=>{
      requests.push([path,JSON.parse(options.body)]);
      if(path.endsWith('validate'))return new Promise(resolve=>finish=resolve);
      return{};
    }});
  lifecycle(page);
  vm.runInContext(read('dpipe'),page);
  vm.runInContext('dpScreen = window.createScreenLifecycle()', page);
  return {page,node,requests,finish:()=>finish({missing:[]})};
}
test('advanced training submits a single captured configuration and suppresses duplicate starts',async()=>{
  const {page,node,requests,finish}=advancedPage();node('dp-dataset').value='dataset-A';node('dp-transformer').value='model-A';
  const started=page.window.startDpipe();assert.equal(node('dp-start').disabled,true);
  node('dp-dataset').value='dataset-B';node('dp-transformer').value='model-B';await page.window.startDpipe();finish();await started;
  assert.equal(requests.length,2);assert.equal(requests[1][1].dataset_path,'dataset-A');assert.equal(requests[1][1].transformer_path,'model-A');assert.equal(node('dp-start').disabled,false);
});
test('leaving advanced training during validation prevents a later launch',async()=>{
  const {page,requests,finish}=advancedPage();const started=page.window.startDpipe();page.window.stopDpipeLog();finish();await started;assert.equal(requests.length,1);
});
test('advanced training renders running and terminal state with matching actions',()=>{
  const {page,node}=advancedPage();page.renderDpipeState({state:'running'});assert.equal(node('dp-start').disabled,true);assert.equal(node('dp-stop').disabled,false);
  page.renderDpipeState({state:'failed'});assert.match(node('dp-status').textContent,/failed/);assert.equal(node('dp-start').disabled,false);assert.equal(node('dp-stop').disabled,true);
  page.renderDpipeState({state:'succeeded'});assert.match(node('dp-status').textContent,/completed/);
});

test('lost download jobs fail with recovery guidance instead of polling forever',async()=>{
  const page=vm.createContext({window:{addEventListener(){}},document:{},confirm:()=>true,alert(){},setTimeout,clearTimeout,DOMException,
    fetchJson:async path=>path.endsWith('preflight')?{missing:[{model_name:'fixture'}]}:{state:'idle'}});
  lifecycle(page);
  vm.runInContext(read('trainpilot'),page);
  vm.runInContext('tpScreen = window.createScreenLifecycle()', page);page.setModelDownloadUI=()=>{};
  await assert.rejects(page.ensureTrainpilotModelsPresent({},new AbortController().signal),/Download status was lost/);
});
test('cancelling training preparation interrupts the polling delay',async()=>{
  const page=vm.createContext({window:{addEventListener(){}},document:{},setTimeout,clearTimeout,DOMException});vm.runInContext(read('trainpilot'),page);
  const controller=new AbortController(),waiting=page.waitForModelPoll(30000,controller.signal);controller.abort();await assert.rejects(waiting,{name:'AbortError'});
});
test('JSON API helper rejects invalid content and accepts explicit no-content responses',async()=>{
  let response;const page=vm.createContext({window:{},fetch:async()=>response});vm.runInContext(read('utils'),page);
  for(const [mime,text] of [['text/html','<html>proxy</html>'],['application/json','{broken'],['application/json','']]){
    response={ok:true,status:200,headers:{get:()=>mime},text:async()=>text};await assert.rejects(page.window.fetchJson('/api/test'));
  }
  response={ok:true,status:204};assert.equal(await page.window.fetchJson('/api/test'),null);
  response={ok:true,status:200,headers:{get:()=> 'application/problem+json; charset=utf-8'},text:async()=>'{"ok":true}'};
  assert.equal((await page.window.fetchJson('/api/test')).ok,true);
});

test('a late Settings refresh cannot replace preferences from a new visit', async()=>{
  const {document}=dom();let finish;const old=new Promise(resolve=>finish=resolve);
  const page=vm.createContext({window:{},document,URL,location:{origin:'http://localhost'},fetchJson:path=>path==='/api/settings'?old:Promise.resolve({set:true})});
  lifecycle(page);vm.runInContext(read('settings'),page);
  const first=page.window.createScreenLifecycle(), pending=page.window.initSettings(first);
  first.dispose();page.window.fetchJson=async path=>path==='/api/settings'?{theme:'dark',comfy_access:{}}:{set:true};
  await page.window.initSettings(page.window.createScreenLifecycle());
  finish({theme:'light',comfy_access:{}});await pending;
  assert.equal(page.window.controlPilotSettings.theme,'dark');
});

test('view-load errors render a text card and unsupported route names use Dashboard',async()=>{
  for (const requested of ['models','<img src=x onerror=alert(1)>','%3Csvg%20onload=alert(1)%3E','__proto__','constructor']) {
    let rendered, requestedView;
    const content={querySelectorAll:()=>[],replaceChildren(node){rendered=node;}};
    Object.defineProperty(content,'innerHTML',{set(){assert.fail('Failure messages must never use an HTML sink');}});
    const page=vm.createContext({activeScreen:null,controlPilotUnlocked:true,contentEl:content,currentSection:null,viewCache:{},
      viewMap:{dashboard:{view:'/views/dashboard.html',init(){}},models:{view:'/views/models.html',init(){}}},
      window:{scrollTo(){}},document:{querySelectorAll:()=>[],querySelector:()=>null,createElement:()=>({})},
      history:{replaceState(){}},setCopilotSectionVisibility(){},closeSidebar(){},
      fetch:async path=>{requestedView=path;throw Error('<svg onload=alert(1)>');}});
    lifecycle(page);
    vm.runInContext(extract('main','async function loadSection(section) {','\nfunction setCopilotSectionVisibility'),page);
    await page.loadSection(requested);
    const route=requested==='models'?'models':'dashboard';
    assert.equal(requestedView,`/views/${route}.html`);
    assert.equal(rendered.className,'card');
    assert.equal(rendered.textContent,`Could not load ${route}. Select the page again to retry.`);
  }
});

test('View run opens configuration and logs for queued runs without starting another run',async()=>{
  const {node,document}=dom();let focused=false,scrolled=false,refreshed=false;
  const details={open:false,scrollIntoView(){scrolled=true;},querySelector:()=>({focus(){focused=true;}})};
  node('tp-run-config').closest=()=>details;
  const page=vm.createContext({document,$:node,trainingScreen:{active:true},preferSetup:true,selected:null,
    comparisonError:'old error',tpDismissedRunId:'previous',refresh(){refreshed=true;},
    api(){assert.fail('Viewing a run must not mutate the training queue');}});
  vm.runInContext(extract('training-workspace','  async function historyAction(event) {','\n  async function stopRun()'),page);
  const control={dataset:{runAction:'view',runId:'queued-run'},disabled:false};
  await page.historyAction({target:{closest:()=>control}});
  assert.equal(page.selected,'queued-run');assert.equal(page.preferSetup,false);
  assert.equal(details.open,true);assert.equal(node('tp-diagnostics').open,true);
  assert.ok(focused && scrolled && refreshed);assert.equal(control.disabled,false);
  assert.match(node('tp-run-config').textContent,/Loading/);
});
