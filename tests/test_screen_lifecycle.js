const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const read = name => fs.readFileSync(`apps/Portal/static/js/${name}.js`, 'utf8');
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => {resolve=a;reject=b;}); return {promise,resolve,reject}; };
const flush = () => new Promise(resolve => setImmediate(resolve));
function page(extra = {}) {
  const timers = new Map(); let next = 0;
  const context = vm.createContext({AbortController, DOMException, console, URL, ...extra,
    setTimeout: fn => { timers.set(++next,fn); return next; }, clearTimeout: id => timers.delete(id)});
  context.window = context;
  vm.runInContext(read('screen-lifecycle'), context);
  return {context,timers};
}

test('disposing a screen aborts its requests and rejects late success even if transport ignores abort', async () => {
  const pending=deferred(); let signal;
  const {context}=page({fetchJson:(url,options)=>{signal=options.signal;return pending.promise;}});
  const screen=context.createScreenLifecycle(); const request=screen.json('/slow');
  screen.dispose(); assert.equal(signal.aborted,true); pending.resolve({stale:true});
  await assert.rejects(request,{name:'AbortError'});
  await assert.rejects(screen.json('/never-sent'),{name:'AbortError'});
});

test('latest operations cancel competitors while independent reads remain active', async () => {
  const {context}=page({fetchJson:async()=>({})}); const screen=context.createScreenLifecycle();
  const first=screen.latest('document'), independent=screen.latest('status'), next=screen.latest('document');
  assert.equal(first.active,false); assert.equal(independent.active,true); assert.equal(next.active,true);
  screen.dispose(); assert.equal(next.active,false); assert.equal(independent.active,false);
});

test('external cancellation is honored and its listener is released after completion', async () => {
  let signal; const pending=deferred();
  const {context}=page({fetchJson:(url,opts)=>{signal=opts.signal;return pending.promise;}});
  const screen=context.createScreenLifecycle(), external=new AbortController();
  const request=screen.json('/prepare',{signal:external.signal});external.abort();pending.resolve({});
  await assert.rejects(request,{name:'AbortError'});assert.equal(signal.aborted,true);
  const already=new AbortController();already.abort();
  await assert.rejects(screen.json('/never-sent',{signal:already.signal}),{name:'AbortError'});
});

test('polls never overlap and a disposed in-flight poll cannot rearm its timer', async () => {
  const {context,timers}=page();const screen=context.createScreenLifecycle(), pending=deferred();let calls=0;
  screen.poll(async()=>{calls++;await pending.promise;},10);
  assert.equal(calls,1);assert.equal(timers.size,0);
  pending.resolve();await flush();assert.equal(timers.size,1);
  const [id,tick]=[...timers][0];timers.delete(id);tick();assert.equal(calls,2);
  screen.dispose();await flush();assert.equal(timers.size,0);
  screen.timeout(()=>calls++,1);assert.equal(timers.size,0);
});

test('cleanup is idempotent and also cancels timers and custom resources', () => {
  const {context,timers}=page();const screen=context.createScreenLifecycle();let closed=0;
  screen.timeout(()=>assert.fail('timer survived screen'),100);
  screen.onCleanup(()=>closed++);screen.dispose();screen.dispose();
  assert.equal(closed,1);assert.equal(timers.size,0);
  screen.onCleanup(()=>closed++);assert.equal(closed,2);
});

test('view response bodies are stale-protected, not only response headers', async () => {
  const body=deferred();const {context}=page({fetch:async()=>({ok:true,text:()=>body.promise})});
  const screen=context.createScreenLifecycle(), response=screen.text('/view');await flush();
  screen.dispose();body.resolve('STALE HTML');await assert.rejects(response,{name:'AbortError'});
});

test('a cancelled late 401 cannot lock a newer screen', async () => {
  const response=deferred();let locks=0;
  const {context}=page({fetch:()=>response.promise,showControlPilotLogin:()=>locks++});
  vm.runInContext(read('utils'),context);
  const screen=context.createScreenLifecycle(), request=screen.json('/old');
  screen.dispose();response.resolve({ok:false,status:401,text:async()=>'expired'});
  await assert.rejects(request,{name:'AbortError'});assert.equal(locks,0);
});

function nodes() {
  const all=new Map();
  const get=id=>{
    if(!all.has(id))all.set(id,{id,textContent:'',innerHTML:'',value:'',dataset:{},hidden:false,
      classList:{add(){},remove(){},toggle(){}},addEventListener(){},setAttribute(){},querySelectorAll:()=>[]});
    return all.get(id);
  };
  return {get,document:{getElementById:get,querySelectorAll:()=>[]}};
}

test('Docs tab changes and remounts cannot be overwritten by late successes or failures', async () => {
  const dom=nodes(), requests=[];
  const {context}=page({document:dom.document,fetchJson:()=>{const pending=deferred();requests.push(pending);return pending.promise;}});
  vm.runInContext(read('docs'),context);context.renderDocIntoContent=(node,text)=>node.textContent=text;
  const first=context.createScreenLifecycle(), loading=context.initDocs(first);
  const newer=context.loadDocsTab('changelog');requests[1].resolve({content:'CHANGELOG'});await newer;
  requests[0].resolve({content:'OLD README'});await loading;assert.equal(dom.get('docs-content').textContent,'CHANGELOG');
  const oldFailure=context.loadDocsTab('readme');first.dispose();
  const remount=context.initDocs(context.createScreenLifecycle());requests[3].resolve({content:'NEW README'});await remount;
  requests[2].reject(Error('old network failure'));await oldFailure;
  assert.equal(dom.get('docs-content').textContent,'NEW README');assert.equal(dom.get('docs-status').textContent,'');
});

test('service update polling aborts on leave and starts exactly one poll on return', async () => {
  const dom=nodes(), requests=[];
  const {context,timers}=page({document:dom.document,fetchJson:()=>{const pending=deferred();requests.push(pending);return pending.promise;}});
  vm.runInContext(read('services'),context);context.loadServices=async()=>{};
  const first=context.createScreenLifecycle();await context.initServices(first);
  await context.startServiceUpdatePolling('fixture');await context.startServiceUpdatePolling('fixture');assert.equal(requests.length,1);
  first.dispose();const second=context.createScreenLifecycle();await context.initServices(second);await context.startServiceUpdatePolling('fixture');
  requests[1].resolve({state:'running',last_line:'new status'});await flush();
  requests[0].resolve({state:'done',installed_after:'stale'});await flush();
  assert.match(dom.get('svc-update-status-fixture').textContent,/new status/);assert.equal(timers.size,1);
  second.dispose();assert.equal(timers.size,0);
});

test('leaving Dashboard during its initial refresh cannot resurrect a polling loop', async () => {
  const dom=nodes(), requests=[];
  const {context,timers}=page({document:dom.document,fetchJson:()=>{const pending=deferred();requests.push(pending);return pending.promise;}});
  vm.runInContext(read('dashboard'),context);context.bindShutdownInputs=()=>{};
  const screen=context.createScreenLifecycle();await context.initDashboard(screen);
  assert.equal(requests.length,3);screen.dispose();requests.forEach(request=>request.resolve({}));await flush();
  assert.equal(timers.size,0);assert.equal(requests.length,3);
});
