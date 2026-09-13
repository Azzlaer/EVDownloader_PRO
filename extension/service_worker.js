const HOST = "com.azzlaer.videomkvhost";
const MAX_MEDIA = 120;
const STATE_KEY = 'vmkv_state_v32';
const candidates = new Map();
const jobs = new Map();
let nativePort = null;
let requestSeq = 1;
const pending = new Map();

const stateReady = (async () => {
  try {
    const saved = (await chrome.storage.session.get(STATE_KEY))[STATE_KEY] || {};
    for (const [tabId, items] of Object.entries(saved.candidates || {})) {
      candidates.set(Number(tabId), Array.isArray(items) ? items : []);
    }
    for (const [id, job] of Object.entries(saved.jobs || {})) jobs.set(id, job);
  } catch (_) {}
})();

let persistTimer = null;
function schedulePersist() {
  clearTimeout(persistTimer);
  persistTimer = setTimeout(async () => {
    try {
      const c = {};
      for (const [tabId, items] of candidates) c[String(tabId)] = items;
      const j = Object.fromEntries(jobs);
      await chrome.storage.session.set({[STATE_KEY]: {candidates:c, jobs:j, savedAt:Date.now()}});
    } catch (_) {}
  }, 120);
}

function mediaKind(url, contentType='') {
  const u=(url||'').toLowerCase(), ct=(contentType||'').toLowerCase();
  if (u.includes('.m3u8') || ct.includes('mpegurl')) return 'HLS';
  if (u.includes('.mpd') || ct.includes('dash+xml')) return 'DASH';
  if (/\.(mp4|m4v|mov)(\?|#|$)/i.test(u)) return 'MP4';
  if (/\.webm(\?|#|$)/i.test(u)) return 'WEBM';
  if (u.includes('.m4s') || /\.(ts|m2ts)(\?|#|$)/i.test(u)) return 'SEGMENT';
  if (ct.startsWith('video/')) return 'VIDEO';
  if (ct.startsWith('audio/')) return 'AUDIO';
  return 'MEDIA';
}
function interesting(url,type='',ct='') {
  if (!url || !/^https?:/i.test(url)) return false;
  const u=url.toLowerCase(), c=(ct||'').toLowerCase();
  return type==='media' || c.startsWith('video/') || c.startsWith('audio/') || c.includes('mpegurl') || c.includes('dash+xml') ||
    /\.(mp4|webm|mov|m4v|mkv|avi|m3u8|mpd|m4s|ts|m2ts|mp3|aac|ogg|wav|flac)(\?|#|$)/i.test(u);
}
function compactHeaders(headers=[]) {
  const wanted = new Set(['referer','origin','authorization','accept-language']);
  const out = {};
  for (const h of headers || []) {
    const k = String(h.name||'').toLowerCase();
    if (wanted.has(k) && h.value) out[k] = h.value;
  }
  return out;
}
async function tabMeta(tabId) {
  try { const t=await chrome.tabs.get(tabId); return {pageUrl:t.url||'',title:t.title||'',favIconUrl:t.favIconUrl||''}; }
  catch { return {pageUrl:'',title:'',favIconUrl:''}; }
}
async function addCandidate(tabId,item) {
  await stateReady;
  if (tabId == null || tabId < 0 || !interesting(item.url,item.type,item.contentType)) return;
  const meta=await tabMeta(tabId), kind=item.kind||mediaKind(item.url,item.contentType);
  let arr=candidates.get(tabId)||[];
  let x=arr.find(v=>v.url===item.url);
  const patch={
    lastSeen:Date.now(), contentType:item.contentType||x?.contentType||'', kind,
    pageUrl:meta.pageUrl||item.pageUrl||x?.pageUrl||'', title:meta.title||x?.title||'', favIconUrl:meta.favIconUrl||x?.favIconUrl||'',
    contentLength:Number(item.contentLength||x?.contentLength||0), statusCode:item.statusCode||x?.statusCode||0,
    requestHeaders:{...(x?.requestHeaders||{}),...(item.requestHeaders||{})},
    width:Number(item.width||x?.width||0), height:Number(item.height||x?.height||0), duration:Number(item.duration||x?.duration||0)
  };
  if(x) Object.assign(x,patch); else arr.unshift({url:item.url,type:item.type||'',source:item.source||'network',firstSeen:Date.now(),...patch});
  const mani=arr.filter(x=>['HLS','DASH'].includes(x.kind));
  const normal=arr.filter(x=>!['HLS','DASH','SEGMENT'].includes(x.kind));
  const seg=arr.filter(x=>x.kind==='SEGMENT').slice(0,8);
  candidates.set(tabId,[...mani,...normal,...seg].slice(0,MAX_MEDIA));
  schedulePersist();
}

chrome.webRequest.onBeforeRequest.addListener(d=>{
  if(['media','xmlhttprequest','other'].includes(d.type)) addCandidate(d.tabId,{url:d.url,type:d.type,source:'network'});
},{urls:['http://*/*','https://*/*']});

chrome.webRequest.onBeforeSendHeaders.addListener(d=>{
  if(['media','xmlhttprequest','other'].includes(d.type)) addCandidate(d.tabId,{url:d.url,type:d.type,source:'request',requestHeaders:compactHeaders(d.requestHeaders)});
},{urls:['http://*/*','https://*/*'],types:['media','xmlhttprequest','other']},['requestHeaders','extraHeaders']);

chrome.webRequest.onHeadersReceived.addListener(d=>{
  const h=d.responseHeaders||[];
  const ct=h.find(x=>String(x.name).toLowerCase()==='content-type')?.value||'';
  const len=h.find(x=>String(x.name).toLowerCase()==='content-length')?.value||0;
  if(interesting(d.url,d.type,ct)) addCandidate(d.tabId,{url:d.url,type:d.type,contentType:ct,contentLength:len,statusCode:d.statusCode,source:'headers'});
},{urls:['http://*/*','https://*/*'],types:['media','xmlhttprequest','other']},['responseHeaders']);

chrome.tabs.onRemoved.addListener(async id=>{await stateReady;candidates.delete(id);schedulePersist();});

async function authContext(url,pageUrl='') {
  let cookieHeader='';
  try { const list=await chrome.cookies.getAll({url}); cookieHeader=list.map(c=>`${c.name}=${c.value}`).join('; '); } catch (_) {}
  return {cookieHeader,referer:pageUrl||'',userAgent:navigator.userAgent};
}

function connectNative(){
  if(nativePort)return nativePort;
  nativePort=chrome.runtime.connectNative(HOST);
  nativePort.onMessage.addListener(onNativeMessage);
  nativePort.onDisconnect.addListener(()=>{
    const err=chrome.runtime.lastError?.message||'Native Host desconectado';
    for(const [,p] of pending)p.reject(new Error(err));
    pending.clear(); nativePort=null;
  });
  return nativePort;
}
async function onNativeMessage(m){
  await stateReady;
  if(m.response_to&&pending.has(m.response_to)){
    const p=pending.get(m.response_to);pending.delete(m.response_to);
    m.ok===false?p.reject(new Error(m.error||'Error')):p.resolve(m);return;
  }
  if(m.event==='batch_complete'){
    chrome.runtime.sendMessage({event:'batchUpdate',batch:m}).catch(()=>{}); return;
  }
  if(m.event&&m.job_id){
    const old=jobs.get(m.job_id)||{};
    jobs.set(m.job_id,{...old,...m,updatedAt:Date.now()});
    schedulePersist();
    chrome.runtime.sendMessage({event:'jobUpdate',job:jobs.get(m.job_id)}).catch(()=>{});
    if(m.event==='complete')chrome.notifications.create({type:'basic',iconUrl:'icon128.png',title:'Video MKV completado',message:m.output||'Finalizado'}).catch(()=>{});
  }
}
function nativeRequest(payload,timeout=20000){
  return new Promise((resolve,reject)=>{
    const port=connectNative(),id=String(requestSeq++);
    pending.set(id,{resolve,reject});port.postMessage({...payload,request_id:id});
    setTimeout(()=>{if(pending.has(id)){pending.delete(id);reject(new Error('Tiempo de espera agotado'));}},timeout);
  });
}
async function scanDom(tabId){try{const r=await chrome.tabs.sendMessage(tabId,{action:'scanVideoElements'});for(const x of(r?.items||[]))await addCandidate(tabId,{...x,source:'dom'});}catch(_){}}

chrome.runtime.onMessage.addListener((msg,sender,sendResponse)=>{(async()=>{try{
  await stateReady;
  if(msg.action==='domCandidate'){if(sender?.tab?.id!=null)await addCandidate(sender.tab.id,{...msg.item,source:'dom-event'});return sendResponse({ok:true});}
  if(msg.action==='getCandidates'){await scanDom(msg.tabId);return sendResponse({ok:true,items:candidates.get(msg.tabId)||[]});}
  if(msg.action==='clearCandidates'){candidates.set(msg.tabId,[]);schedulePersist();return sendResponse({ok:true});}
  if(msg.action==='getAuthContext'){return sendResponse({ok:true,context:await authContext(msg.url,msg.pageUrl)});}
  if(msg.action==='getJobs')return sendResponse({ok:true,jobs:[...jobs.values()].sort((a,b)=>(b.startedAt||b.updatedAt||0)-(a.startedAt||a.updatedAt||0))});
  if(msg.action==='clearFinishedJobs'){
    for(const [id,j] of jobs) if(['complete','error','cancelled'].includes(j.event)) jobs.delete(id);
    schedulePersist();return sendResponse({ok:true});
  }
  if(msg.action==='native'){const r=await nativeRequest(msg.payload,msg.timeout||20000);return sendResponse({ok:true,response:r});}
  sendResponse({ok:false,error:'Acción desconocida'});
}catch(e){sendResponse({ok:false,error:e?.message||String(e)});}})();return true;});
