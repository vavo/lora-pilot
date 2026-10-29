const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('apps/TagPilot/index.html', 'utf8');
function source(name) {
  const match = html.match(new RegExp(`        (?:async )?function ${name}\\([^]*?^        }`, 'm'));
  assert.ok(match, `Missing ${name}`);
  return match[0];
}
function node() {
  const children = new Map();
  return {
    style: {}, disabled: false, textContent: '', children: [], dataset: {},
    classList: {toggle(){}, add(){}, remove(){}},
    set innerHTML(value) { this.children = []; },
    setAttribute(name, value) { this[name] = value; }, removeAttribute(name) { delete this[name]; },
    addEventListener(){}, focus(){this.focused = true;}, scrollIntoView(){},
    appendChild(child) {this.children.push(child);},
    querySelector(selector) {if (!children.has(selector)) children.set(selector, node()); return children.get(selector);},
    querySelectorAll() {return [];},
  };
}
function setup(length) {
  const nodes = new Map();
  const get = id => {if (!nodes.has(id)) nodes.set(id,node());return nodes.get(id);};
  const page = vm.createContext({
    dataset: Array.from({length}, (_,i)=>({id:`item-${i+1}`, file:{name:`photo-${i+1}.png`}, tags:`tag ${i+1}`, type:'tags'})),
    currentPage:0, IMAGES_PER_PAGE:50, currentPreviewItemId:null, previewReturnFocus:null,
    document:{getElementById:get,createElement:node, activeElement:node()},
    imageGrid:node(), taggerSection:node(), tagViewerSection:node(), placeholder:node(),
    exportButton:node(), saveWorkspaceButton:node(), saveTrainingButton:node(), tagAllButton:node(), captionAllButton:node(), clearTagsButton:node(), resetButton:node(),
    previewModal:node(), previewImage:node(), previewClose:node(), cropModal:node(), tagSettingsModal:node(), captionSettingsModal:node(), settingsModal:node(),
    getFileObjectUrl:file=>`blob:${file.name}`, revokeFileObjectUrl(){}, ensureDatasetItemIds(){},
    rendered:[], renderTagsInCard(wrapper,id){page.rendered.push({id,tags:page.dataset.find(item=>item.id===id).tags});},
    renderTagViewer(){},setSingleProcessing(){}, console,
  });
  for (const name of ['findDatasetItemById','findDatasetItemIndexById','pageBounds','render','changePage','removeImage','showPreview','hidePreview','navigatePreview','handleDialogKeydown','cropPreviewImage','runBatchProcessing','updateBatchProgress','shouldProcessBatchItem']) {
    vm.runInContext(source(name),page);
  }
  return {page,get};
}
test('50-image pagination handles empty, exact and partial pages',()=>{
  for (const [count,pages] of [[0,1],[50,1],[51,2],[100,2],[101,3]]) {
    const {page}=setup(count);
    assert.equal(page.pageBounds().pages,pages);
    page.currentPage=999;
    const bounds=page.pageBounds();
    assert.equal(page.currentPage,pages-1);
    assert.equal(bounds.end,count);
    assert.ok(bounds.end-bounds.start<=50);
  }
});
test('render bounds cards and preserves edits across page navigation',()=>{
  const {page,get}=setup(51);
  page.render();
  assert.equal(page.imageGrid.children.length,50);
  assert.equal(get('page-prev').disabled,true);
  page.dataset[0].tags='Edited caption';
  page.changePage(1);
  assert.equal(page.imageGrid.children.length,1);
  assert.equal(page.rendered.at(-1).id,'item-51');
  assert.equal(get('page-status').textContent,'51–51 of 51 · Page 2 of 2');
  assert.equal(get('page-next').disabled,true);
  page.rendered=[];
  page.changePage(-1);
  assert.equal(page.rendered[0].tags,'Edited caption');
});
test('removing the final card on page two returns to the populated first page',()=>{
  const {page,get}=setup(51);
  page.currentPage=1;
  page.removeImage('item-51');
  assert.equal(page.currentPage,0);
  assert.equal(page.imageGrid.children.length,50);
  assert.equal(get('image-count').textContent,'50 images');
});
test('preview buttons traverse the entire dataset and stop at each boundary',()=>{
  const {page,get}=setup(51);
  page.showPreview('blob:50','item-50');
  page.navigatePreview(1);
  assert.equal(page.currentPreviewItemId,'item-51');
  assert.equal(get('preview-next').disabled,true);
  page.navigatePreview(1);
  assert.equal(page.currentPreviewItemId,'item-51');
  page.showPreview('blob:1','item-1');
  assert.equal(get('preview-prev').disabled,true);
  page.navigatePreview(-1);
  assert.equal(page.currentPreviewItemId,'item-1');
  assert.equal(page.previewImage.alt,'photo-1.png');
});
test('preview arrows are scoped to an open preview and do not intercept typing',()=>{
  const {page}=setup(51);
  const event={key:'ArrowRight',target:{closest:()=>null},preventDefault(){this.prevented=true;}};
  page.handleDialogKeydown(event);
  assert.equal(event.prevented,undefined);
  page.showPreview('blob:50','item-50');
  page.handleDialogKeydown({...event,target:{closest:()=>({})}});
  assert.equal(page.currentPreviewItemId,'item-50');
  page.handleDialogKeydown(event);
  assert.equal(page.currentPreviewItemId,'item-51');
  assert.equal(event.prevented,true);
  page.cropModal.style.display='flex';
  page.handleDialogKeydown({...event,key:'ArrowLeft'});
  assert.equal(page.currentPreviewItemId,'item-51');
});
test('crop from a navigated preview targets the displayed image and closes preview',()=>{
  const {page}=setup(51);
  page.openCrop=id=>{page.cropId=id;};
  page.showPreview('blob:50','item-50');page.navigatePreview(1);page.cropPreviewImage();
  assert.equal(page.cropId,'item-51');
  assert.equal(page.previewModal.style.display,'none');
  assert.equal(page.currentPreviewItemId,null);
});
test('bulk processing includes all pages and honors skip, append, overwrite selection',async()=>{
  const {page}=setup(101);
  page.currentTriggerWord='';page.isBlankOrTriggerOnly=text=>!text;
  assert.equal(page.shouldProcessBatchItem(page.dataset[100],'ignore'),false);
  assert.equal(page.shouldProcessBatchItem(page.dataset[100],'append'),true);
  assert.equal(page.shouldProcessBatchItem(page.dataset[100],'overwrite'),true);
  const seen=[];page.showNotification=()=>{};
  const progress=node();
  await page.runBatchProcessing({configPanel:node(),progressPanel:node(),progressBar:node(),progressText:progress,closeModal(){},completeMessage:'Done',processItem:async item=>seen.push(item.id)});
  assert.equal(seen.length,101);assert.equal(seen.at(-1),'item-101');
  assert.equal(progress.textContent,'101 / 101');
});
test('photo import pairs text sidecars and skips duplicates without any network calls',async()=>{
  const {page}=setup(0);
  page.currentTriggerWord='subject';
  page.showLoader=()=>{};page.hideLoader=()=>{};page.showNotification=()=>{};
  page.calculateFileHash=async file=>file.hash;
  page.createDatasetItem=(file,tags,type)=>({file,tags,type,id:`item-${page.dataset.length+1}`});
  page.withTriggerWord=(text,word)=>`${word}, ${text}`;
  vm.runInContext(source('handleImageUpload'),page);
  const photo={name:'sample.png',hash:'image-bytes'};
  const sidecar={name:'sample.txt',text:async()=>'imported caption, café'};
  await page.handleImageUpload({target:{files:[photo,sidecar],value:'selected'}});
  assert.equal(page.dataset.length,1);
  assert.equal(page.dataset[0].tags,'subject, imported caption, café');
  await page.handleImageUpload({target:{files:[photo,sidecar],value:'selected'}});
  assert.equal(page.dataset.length,1);
});

