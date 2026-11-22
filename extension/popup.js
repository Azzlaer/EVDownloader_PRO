let tabId=null,selected=null,sources=[],probeData=null,variants=[];
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function status(s,bad=false){$('status').textContent=s;$('status').style.color=bad?'#fca5a5':''}
async function native(payload,timeout=20000){const r=await chrome.runtime.sendMessage({action:'native',payload,timeout});if(!r?.ok)throw new Error(r?.error||'Native Host no disponible');return r.response}
function safeName(v){return(v||'video').replace(/[<>:"/\\|?*\x00-\x1f]/g,'_').replace(/\s+/g,' ').trim().slice(0,110)||'video'}
async function hostStatus(){try{const r=await native({command:'ping'});$('hostDot').className='dot '+(r.ffmpeg_ok?'ok':'bad');$('hostText').textContent=r.ffmpeg_ok?`FFmpeg conectado · Host ${r.version||'PRO'}`:'Motor conectado · configura FFmpeg';}catch(e){$('hostDot').className='dot bad';$('hostText').textContent='Native Host no conectado';status(e.message,true)}}
function fmtBytes(n){n=Number(n||0);if(!n)return'';const u=['B','KB','MB','GB'];let i=0;while(n>=1024&&i<3){n/=1024;i++}return`${n.toFixed(i>1?2:1)} ${u[i]}`}
function dedupeKey(s){try{const u=new URL(s.url);return `${s.kind}|${u.origin}${u.pathname}`;}catch{return `${s.kind}|${s.url}`}}
function downloadableSources(){
 const seenExact=new Set(), seenPath=new Set();
 const preferred=[...sources].sort((a,b)=>{const rank={HLS:0,DASH:0,MP4:1,WEBM:1,VIDEO:2,MEDIA:3};return (rank[a.kind]??9)-(rank[b.kind]??9)});
 return preferred.filter(s=>{
  if(!s?.url||['SEGMENT','AUDIO'].includes(s.kind))return false;
  if(!['HLS','DASH','MP4','WEBM','VIDEO','MEDIA'].includes(s.kind))return false;
  if(seenExact.has(s.url))return false;seenExact.add(s.url);
  const k=dedupeKey(s);
  if(seenPath.has(k))return false;seenPath.add(k);return true;
 });
}
function extForMode(mode){return mode==='audio_mp3'?'.mp3':mode==='audio_flac'?'.flac':'.mkv'}
function renderSources(){
 const box=$('sources');box.innerHTML='';
 if(!sources.length){box.innerHTML='<div class="empty">No se detectaron medios. Inicia la reproducción y vuelve a detectar.</div>';return;}
 sources.forEach((s,i)=>{const d=document.createElement('div');d.className='source'+(selected?.url===s.url?' selected':'');const dims=s.width&&s.height?`${s.width}x${s.height}`:'';const meta=[fmtBytes(s.contentLength),dims,s.statusCode?`HTTP ${s.statusCode}`:'',s.source||''].filter(Boolean).join(' · ');d.innerHTML=`<div class="source-top"><b>${esc(s.kind)} · Fuente ${i+1}</b><span class="badge">${esc(meta||'media')}</span></div><div class="source-url">${esc(s.url)}</div>`;d.onclick=()=>{selected=s;probeData=null;variants=[];$('variant').innerHTML='<option value="">Automática / original</option>';renderSources();status('Fuente seleccionada.');};box.appendChild(d);});
}
async function detect(){try{status('Analizando pestaña…');const r=await chrome.runtime.sendMessage({action:'getCandidates',tabId});sources=r?.items||[];selected=sources[0]||null;renderSources();status(`${sources.length} fuente(s) detectada(s). ${downloadableSources().length} descargable(s) tras deduplicar.`)}catch(e){status(e.message,true)}}
function fillTracks(data){const a=$('audioTrack'),s=$('subtitleTrack');a.innerHTML='<option value="all">Todos</option>';s.innerHTML='<option value="all">Todos</option><option value="none">Ninguno</option>';let ai=0,si=0;for(const st of(data?.streams||[])){if(st.codec_type==='audio'){const o=document.createElement('option');o.value=String(ai++);o.textContent=`Audio ${ai} · ${st.codec_name||'?'} · ${st.tags?.language||'und'}`;a.appendChild(o)}if(st.codec_type==='subtitle'){const o=document.createElement('option');o.value=String(si++);o.textContent=`Sub ${si} · ${st.codec_name||'?'} · ${st.tags?.language||'und'}`;s.appendChild(o)}}}
async function authFor(src){src=src||selected;if(!$('useSession').checked||!src)return{cookieHeader:'',referer:src?.pageUrl||'',userAgent:navigator.userAgent};const r=await chrome.runtime.sendMessage({action:'getAuthContext',url:src.url,pageUrl:src.pageUrl||''});return r?.context||{}}
async function auth(){return authFor(selected)}
function nativeContext(src,ctx){return{referer:src?.pageUrl||ctx?.referer||'',cookie:ctx?.cookieHeader||'',user_agent:ctx?.userAgent||navigator.userAgent,http_headers:src?.requestHeaders||{}}}
async function analyze(){if(!selected)return status('Selecciona una fuente.',true);try{status('Analizando con ffprobe…');const ctx=await auth();const r=await native({command:'probe',url:selected.url,...nativeContext(selected,ctx)},90000);probeData=r.data;fillTracks(probeData);$('mediaInfo').textContent=r.summary||'Analizado';status('Análisis completado.')}catch(e){status(e.message,true)}}
async function inspect(){if(!selected)return status('Selecciona una fuente.',true);if(!['HLS','DASH'].includes(selected.kind))return status('La fuente seleccionada no es un manifiesto HLS/DASH.');try{status('Leyendo variantes…');const ctx=await auth();const r=await native({command:'inspect_manifest',kind:selected.kind,url:selected.url,...nativeContext(selected,ctx)},60000);variants=r?.variants||[];const sel=$('variant');sel.innerHTML='<option value="">Automática / original</option>';variants.forEach((v,i)=>{const o=document.createElement('option');o.value=v.url||v.id||String(i);o.textContent=v.label||`Variante ${i+1}`;sel.appendChild(o)});$('mediaInfo').textContent=variants.length?`${variants.length} variante(s) detectadas. En HLS puedes elegir una calidad concreta.`:'No se encontraron variantes explícitas.';status('Calidades inspeccionadas.')}catch(e){status(e.message,true)}}
function stateText(j){return({started:'Iniciando',progress:'Procesando',retry:'Reintentando H.264',complete:'Completado',error:'Error',cancelled:'Cancelado'})[j.event]||j.event||'Pendiente'}
function renderJobs(list){
 $('queueCount').textContent=list.length;const box=$('jobs');box.innerHTML='';if(!list.length){box.innerHTML='<div class="empty">No hay trabajos todavía.</div>';return;}
 const batches=new Map();for(const j of list){if(j.batch_id){const b=batches.get(j.batch_id)||{total:Number(j.batch_total||0),items:[]};b.items.push(j);b.total=Math.max(b.total,Number(j.batch_total||0));batches.set(j.batch_id,b)}}
 for(const [bid,b] of batches){const done=b.items.filter(x=>['complete','error','cancelled'].includes(x.event)).length,ok=b.items.filter(x=>x.event==='complete').length,pct=b.total?done/b.total*100:0,d=document.createElement('div');d.className='batch-summary';d.innerHTML=`<div class="batch-title">📦 Lote ${esc(bid)} · ${done}/${b.total} procesados</div><div class="progress"><div class="bar" style="width:${pct}%"></div></div><div class="batch-meta"><span>${ok} completados</span><span>${pct.toFixed(0)}% global</span></div>`;box.appendChild(d)}
 for(const j of list){const pct=Math.max(0,Math.min(100,Number(j.percent||0))),d=document.createElement('div');d.className='job '+(j.event==='complete'?'complete':j.event==='error'?'error':'');const stat=pct>0?`${pct.toFixed(1)}% · ${esc(j.speed||'--')}`:`${esc(j.out_time||'')} ${fmtBytes(j.total_size||0)}`.trim()||'En curso';d.innerHTML=`<div class="job-head"><span class="job-name">${esc(j.filename||'video')}</span><span class="job-state">${esc(stateText(j))}</span></div>${j.batch_id?`<div class="job-batch">Lote ${esc(j.batch_id)} · ${Number(j.batch_index||0)}/${Number(j.batch_total||0)}</div>`:''}${j.message?`<div class="job-batch">${esc(j.message)}</div>`:''}<div class="progress"><div class="bar" style="width:${pct}%"></div></div><div class="job-meta"><span>${stat}</span><span>ETA ${esc(j.eta||'--')}</span></div>${['started','progress','retry'].includes(j.event)?`<button class="cancel" data-id="${esc(j.job_id)}">Cancelar actual</button>`:''}`;box.appendChild(d)}
 box.querySelectorAll('.cancel').forEach(b=>b.onclick=()=>native({command:'cancel',job_id:b.dataset.id}).catch(e=>status(e.message,true)));
}
async function jobs(){const r=await chrome.runtime.sendMessage({action:'getJobs'});renderJobs(r?.jobs||[])}
async function start(){if(!selected)return status('Selecciona una fuente.',true);try{const ctx=await auth();let url=selected.url;const chosen=$('variant').value;if(selected.kind==='HLS'&&chosen&&/^https?:/.test(chosen))url=chosen;let name=$('filename').value||'video.mkv',mode=$('mode').value;if(mode.startsWith('audio_'))name=name.replace(/\.[^.]+$/,mode==='audio_mp3'?'.mp3':'.flac');else if(!/\.mkv$/i.test(name))name=name.replace(/\.[^.]+$/,'')+'.mkv';const minutes=Math.max(0,Number($('liveMinutes').value||0));const r=await native({command:'download',url,mode,filename:name,audio_track:$('audioTrack').value,subtitle_track:$('subtitleTrack').value,max_seconds:minutes?minutes*60:0,...nativeContext(selected,ctx)},30000);status(`Trabajo ${r.job_id} iniciado.`);await jobs();document.querySelector('[data-tab="queue"]').click()}catch(e){status(e.message,true)}}
async function startAll(){
 const list=downloadableSources();if(!list.length)return status('No hay videos descargables detectados. Reproduce los videos y pulsa Detectar.',true);
 try{status('Selecciona la carpeta donde se guardará el lote…');const pick=await native({command:'select_folder'},120000);if(!pick?.folder)return status('Selección de carpeta cancelada.');$('bulkFolder').textContent='Carpeta: '+pick.folder;const mode=$('mode').value,ext=extForMode(mode),base=safeName($('pageTitle').textContent||'video'),items=[];
  for(let i=0;i<list.length;i++){const src=list[i],ctx=await authFor(src),kind=String(src.kind||'VIDEO').toLowerCase();items.push({url:src.url,mode,filename:`${base}_${String(i+1).padStart(3,'0')}_${kind}${ext}`,audio_track:$('audioTrack').value,subtitle_track:$('subtitleTrack').value,max_seconds:0,...nativeContext(src,ctx)})}
  status(`Enviando ${items.length} video(s) a la cola automática…`);const r=await native({command:'batch_download',items,output_dir:pick.folder},60000);status(`📦 Lote ${r.batch_id}: ${r.count} video(s) en cola. Conversión automática iniciada.`);await jobs();document.querySelector('[data-tab="queue"]').click();
 }catch(e){status(e.message,true)}
}
document.addEventListener('DOMContentLoaded',async()=>{
 const tabs=await chrome.tabs.query({active:true,currentWindow:true}),tab=tabs[0];tabId=tab?.id;$('pageTitle').textContent=tab?.title||tab?.url||'';$('filename').value=safeName(tab?.title)+'.mkv';
 $('settings').onclick=()=>chrome.runtime.openOptionsPage();$('refreshHost').onclick=hostStatus;$('detectBtn').onclick=detect;$('clearBtn').onclick=async()=>{await chrome.runtime.sendMessage({action:'clearCandidates',tabId});sources=[];selected=null;renderSources()};$('analyzeBtn').onclick=analyze;$('inspectBtn').onclick=inspect;
 $('previewBtn').onclick=async()=>{if(!selected)return;try{const ctx=await auth();await native({command:'preview',url:selected.url,...nativeContext(selected,ctx)});status('FFplay iniciado.')}catch(e){status(e.message,true)}};
 $('downloadBtn').onclick=start;$('downloadAllBtn').onclick=startAll;$('reloadJobs').onclick=jobs;$('clearFinished').onclick=async()=>{await chrome.runtime.sendMessage({action:'clearFinishedJobs'});await jobs()};
 document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));b.classList.add('active');$(b.dataset.tab).classList.add('active');if(b.dataset.tab==='queue')jobs()});
 chrome.runtime.onMessage.addListener(m=>{if(m.event==='jobUpdate'||m.event==='batchUpdate')jobs()});await hostStatus();await detect();await jobs();
});


