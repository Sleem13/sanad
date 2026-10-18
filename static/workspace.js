import {pageSVG} from '/static/page-layout.js';
import {language,t,applyLanguage,saveLanguage} from '/static/i18n.js';
import {label, num, errorMessage} from '/static/locale.js';
const $ = id => document.getElementById(id);
const state = {token:'', me:null, system:null, docs:[], doc:null, page:null, content:null, dirty:false, zoom:100, dataset:null};
const imageURLs = new Map();
let selectionRequest=0,pageRequest=0;
const imageRequests=new Map();
const navPaths={documents:'M6 3h8l4 4v14H6z M14 3v5h4 M9 12h6 M9 16h6',workflow:'M9 6h11 M9 12h11 M9 18h11 M3 6h1 M3 12h1 M3 18h1',dataset:'M4 6c0-4 16-4 16 0s-16 4-16 0 M4 6v12c0 4 16 4 16 0V6 M4 12c0 4 16 4 16 0',system:'M12 3l3 3 4 1-1 4 1 4-4 1-3 3-3-3-4-1 1-4-1-4 4-1z M15 11a3 3 0 1 1-6 0 3 3 0 0 1 6 0'};
document.querySelectorAll('[data-view]').forEach(b=>{const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',navPaths[b.dataset.view]);svg.append(path);b.prepend(svg);});
const statuses = ['recognized','uncertain','illegible','not_present','not_processed','requires_review'];
function node(tag, text, className,raw=false){const e=document.createElement(tag);if(text!==undefined)e.textContent=raw?text:t(text);if(className)e.className=className;return e;}
function tell(message,error=false){$('notice').textContent=t(message);$('notice').className=error?'error':'';$('notice').hidden=false;}
function uiError(e){return /Failed to fetch|NetworkError/.test(e.message)?errorMessage(e.message,e.status):t(e.message);}
function can(p){return !!state.me?.permissions.includes(p);}
async function api(path,options={}){
 const headers={...(state.token?{Authorization:`Bearer ${state.token}`} : {}),...options.headers};
 if(options.body && !(options.body instanceof FormData))headers['Content-Type']='application/json';
 let r=await fetch(`/api/v1${path}`,{...options,headers});if(r.status===401&&state.me?.roles.includes('super_admin')){const session=await fetch('/api/v1/dev/session',{method:'POST'});if(session.ok)r=await fetch(`/api/v1${path}`,{...options,headers});}
 if(!r.ok){let message;try{const j=await r.json();message=typeof j.detail==='string'?j.detail:JSON.stringify(j.detail);}catch{message=r.statusText;}const error=new Error(errorMessage(message,r.status));error.status=r.status;throw error;}
 return r.json();
}
async function action(fn,button){if(button)button.disabled=true;try{await fn();}catch(e){tell(uiError(e),true);}finally{if(button)button.disabled=false;syncButtons();}}
function dirty(){state.dirty=true;}
function leave(){if(!state.dirty)return true;if(!confirm(t('هل تريد تجاهل التعديلات غير المحفوظة على النص؟')))return false;state.dirty=false;if(state.content)renderRegions();if(state.dataset)$('dataset-text').value=state.dataset.text;return true;}
async function image(path,id){const request=(imageRequests.get(id)||0)+1;imageRequests.set(id,request);const r=await fetch(`/api/v1${path}`,{headers:state.token?{Authorization:`Bearer ${state.token}`}:{}});if(imageRequests.get(id)!==request)return;if(!r.ok)throw new Error(`تعذّر تحميل الصورة (${num(r.status)})`);if(imageURLs.has(id))URL.revokeObjectURL(imageURLs.get(id));const url=URL.createObjectURL(await r.blob());imageURLs.set(id,url);$(id).src=url;$(id).hidden=false;}
function clearWorkspace(){selectionRequest++;pageRequest++;state.docs=[];$('documents').replaceChildren();$('dataset-notes').textContent='';$('dataset-title').textContent=t('اختر عينة');$('dataset-confirm').checked=false;state.doc=null;state.page=null;state.content=null;state.dataset=null;state.dirty=false;$('filename').textContent='اختر مستنداً';$('regions').replaceChildren(node('p','اختر مستنداً لمراجعة نصه.','empty'));$('page-image').hidden=true;$('boxes').replaceChildren();$('source-empty').hidden=false;$('pages').hidden=true;$('jobs').replaceChildren(node('p','اختر مستنداً لعرض مهام معالجته.','empty'));$('version').textContent=t('');$('history').textContent=t('سيظهر سجل الإصدارات بعد التعرف على النص.');$('legacy-banner').hidden=true;$('dataset-image').hidden=true;$('dataset-text').value='';$('dataset-list').replaceChildren();syncButtons();}
function syncButtons(){
 $('page-layout').disabled=!state.content||state.content.is_mock;
 const editable=state.content&&!state.content.is_mock&&state.content.kind!=='approved';
 $('save').disabled=!(editable&&can('edit'));$('approve').disabled=!(editable&&can('approve'));
 $('reopen').disabled=!(state.content?.kind==='approved'&&can('reopen'));
 $('export').disabled=!(state.doc&&can('export'));$('upload-open').disabled=!can('ingest');
 $('assign').disabled=!(state.content&&can('assign'));$('escalate').disabled=!(state.content&&can('edit'));
 $('recognize').disabled=!(state.doc&&(can('ingest')||can('assign'))&&!state.doc.pages.some(p=>p.status==='approved')&&!state.doc.jobs.some(j=>j.status==='running'));$('understanding-start').disabled=!state.content||state.content.is_mock||!can('edit');$('audit').disabled=!can('read_audit');$('dataset-save').disabled=!(state.dataset&&can('edit'));
}
async function connect(token){
 const previous=state.token;state.token=token;
 try{const who=await api('/me');if(!leave()){state.token=previous;return;}clearWorkspace();state.me=who;
 state.system=await api('/system').catch(()=>null);$('connect').textContent=t(who.roles.includes('super_admin')?'المدير العام':who.user);$('connect').disabled=who.roles.includes('super_admin');$('org').closest('label').hidden=who.roles.includes('super_admin');if(who.roles.includes('super_admin'))$('org').value='sanad-workspace';$('token').value='';
 $('connection-dialog').close();$('notice').hidden=true;syncButtons();
 if(can('read_content'))await loadDocs();else{$('documents').replaceChildren(node('p','هذا الحساب لا يملك صلاحية الاطلاع على المستندات.','empty'));}
 renderSystem();if(!who.roles.includes('super_admin'))tell(`تم الدخول باسم ${who.user}.`);
 }catch(e){state.token=previous;throw e;}
}
async function loadDocs(){
 const result=await api(`/documents?q=${encodeURIComponent($('search').value)}&status=${encodeURIComponent($('status').value)}`);
 state.docs=result.items;renderDocs();
}
function renderDocs(){
 $('count').textContent=t(`${num(state.docs.length)} مستند · الأحدث أولاً`);$('documents').replaceChildren();
 if(!state.docs.length)$('documents').append(node('p','لا توجد مستندات. ارفع صورة للبدء.','empty'));
 for(const doc of state.docs){const b=node('button',undefined,`doc-row${state.doc?.id===doc.id?' active':''}`);
 b.append(node('strong',doc.filename,undefined,true),node('small',`${doc.org_scope==='sanad-workspace'?'مساحة سند':doc.org_scope} · ${num(doc.pages)} صفحة${doc.demo?' · تجريبي':''}`),node('span',label(doc.status),`status ${doc.status}`));
 b.onclick=()=>action(async()=>{if(leave()){state.dirty=false;await selectDoc(doc.id);}});$('documents').append(b);}
}
async function selectDoc(id){
 const request=++selectionRequest;const documentResult=await api(`/documents/${id}`);if(request!==selectionRequest)return;state.doc=documentResult;state.content=null;state.page=null;$('filename').textContent=state.doc.filename;
 $('pages').replaceChildren();for(const p of state.doc.pages){const option=node('option',`الصفحة ${num(p.page_no)}`);option.value=p.id;$('pages').append(option);}
 $('pages').hidden=!state.doc.pages.length;renderDocs();renderJobs();
 if(state.doc.pages.length)await loadPage(state.doc.pages[0].id);syncButtons();
}
async function loadPage(id){
 const request=++pageRequest;state.page=id;state.content=null;$('page-image').hidden=true;$('understanding-output').replaceChildren();$('quality-note').hidden=true;$('regions').replaceChildren(node('p','جارٍ تحميل النص…','empty'));$('boxes').replaceChildren();$('legacy-banner').hidden=true;$('version').textContent=t('');$('source-empty').hidden=true;
 await image(`/pages/${id}/image`,'page-image');if(request!==pageRequest)return;
 try{const contentResult=await api(`/pages/${id}/content`);if(request!==pageRequest)return;state.content=contentResult;renderRegions();}
 catch(e){if(e.status===409){$('regions').replaceChildren(node('p','لم يكتمل التعرف بعد. راجع قائمة المهام أدناه. اضغط «تشغيل OCR العربي» لاستخراج النص الحقيقي.','empty'));$('history').textContent=t('لا يوجد إصدار ناتج عن التعرف بعد.');}else throw e;}
 syncButtons();setStage();refreshUnderstanding().catch(()=>{});
}
function setStage(){let stage=state.content?(state.content.kind==='approved'?3:2):1;if(state.doc?.deliveries?.some(d=>d.status==='delivered'))stage=4;document.querySelectorAll('.steps>div').forEach((e,i)=>e.classList.toggle('current',i===stage));}
function renderRegions(){
 const c=state.content;$('quality-note').hidden=Math.min(c.content.width,c.content.height)>=600;$('quality-note').textContent=t('الصورة الأصلية منخفضة الدقة. راجع الأسماء والأرقام مقابل المصدر، وارفع نسخة أوضح إن توفرت.');$('regions').replaceChildren();$('legacy-banner').hidden=!c.is_mock;$('version').textContent=t(`الإصدار ${num(c.version_no)} · ${label(c.kind)}`);
 $('history').textContent=t(c.history.map(v=>`الإصدار ${num(v.version_no)} ${label(v.kind)} · ${v.author==='local.super_admin'?'المدير العام':v.author.startsWith('engine:')?'محرك '+label(v.author.slice(7)):v.author}`).join(' ← '));
 if(c.is_mock){$('regions').append(node('p','لا يوجد ناتج تعرف حقيقي في هذا الإصدار القديم. اضغط «تشغيل OCR العربي» لاستخراج النص.','empty'));$('boxes').replaceChildren();setStage();return;}
 const ordered=[...c.content.regions].sort((a,b)=>(a.reading_order??Infinity)-(b.reading_order??Infinity));
 if(!ordered.length)$('regions').append(node('p','لم يُرجع المحرك مناطق. تحتاج هذه الصفحة إلى فحص.','empty'));
 for(const r of ordered){const wrap=node('div',undefined,'region');wrap.id=`region-${r.region_id}`;const head=node('div',undefined,'region-head');head.append(node('span',`${r.region_id} · ${label(r.label)}`));
 const select=node('select');select.setAttribute('aria-label',`حالة المنطقة ${r.region_id}`);select.dataset.regionStatus=r.region_id;
 for(const s of statuses){const o=node('option',label(s));o.value=s;select.append(o);}select.value=r.status;
 const field=node('textarea');field.dir='auto';field.value=r.text??'';field.dataset.regionText=r.region_id;field.setAttribute('aria-label',`نص المنطقة ${r.region_id}`);
 field.disabled=select.disabled=c.is_mock||c.kind==='approved'||!can('edit');field.oninput=dirty;select.onchange=dirty;field.onfocus=()=>highlight(r.region_id);
 head.append(select);wrap.append(head,field);if(typeof r.engine_score==='number'){const signal=node('div',`${t('درجة المحرك')}: ${num(Math.round(r.engine_score*100)/100)} · ${t('ليست نسبة دقة')}`,'muted');wrap.append(signal);}if(r.flags?.length)wrap.append(node('span',r.flags.map(label).join(' · '),'muted'));if(r.alternatives?.length){const details=node('details',undefined,'ocr-alternatives');details.append(node('summary',language==='ar'?'قراءة أخرى للمقارنة':'Alternative reading'));if(r.alternative_sources?.length)details.append(node('small',r.alternative_sources.join(' · '),'muted',true));for(const text of r.alternatives){const reading=node('p',text,undefined,true);reading.dir='auto';details.append(reading);}wrap.append(details);}$('regions').append(wrap);}
 drawBoxes();setStage();
}
function highlight(id){document.querySelectorAll('.region,.region-box').forEach(e=>e.classList.toggle('active',e.id===`region-${id}`||e.dataset.id===id));}
function drawBoxes(){
 $('boxes').replaceChildren();if(!state.content)return;const c=state.content.content;
 for(const r of c.regions){const b=node('button',undefined,'region-box');b.dataset.id=r.region_id;b.title=`${r.region_id}: ${label(r.label)}`;b.setAttribute('aria-label',`تحديد منطقة المصدر ${r.region_id}`);
 const [x,y,x1,y1]=r.bbox;Object.assign(b.style,{left:`${x/c.width*100}%`,top:`${y/c.height*100}%`,width:`${(x1-x)/c.width*100}%`,height:`${(y1-y)/c.height*100}%`});
 b.onclick=()=>{highlight(r.region_id);$(`region-${r.region_id}`).scrollIntoView({behavior:'smooth',block:'nearest'});};$('boxes').append(b);}
}
function renderJobs(){
 const target=$('jobs');target.replaceChildren();
 const all=[...(state.doc?.jobs??[])].sort((a,b)=>(b.sequence??0)-(a.sequence??0));
 const real=all.filter(j=>j.engine!=='mock');
 const current=real.find(j=>j.status==='running')??real[0];
 const panel=node('div',undefined,'processing-panel');
 if(!current){panel.append(node('h3','جاهز للتعرف'),node('p','لم تبدأ المعالجة بعد.','muted'));target.append(panel);return;}
 const heading=node('div',undefined,'processing-heading');heading.append(node('h3','المهمة الحالية'),node('span',label(current.status),`status ${current.status}`));panel.append(heading);
 panel.append(node('strong',`${label(current.engine)} · CPU`));
 const descriptions={running:'جارٍ تحميل النموذج واستخراج النص. يمكنك متابعة العمل؛ ستظهر النتيجة تلقائياً.',succeeded:'حُفظ النص؛ يمكنك الآن مراجعته واعتماده.',queued:'لم تبدأ المعالجة بعد.'};
 if(descriptions[current.status])panel.append(node('p',descriptions[current.status],'muted'));
 if(current.last_error&&['failed','blocked','partial_failure'].includes(current.status)){
  const issue=node('div',undefined,'processing-error');issue.append(node('strong','السبب'),node('p',errorMessage(current.last_error)),node('strong','الإجراء المقترح'),node('p','أعد تشغيل التعرف لتطبيق الإصلاح الحالي.'));panel.append(issue);
 }
 const controls=node('div',undefined,'button-row');
 const controllable=can('ingest')||can('assign');
 if(current.status!=='running'&&current.status!=='succeeded'){
  const retry=node('button','أعد المحاولة','primary');retry.disabled=!controllable;retry.onclick=()=>$('recognize').click();controls.append(retry);
 }
 if(['running','queued','blocked'].includes(current.status)){
  const cancel=node('button','إلغاء');cancel.disabled=!controllable;cancel.onclick=()=>action(async()=>{await api(`/jobs/${current.id}/cancel`,{method:'POST'});state.doc=await api(`/documents/${state.doc.id}`);renderJobs();tell('تم طلب الإجراء: إلغاء.');},cancel);controls.append(cancel);
 }
 panel.append(controls);target.append(panel);
 const previous=all.filter(j=>j.id!==current.id);
 if(previous.length){const history=node('details',undefined,'processing-history');history.append(node('summary',`${t('محاولات سابقة')} (${num(previous.length)})`));for(const job of previous){const row=node('div',undefined,'history-row');row.append(node('span',label(job.engine)),node('code',job.id.slice(0,10)),node('span',label(job.status),`status ${job.status}`));history.append(row);}target.append(history);}
}
async function refreshDocument(){if(!leave())return;state.dirty=false;await loadDocs();if(state.doc)await selectDoc(state.doc.id);}
function download(value,name){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=node('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function renderSystem(){
 refreshModels().catch(e=>tell(uiError(e),true));
 const target=$('system-content');target.replaceChildren();if(!state.system){target.append(node('p','افتح جلسة مخولة لعرض حالة الخادم.','empty'));return;}
 const grid=node('div',undefined,'system-grid');for(const entries of [Object.entries(state.system).filter(([k])=>!['models','supported_uploads'].includes(k)),state.system.models.map(m=>[m.id,m.state])]){const column=node('div');for(const [key,value] of entries){const row=node('div',undefined,'system-row');row.append(node('strong',label(key)),node('span',typeof value==='boolean'?(value?'مفعّلة':'معطّلة'):typeof value==='number'?num(value):label(value)));column.append(row);}grid.append(column);}target.append(grid,node('p',`صيغ الصور المدعومة: ${state.system.supported_uploads.join('، ')}. تُدار إعدادات النماذج على الخادم. هذه الصفحة لا تبدأ التدريب.`,'muted'));
}
const workflow=[['الاستلام','ارفع صورة بصيغة مدعومة. يحفظ الفحص الأصل ويعزل الملفات التالفة أو غير المدعومة.'],['التعرف','يعالج العامل المهام المنتظرة. افحص الأخطاء وألغِ المهام أو أعد محاولة المهام المتوقفة بعد تجهيز الاعتماديات.'],['المراجعة','طابق المناطق المرتبطة بالمصدر مع الصورة. احفظ التصحيحات في مسودة جديدة، أو أسند المراجعة، أو صعّد المشكلة. حفظ المسودة لا يعني اعتمادها.'],['الاعتماد','راجع المناطق غير المؤكدة ثم اعتمد الإصدار الحالي. يُحفظ الإصدار المعتمد دون تعديل، ويمكن إعادة فتحه كمسودة جديدة.'],['التصدير','صدّر الصفحات المعتمدة وفق مخطط البيانات المحدد. تظهر أخطاء التحقق ولا تُسلّم السجلات المرفوضة.']];
workflow.forEach(([title,text],i)=>{const row=node('div',undefined,'workflow-row');row.append(node('b',num(i+1)),node('h3',title),node('p',text));$('workflow-content').append(row);});
async function loadDataset(){const data=await api('/dataset');$('dataset-list').replaceChildren();if(!data.items.length)$('dataset-list').append(node('p','لا توجد عينة عامة مجهزة. راجع دليل البيانات العامة في مستندات المشروع.','empty'));for(const r of data.items){const b=node('button',undefined,'doc-row');b.append(node('strong',r.document_id.replace('egyptian-official:','')),node('small',`الصفحة ${num(r.page)} · ${num(r.notes)} ملاحظة من الناشر`),node('span',r.reviewed?'تمت المراجعة':'بانتظار المراجعة',`status ${r.reviewed?'reviewed':''}`));b.onclick=()=>action(async()=>{if(!leave())return;state.dirty=false;state.dataset=await api(`/dataset/${r.id}`);await image(`/dataset/${r.id}/image`,'dataset-image');$('dataset-title').textContent=t(`${r.document_id.replace('egyptian-official:','')} · الصفحة ${num(r.page)}`);$('dataset-text').value=state.dataset.text;$('dataset-notes').textContent=(state.dataset.review_notes??[]).join('\n');$('dataset-note').value='';$('dataset-confirm').checked=false;syncButtons();});$('dataset-list').append(b);}}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>action(async()=>{if(!leave())return;state.dirty=false;$('notice').hidden=true;document.querySelectorAll('[data-view]').forEach(e=>e.classList.toggle('active',e===b));for(const v of ['documents','workflow','dataset','system'])$(`${v}-view`).hidden=v!==b.dataset.view;const titles={documents:['مساحة المستندات','راجع الأصل، واحفظ كل التفاصيل.'],workflow:['سير العمل','تابع المراحل من المستند الأصلي إلى السجل المعتمد.'],dataset:['مساحة مراجعة البيانات','جهّز نصوصاً موثوقة قبل تدريب النموذج.'],system:['النظام والنماذج','اطلع على حالة الخادم والإمكانات المتاحة.']};[$('title').textContent,$('subtitle').textContent]=titles[b.dataset.view].map(t);$('crumb').textContent=t(b.textContent);if(b.dataset.view==='dataset')await loadDataset();if(b.dataset.view==='system'){state.system=await api('/system');renderSystem();}}));
$('connect').onclick=()=>$('connection-dialog').showModal();document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>$(b.dataset.close).close());
$('connection-form').onsubmit=async e=>{e.preventDefault();$('connection-error').textContent=t('');try{await connect($('token').value);}catch(error){$('connection-error').textContent=t(uiError(error));}};
$('disconnect').onclick=()=>{if(!leave())return;state.token='';state.me=null;state.system=null;clearWorkspace();$('documents').replaceChildren();$('system-content').replaceChildren();$('dataset-notes').textContent='';$('dataset-title').textContent=t('اختر عينة');$('dataset-note').value='';for(const u of imageURLs.values())URL.revokeObjectURL(u);imageURLs.clear();$('connect').textContent=t('الدخول إلى مساحة العمل');$('connection-dialog').close();tell('تم تسجيل الخروج.');};
$('upload-open').onclick=()=>{const org=state.me?.orgs.find(o=>o!=='*');if(org)$('org').value=org;if(state.me?.roles.includes('super_admin')&&!$('org').value)$('org').value='demo-court-a';$('upload-dialog').showModal();};
$('upload-form').onsubmit=e=>{e.preventDefault();action(async()=>{if(!leave())return;const form=new FormData();form.append('file',$('file').files[0]);form.append('org_scope',$('org').value);const result=await api('/documents',{method:'POST',body:form});if(result.status==='quarantined'){tell(`تم عزل الملف: ${errorMessage(result.reason)}`,true);return;}$('upload-dialog').close();$('file').value='';$('file-name').textContent=t('لم يتم اختيار ملف');state.dirty=false;await loadDocs();await selectDoc(result.document_id);if(!result.duplicate_file&&$('pipeline-engine').value==='paddleocr_arabic'){await api(`/documents/${result.document_id}/recognize`,{method:'POST',body:JSON.stringify({engine:$('pipeline-engine').value})});await selectDoc(result.document_id);tell('تم رفع المستند وبدأ التعرف الحقيقي على النص باستخدام PaddleOCR العربي.');}else{tell(result.duplicate_file?'الملف موجود مسبقاً. تم فتح مستنده.':'تم حفظ المستند وإضافته إلى قائمة التعرف.');}},e.submitter);};
$('refresh').onclick=()=>action(refreshDocument);$('status').onchange=()=>action(loadDocs);let timer;$('search').oninput=()=>{clearTimeout(timer);timer=setTimeout(()=>action(loadDocs),250);};
$('pages').onchange=()=>action(async()=>{if(!leave()){$('pages').value=state.page;return;}state.dirty=false;await loadPage($('pages').value);});
$('zoom-in').onclick=()=>zoom(25);$('zoom-out').onclick=()=>zoom(-25);function zoom(delta){state.zoom=Math.min(250,Math.max(50,state.zoom+delta));$('image-stage').style.width=`${state.zoom}%`;$('zoom-label').textContent=t(`${num(state.zoom)}٪`);}
$('save').onclick=()=>action(async()=>{const edits=state.content.content.regions.map(r=>({region_id:r.region_id,text:document.querySelector(`[data-region-text="${r.region_id}"]`).value,status:document.querySelector(`[data-region-status="${r.region_id}"]`).value})).filter(e=>{const r=state.content.content.regions.find(r=>r.region_id===e.region_id);return e.text!==(r.text??'')||e.status!==r.status;});if(!edits.length){tell('لا توجد تعديلات على النص لحفظها.');return;}await api(`/pages/${state.page}/draft`,{method:'PUT',body:JSON.stringify({base_version_no:state.content.version_no,edits,reason:$('reason').value})});state.dirty=false;await loadPage(state.page);tell('حُفظت مسودة جديدة. الاعتماد خطوة مستقلة.');},$('save'));
$('approve').onclick=()=>action(async()=>{if(state.dirty)throw new Error('احفظ المسودة قبل الاعتماد.');await api(`/pages/${state.page}/approve`,{method:'POST',body:JSON.stringify({version_no:state.content.version_no})});await selectDoc(state.doc.id);await loadDocs();tell('تم اعتماد الإصدار الحالي من الصفحة.');},$('approve'));
$('reopen').onclick=()=>action(async()=>{if(!$('reason').value.trim())throw new Error('أدخل سبب إعادة فتح الصفحة المعتمدة.');await api(`/pages/${state.page}/reopen`,{method:'POST',body:JSON.stringify({reason:$('reason').value})});await selectDoc(state.doc.id);await loadDocs();tell('فُتحت مسودة جديدة مع الاحتفاظ بالإصدار المعتمد.');},$('reopen'));
$('export').onclick=()=>action(async()=>{if(state.dirty)throw new Error('احفظ التعديلات قبل التصدير.');const r=await api(`/documents/${state.doc.id}/export`,{method:'POST'});if(r.status!=='delivered')throw new Error(`تعذّر التصدير: ${r.errors.map(e=>errorMessage(e)).join(' ')}`);download(r.payload,`sanad-${state.doc.id}.json`);await selectDoc(state.doc.id);tell('تم تصدير النسخة المعتمدة بصيغة JSON.');},$('export'));
$('assign').onclick=()=>action(async()=>{await api(`/pages/${state.page}/assign`,{method:'POST',body:JSON.stringify({assignee:$('assignee').value})});tell('تم إسناد مهمة المراجعة.');},$('assign'));
$('escalate').onclick=()=>action(async()=>{await api(`/pages/${state.page}/escalate`,{method:'POST',body:JSON.stringify({note:$('escalation').value})});tell('تم تصعيد مهمة المراجعة.');},$('escalate'));
$('audit').onclick=()=>action(async()=>{const r=await api('/audit/verify');$('audit-result').textContent=t(r.intact?'سلسلة التدقيق سليمة.':`يوجد خلل في سلسلة التدقيق عند الحدث ${num(r.first_bad_seq)}.`);},$('audit'));
$('dataset-refresh').onclick=()=>action(loadDataset);$('dataset-text').oninput=dirty;
$('dataset-save').onclick=()=>action(async()=>{const r=state.dataset;if(!$('dataset-confirm').checked)throw new Error('أكد أنك راجعت الصفحة كاملة وطابقتها مع الصورة.');const result=await api(`/dataset/${r.id}/review`,{method:'PUT',body:JSON.stringify({text:$('dataset-text').value,note:$('dataset-note').value,base_revision:r.review_revision,checked_against_image:true})});state.dirty=false;r.text=$('dataset-text').value;r.review_revision=result.review_revision;await loadDataset();tell('حُفظ النص المُراجع منفصلاً مع سجل المراجع والتعديلات.');},$('dataset-save'));
window.addEventListener('beforeunload',e=>{if(state.dirty){e.preventDefault();e.returnValue='';}});
syncButtons();fetch('/healthz').then(r=>r.json()).then(async h=>{if(h.local_super_admin){await api('/dev/session',{method:'POST'});await connect('');if(state.docs.length)await selectDoc(state.docs[0].id);}else{$('connect').textContent=t('تسجيل الدخول');}}).catch(e=>tell(`تعذّر فتح مساحة العمل: ${uiError(e)}`,true));

$('file').onchange=()=>{$('file-name').textContent=$('file').files[0]?.name??t('لم يتم اختيار ملف');};
document.querySelectorAll('input[required]').forEach(e=>{e.addEventListener('invalid',()=>e.setCustomValidity(t('يرجى استكمال هذا الحقل.')));e.addEventListener('input',()=>e.setCustomValidity(''));});

$('recognize').onclick=()=>action(async()=>{if(!leave())return;await api(`/documents/${state.doc.id}/recognize`,{method:'POST',body:JSON.stringify({engine:$('pipeline-engine').value})});await selectDoc(state.doc.id);await loadDocs();tell(language==='ar'?'بدأ الاستخراج بالمحرك المحدد. قد تستغرق معالجة VLM على المعالج المركزي عدة دقائق.':'Extraction started with the selected model. CPU VLM processing may take several minutes.');},$('recognize'));
setInterval(()=>{if(state.doc&&!state.dirty&&state.doc.jobs.some(j=>j.status==='running'))action(async()=>{const id=state.doc.id;const updated=await api(`/documents/${id}`);if(state.doc?.id!==id)return;const wasRunning=state.doc.jobs.some(j=>j.status==='running');state.doc=updated;renderJobs();syncButtons();if(wasRunning&&!updated.jobs.some(j=>j.status==='running')){await selectDoc(id);await loadDocs();tell(updated.jobs.some(j=>j.engine!=='mock'&&j.status==='succeeded')?'اكتمل التعرف الحقيقي. راجع النص المستخرج مقابل الصورة الأصلية.':'توقفت المعالجة. راجع تفاصيل المهمة أدناه.',updated.status==='blocked'||updated.status==='failed');}});},3000);

applyLanguage();$('language').textContent=language==='ar'?'English':'العربية';$('language').onclick=()=>{if(!leave())return;saveLanguage(language==='ar'?'en':'ar');location.reload();};

function currentLayout(){
 const page=structuredClone(state.content.content);
 for(const r of page.regions){const field=document.querySelector(`[data-region-text="${r.region_id}"]`);if(field)r.text=field.value;}
 return pageSVG(page);
}
$('page-layout').onclick=()=>{
 if(!state.content||state.content.is_mock)return;
 $('layout-title').textContent=language==='ar'?'الصفحة النصية · نفس مواضع الأصل':'Full-page text · source positions';
 $('layout-note').textContent=language==='ar'?'معاينة نص OCR الحالي، بما فيه التعديلات غير المحفوظة. مواضع الكتل من الأصل؛ الخط وتوزيع السطور داخل الكتل تقريبيان. الأخطاء تحتاج مراجعة.':'Preview of current OCR text, including unsaved edits. Block positions follow the source; fonts and line placement within blocks are approximate. Errors need review.';
 $('layout-original-title').textContent=language==='ar'?'الأصل':'Original';
 $('layout-text-title').textContent=language==='ar'?'النص المستخرج':'Extracted text';
 $('layout-download').textContent=language==='ar'?'تنزيل الصفحة SVG':'Download page SVG';
 $('layout-close').textContent=language==='ar'?'إغلاق':'Close';
 $('layout-original').src=$('page-image').src;
 $('layout-original').alt=language==='ar'?'الصفحة الأصلية':'Original page';
 $('layout-output').innerHTML=currentLayout();
 $('layout-dialog').showModal();
};
$('layout-close').onclick=()=>$('layout-dialog').close();
$('layout-download').onclick=()=>{
 const url=URL.createObjectURL(new Blob([currentLayout()],{type:'image/svg+xml;charset=utf-8'}));
 const a=document.createElement('a');a.href=url;a.download=`sanad-${state.page}-v${state.content.version_no}-preview.svg`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
$('page-layout').textContent=language==='ar'?'عرض الصفحة النصية':'Full-page text';

const bilingual=(ar,en)=>language==='ar'?ar:en;
$('pipeline-engine').value=localStorage.getItem('sanad.pipeline')||'paddleocr_vl';
$('recognize').textContent=bilingual('استخراج الصفحة','Extract page');
$('pipeline-engine').setAttribute('aria-label',bilingual('محرك الاستخراج','Extraction engine'));
$('pipeline-engine').onchange=()=>{localStorage.setItem('sanad.pipeline',$('pipeline-engine').value);syncButtons();};
$('understanding-title').textContent=bilingual('فهم المستند · Gemma','Document understanding · Gemma');
$('understanding-note').textContent=bilingual('اقتراحات مرتبطة بالنص المحفوظ، تحتاج مراجعة. لا تُعدّل نص الصفحة أو تعتمد المستند.','Proposals reference saved source text and need review. They do not edit or approve the page.');
$('understanding-start').textContent=bilingual('استخراج الحقول','Extract fields');
let understandingRunning=false;
async function refreshUnderstanding(){
 if(!state.page||!state.content)return;
 const id=state.page;const result=await api(`/pages/${id}/understanding`);if(state.page!==id)return;
 understandingRunning=result.status==='running';const target=$('understanding-output');target.replaceChildren();
 if(result.status!=='succeeded'){target.append(node('p',label(result.status),'muted'));if(result.error)target.append(node('p',result.error,'error',true));return;}
 const fields=result.result.fields||[];const exportFields=node('button',bilingual('تنزيل الحقول المقترحة JSON','Download proposed fields JSON'),undefined,true);exportFields.onclick=()=>download(result,`sanad-${state.page}-fields-unapproved.json`);target.append(exportFields);
 target.append(node('p',bilingual(`${fields.length} حقل مقترح · غير معتمد · ${result.model}`,`${fields.length} proposed fields · unapproved · ${result.model}`),'muted',true));
 if(!fields.length)target.append(node('p',bilingual('لم ينتج النموذج حقولاً مدعومة بالنص.','The model returned no source-grounded fields.'),undefined,true));
 for(const field of fields){const row=node('div',undefined,'grounded-field');row.append(node('strong',label(field.kind)),node('p',field.value,undefined,true));for(const id of field.region_ids){const button=node('button',id,undefined,true);button.onclick=()=>{highlight(id);$(`region-${id}`)?.scrollIntoView({block:'nearest'});};row.append(button);}target.append(row);}
}
$('understanding-start').onclick=()=>action(async()=>{if(state.dirty)throw new Error(bilingual('احفظ تعديلات النص أولاً.','Save text changes first.'));await api(`/pages/${state.page}/understanding`,{method:'POST'});await refreshUnderstanding();},$('understanding-start'));
async function refreshModels(){
 const info=await api('/models/runtime');const target=$('model-controls');target.replaceChildren();
 target.append(node('h3',bilingual('التحكم في نماذج سند','SANAD model controls'),undefined,true));
 target.append(node('p',bilingual('PaddleOCR-VL يقرأ الصورة ويحدد مناطقها؛ Gemma يقترح الحقول من النص.','PaddleOCR-VL reads and locates page content; Gemma proposes fields from that text.'),undefined,true));
 target.append(node('p',`${info.model} · CPU · ${label(info.state)} · ${info.assets_percent}% | Gemma: ${info.gemma_model} · ${label(info.gemma_ready?'ready':'unavailable')}`,'model-status',true));
 const controls=node('div',undefined,'button-row');
 for(const command of ['start','stop']){const button=node('button',command==='start'?bilingual('تشغيل VLM','Start VLM'):bilingual('إيقاف VLM','Stop VLM'),undefined,true);button.disabled=!can('admin_ops')||(command==='stop'&&!['ready','starting'].includes(info.state))||(command==='start'&&(!info.provisioned||['ready','starting'].includes(info.state)));button.onclick=()=>action(async()=>{await api(`/models/${command}`,{method:'POST'});await refreshModels();},button);controls.append(button);}
 const refresh=node('button',bilingual('تحديث حالة النماذج','Refresh models'),undefined,true);refresh.onclick=()=>action(refreshModels,refresh);controls.append(refresh);target.append(controls);
 if(!info.provisioned)target.append(node('p',bilingual('أوزان VLM غير جاهزة. شغّل scripts/provision_vlm.py على الخادم.','VLM assets are missing. Run scripts/provision_vlm.py on the server.'),'muted',true));
 if(!info.gemma_ready)target.append(node('p','ollama pull gemma3:4b','muted',true));
}
setInterval(()=>{if(understandingRunning)refreshUnderstanding().catch(()=>{});if(!$('system-view').hidden)refreshModels().catch(()=>{});},5000);
