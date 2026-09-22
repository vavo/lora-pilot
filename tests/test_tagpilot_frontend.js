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
    exportButton:node(), saveWorkspaceButton:node(), tagAllButton:node(), captionAllButton:node(), clearTagsButton:node(), resetButton:node(),
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