// Optional YouTube provider: uses the native host, not network interception.
async function ytInspect() {
 try {
  status('Consultando formatos con yt-dlp…');
  const response = await native({command:'youtube_inspect',url:$('ytUrl').value.trim()},90000);
  const v = response.video || {};
  $('ytInfo').textContent = [v.title, v.channel, v.duration ? 'Duración: '+Math.round(v.duration)+' s' : '',
    (v.formats||[]).length+' formatos disponibles'].filter(Boolean).join(' · ');
  status('Video analizado. Elige formato y calidad.');
 } catch(e) {status(e.message,true);}
}
async function ytDownload() {
 try {
  status('Iniciando descarga autorizada…');
  const response = await native({command:'youtube_download',url:$('ytUrl').value.trim(),
   quality:$('ytQuality').value,format:$('ytFormat').value},30000);
  status('Trabajo '+response.job_id+' iniciado.');
  document.querySelector('[data-tab="queue"]').click();
  await jobs();
 } catch(e) {status(e.message,true);}
}
document.addEventListener('DOMContentLoaded',()=>{
 $('ytCurrent').onclick=async()=>{
  const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
  $('ytUrl').value=tab?.url||'';
 };
 $('ytAnalyze').onclick=ytInspect;
 $('ytDownload').onclick=ytDownload;
});
