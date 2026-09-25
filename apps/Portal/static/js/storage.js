window.storagePage = (() => {
  let storageScreen=null, data=null, selected=new Set(), plan=null, busy=false;
  const bytes=value=>value===0?'0 B':formatBytes(value);
  const files=count=>`${count} ${count===1?'file':'files'}`;
  const $=id=>document.getElementById(id);
  const node=(tag,text,cls='')=>{const el=document.createElement(tag);el.textContent=text;el.className=cls;return el;};
  const api=(screen,path,body)=>screen.json(`/api/storage${path}`,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  function selection(){
    const items=data?.candidates.filter(item=>selected.has(item.id)) || [];
    $('storage-selected').textContent=items.length?`${items.length} ${items.length===1?'item':'items'} selected · about ${bytes(items.reduce((sum,item)=>sum+item.reclaim_bytes,0))} reclaimable`:'No files selected.';
    $('storage-review').disabled=busy || !items.length || !!data?.warnings.length;
  }
  function render(){
    const query=$('storage-search').value.toLowerCase(), category=$('storage-filter').value;
    const items=data.candidates.filter(item=>(!category || item.category===category) && item.label.toLowerCase().includes(query));
    $('storage-count').textContent=`${items.length} cleanup items${items.length>100?' · showing the first 100; refine your search to see others':''}`;
    const list=$('storage-items');list.replaceChildren();
    if(!items.length)list.append(node('p','No eligible files match. Only private files from finished guided runs are offered here.','journey-note'));
    for(const item of items.slice(0,100)){
      const row=node('label','','storage-item'), check=document.createElement('input');check.type='checkbox';check.checked=selected.has(item.id);
      check.setAttribute('aria-label',`Select ${item.label}`);
      check.onchange=()=>{if(check.checked)selected.add(item.id);else selected.delete(item.id);selection();};
      const info=node('span');info.append(node('strong',item.label),node('small',`${files(item.file_count)} · ${bytes(item.size_bytes)} · about ${bytes(item.reclaim_bytes)} reclaimable`));
      row.append(check,info);list.append(row);
    }
    selection();
  }
  async function scan(message=''){
    const screen=storageScreen.latest("operation");busy=true;
    $('storage-scan').disabled=true;$('storage-review').disabled=true;$('storage-status').textContent='Scanning workspace storage…';$('storage-error').replaceChildren();
    try{
      const result=await api(screen,'');if(!screen.active || !$('storage-page'))return;
      data=result;selected=new Set();plan=null;
      $('storage-disk').textContent=typeof data.disk.free==='number'
        ? `${data.disk.estimated?'About ':''}${bytes(data.disk.free)} free of ${bytes(data.disk.total)}`
        : data.disk.total>0 ? `${bytes(data.disk.total)} capacity · ${typeof data.disk.used==='number'?`${bytes(data.disk.used)} in workspace`:'usage unavailable'}`
        : `${typeof data.disk.used==='number'?`${bytes(data.disk.used)} used · `:''}capacity unavailable`;
      $('storage-disk').title=data.disk.note || '';
      $('storage-categories').replaceChildren(...data.categories.map(item=>{const card=node('div','','journey-surface');card.append(node('strong',item.name),node('p',bytes(item.size_bytes)));return card;}));
      $('storage-status').textContent=[message,...data.warnings].filter(Boolean).join(' ') || 'Scan complete. Review items below to choose what to remove.';
      busy=false;render();
    }catch(error){if(screen.active && $('storage-page')){$('storage-error').replaceChildren(taskError(error.message));$('storage-status').textContent='Storage scan unavailable.';data=null;$('storage-items').replaceChildren();}}
    finally{if(screen.active && $('storage-page')){busy=false;$('storage-scan').disabled=false;selection();}}
  }
  async function review(){
    if(busy)return;busy=true;
    const screen=storageScreen.latest("operation");$('storage-review').disabled=true;$('storage-error').replaceChildren();
    try{
      const result=await api(screen,'/preview',{ids:[...selected]});if(!screen.active || !$('storage-page'))return;
      plan=result;$('storage-cancel').disabled=false;$('storage-confirm-check').disabled=false;$('storage-review-total').textContent=`${files(plan.file_count)} · about ${bytes(plan.reclaim_bytes)} reclaimable. This preview expires in five minutes.`;
      $('storage-review-items').replaceChildren(...plan.items.map(item=>node('p',`${item.label}: ${files(item.file_count)} · ${bytes(item.size_bytes)}`)));
      $('storage-confirm-check').checked=false;$('storage-confirm').disabled=true;$('storage-confirm-status').textContent='';$('storage-review-dialog').showModal();
    }catch(error){if(screen.active && $('storage-page'))$('storage-error').replaceChildren(taskError(error.message));}
    finally{if(screen.active && $('storage-page')){busy=false;selection();}}
  }
  async function remove(){
    if(!plan || !$('storage-confirm-check').checked)return;
    const screen=storageScreen.latest("operation"), token=plan.token;plan=null;
    $('storage-confirm').disabled=true;$('storage-cancel').disabled=true;$('storage-confirm-check').disabled=true;$('storage-confirm-status').textContent='Rechecking files and removing your selection…';
    try{
      const result=await api(screen,'/cleanup',{token});if(!screen.active || !$('storage-page'))return;
      $('storage-review-dialog').close();await scan(`${result.message} ${files(result.removed_files)} removed; estimated reclaimed size ${bytes(result.estimated_reclaimed_bytes)}.`);
    }catch(error){if(screen.active && $('storage-page')){$('storage-confirm-status').textContent=`${error.message} Close this review and scan again before retrying.`;}}
    finally{if(screen.active && $('storage-page')){$('storage-cancel').disabled=false;$('storage-confirm-check').disabled=false;}}
  }
  function init(screen = window.createScreenLifecycle()){
    storageScreen=screen;busy=false;data=null;plan=null;selected=new Set();
    $('storage-scan').onclick=()=>scan();$('storage-search').oninput=()=>{if(data)render();};$('storage-filter').onchange=()=>{if(data)render();};
    $('storage-review').onclick=review;$('storage-confirm').onclick=remove;
    $('storage-cancel').onclick=()=>{$('storage-review-dialog').close();plan=null;};
    $('storage-confirm-check').onchange=()=>{$('storage-confirm').disabled=!plan || !$('storage-confirm-check').checked;};
    $('storage-review-dialog').oncancel=event=>{if($('storage-cancel').disabled)event.preventDefault();};
    scan();
  }
  function stop(){storageScreen?.dispose();if($('storage-review-dialog')?.open)$('storage-review-dialog').close();}
  return {init,stop};
})();