test('local generation uses TagPilot API and requires no external provider or browser key', async()=>{
  const calls=[];
  const page=vm.createContext({FormData, getImageMimeType:()=> 'image/png',
    fetch:async(url,options)=>{calls.push({url,options});return {ok:true,json:async()=>({text:'A local caption.'})};}});
  vm.runInContext(source('generateImageText'),page);
  const result=await page.generateImageText(new Blob(['image']), 'Describe it', 'local', 'caption');
  assert.equal(result,'A local caption.');
  assert.equal(calls[0].url,'/api/tagpilot/generate');
  assert.equal(calls[0].options.body.get('mode'),'caption');
  assert.equal(calls[0].options.body.get('provider'),'local');
});

test('saving uses the existing ZIP API and opens training only after success', async()=>{
  const calls=[], messages=[], notices=[];
  const page=vm.createContext({dataset:[{tags:'person, portrait'}],currentTriggerWord:'person',
    datasetNameInput:{value:'1_generated'},FormData,
    datasetArchive:async()=>new Blob(['zip']),showLoader(){},hideLoader(){},
    showNotification:text=>notices.push(text),isBlankOrTriggerOnly:text=>text==='person',
    parseResponseError:async()=> 'Save rejected',console:{error(){}},
    window:{location:{origin:'https://pilot.test'},parent:{postMessage:(...args)=>messages.push(args)}},
    fetch:async(url)=>{calls.push(url);return {ok:true,json:async()=>({name:'1_generated'})};}});
  vm.runInContext(source('handleSaveToWorkspace'),page);
  page.dataset[0].tags='person'; await page.handleSaveToWorkspace(true);
  assert.equal(calls.length,0); assert.equal(messages.length,0);
  page.dataset[0].tags='person, portrait';
  page.fetch=async()=>({ok:false}); await page.handleSaveToWorkspace(true);
  assert.equal(messages.length,0); assert.match(notices.at(-1),/Save rejected/);
  page.fetch=async url=>{calls.push(url);return {ok:true,json:async()=>({name:'1_generated'})};};
  await page.handleSaveToWorkspace(true);
  assert.equal(calls[0],'/api/tagpilot/save?name=1_generated');
  assert.equal(messages[0][0].dataset,'1_generated');
  assert.equal(messages[0][1],'https://pilot.test');
});

