/* Known failures get a next action; unfamiliar failures retain their details. */
function taskAdvice(message) {
  const text = String(message || '');
  if (/out of memory|cuda.*alloc|CUBLAS_STATUS_ALLOC_FAILED/i.test(text)) return {title:'GPU memory is exhausted.',help:'Review batch size and model settings, and stop GPU workloads you do not need.',action:'Review training settings',section:'trainpilot'};
  if (/no space left|disk quota|insufficient.*space|not enough.*space/i.test(text)) return {title:'Workspace storage is full.',help:'Review storage usage before retrying.',action:'Open storage',section:'storage'};
  if (/gated|401|403|unauthorized|access.*(?:denied|restricted)|repository not found/i.test(text)) return {title:'Model access could not be verified.',help:'Check your Hugging Face token and accept any access agreement on the model’s page.',action:'Check Hugging Face access',section:'settings'};
  if (/required model.*(?:missing|removed)|model.*not found|checkpoint.*not found/i.test(text)) return {title:'A required model is missing.',help:'Check the required files in Models, then retry.',action:'Open Models',section:'models'};
  if (/ModuleNotFoundError|No module named|ImportError/i.test(text)) return {title:'A service dependency could not be loaded.',help:'Check the affected service and its logs before retrying.',action:'Open Services',section:'services'};
  return {title:'The task could not finish.',help:'Review the technical details before retrying.'};
}
function taskError(message) {
  const advice = taskAdvice(message), box = document.createElement('div'); box.className='task-error';
  const heading=document.createElement('strong'); heading.textContent=advice.title;
  const help=document.createElement('p'); help.textContent=advice.help; box.append(heading,help);
  if(advice.action){const button=document.createElement('button');button.type='button';button.className='journey-link';button.textContent=advice.action;button.onclick=()=>{
    if(advice.section==='settings') window.pendingSettingsTab='connections';
    window.loadSection(advice.section);
  };box.append(button);}
  const details=document.createElement('details'), summary=document.createElement('summary'), text=document.createElement('pre');
  summary.textContent='Technical details';text.textContent=String(message || 'No additional details.');text.style.whiteSpace='pre-wrap';text.style.overflowWrap='anywhere';details.append(summary,text);box.append(details);return box;
}
function trainingTimeLabel(timing) {
  if(!timing)return '';
  const duration=value=>{const total=Math.max(0,Math.round(value));return total>=3600?`${Math.floor(total/3600)}h ${Math.floor(total%3600/60)}m`:total>=60?`${Math.floor(total/60)}m ${total%60}s`:`${total}s`;};
  const parts=[timing.stage];
  if(Number.isFinite(timing.elapsed_seconds)) parts.push(`${duration(timing.elapsed_seconds)} elapsed`);
  if(Number.isFinite(timing.remaining_seconds))parts.push(`about ${duration(timing.remaining_seconds)} remaining`);
  else if(timing.stage==='Training')parts.push('Estimating remaining time…');
  return parts.join(' · ');
}