test('archive shares export/save logic and keeps provenance, edited trigger and annotation modes',async()=>{
  const files={};
  const page=vm.createContext({dataset:[{file:{name:'001.png'},tags:'edited, portrait',type:'caption'}],
    currentTriggerWord:'edited',generationRecord:{id:'job',spec:{trigger:'original'}},
    isBlankOrTriggerOnly:text=>!text || text==='edited',
    JSZip:class {file(name,data){files[name]=data;}async generateAsync(){return 'zip';}}});
  vm.runInContext(source('datasetArchive'),page);
  await page.datasetArchive();
  assert.equal(files['001.txt'],'edited, portrait');
  const record=JSON.parse(files['generation.json']);
  assert.equal(record.spec.trigger,'original');assert.equal(record.preparation.trigger,'edited');
  assert.equal(record.preparation.formats['001.png'],'caption');
  delete files['001.txt'];page.dataset[0].tags='edited';await page.datasetArchive();
  assert.equal(files['001.txt'],undefined);
});

test('ControlPilot accepts handoff only from its active same-origin TagPilot frame',()=>{
  const frame={contentWindow:{}}, handlers={}, opened=[];
  let cleanup;
  const screen={active:true,onCleanup:fn=>cleanup=fn};
  const page=vm.createContext({window:{location:{origin:'https://pilot.test'},
    addEventListener:(name,fn)=>handlers[name]=fn,removeEventListener:name=>delete handlers[name],
    loadSection:name=>opened.push(name)},document:{querySelector:()=>frame}});
  vm.runInContext(fs.readFileSync('apps/Portal/static/js/tagpilot.js','utf8'),page);
  page.window.initTagpilot(screen);
  const event={origin:'https://pilot.test',source:frame.contentWindow,data:{type:'tagpilot:train',dataset:'1_generated'}};
  handlers.message({...event,origin:'https://other.test'});handlers.message({...event,source:{}});
  assert.equal(opened.length,0);
  handlers.message(event); assert.equal(page.window.pendingTrainDataset,'1_generated');
  assert.deepEqual(opened,['trainpilot']);
  screen.active=false; handlers.message(event);assert.equal(opened.length,1);
  cleanup();assert.equal(handlers.message,undefined);
});

test('failed local batches report failure instead of claiming caption completion',async()=>{
  const {page}=setup(1);const notices=[];page.showNotification=text=>notices.push(text);page.console={error(){}};
  await page.runBatchProcessing({configPanel:node(),progressPanel:node(),progressBar:node(),progressText:node(),
    closeModal(){},completeMessage:'Captioning complete',processItem:async()=>{throw new Error('Install local model');}});
  assert.equal(notices[0],'1 image(s) failed: Install local model');
});
