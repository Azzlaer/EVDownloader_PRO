#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import configparser, json, os, re, shutil, struct, subprocess, sys, threading, time, traceback, uuid, urllib.request, urllib.parse
from collections import deque
from pathlib import Path

BASE=Path(__file__).resolve().parent
CFG_PATH=BASE/'config.ini'
CFG=configparser.ConfigParser(interpolation=None)
CFG.read(CFG_PATH,encoding='utf-8')
WRITE_LOCK=threading.Lock(); JOB_LOCK=threading.Lock(); JOBS={}

def log(s):
    try:
        p=BASE/CFG.get('LOG','file',fallback='videomkv_host.log')
        with p.open('a',encoding='utf-8') as f:f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {s}\n")
    except Exception: pass

def read_exact(stream,n):
    chunks=[];left=n
    while left>0:
        b=stream.read(left)
        if not b:return None
        chunks.append(b);left-=len(b)
    return b''.join(chunks)

def read_msg():
    raw=read_exact(sys.stdin.buffer,4)
    if not raw:return None
    n=struct.unpack('<I',raw)[0]
    if n<=0 or n>16*1024*1024:raise ValueError('Mensaje Native Messaging inválido.')
    data=read_exact(sys.stdin.buffer,n)
    if data is None:return None
    return json.loads(data.decode('utf-8'))

def send(obj):
    data=json.dumps(obj,ensure_ascii=False).encode('utf-8')
    with WRITE_LOCK:
        sys.stdout.buffer.write(struct.pack('<I',len(data)));sys.stdout.buffer.write(data);sys.stdout.buffer.flush()

def reload_cfg():
    global CFG
    CFG=configparser.ConfigParser(interpolation=None);CFG.read(CFG_PATH,encoding='utf-8')

def expand(v):return os.path.expandvars(os.path.expanduser(str(v).strip().strip('"')))
def get_paths():
    return (Path(expand(CFG.get('FFMPEG','ffmpeg',fallback='ffmpeg.exe'))),Path(expand(CFG.get('FFMPEG','ffprobe',fallback='ffprobe.exe'))),Path(expand(CFG.get('FFMPEG','ffplay',fallback='ffplay.exe'))),Path(expand(CFG.get('FFMPEG','dll_dir',fallback=''))))
def env():
    e=os.environ.copy();*_,d=get_paths()
    if str(d) and d.exists():e['PATH']=str(d)+os.pathsep+e.get('PATH','')
    return e

def creationflags():
    return getattr(subprocess,'CREATE_NO_WINDOW',0) if os.name=='nt' else 0

def okexe(p):
    try:return subprocess.run([str(p),'-version'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=env(),timeout=5,creationflags=creationflags()).returncode==0
    except Exception:return False

def out_dir():return Path(expand(CFG.get('OUTPUT','directory',fallback=str(Path.home()/'Videos'/'MKV'))))
def clean_name(n):
    # Handle Windows paths even when tests or tooling run on another OS.
    n=re.split(r'[/\\]',str(n or 'video.mkv'))[-1]
    n=re.sub(r'[<>:"/\\|?*\x00-\x1F]','_',n).strip(' .')
    if not n:n='video'
    match=re.search(r'\.(mkv|mp3|flac)$',n,re.I)
    suffix=match.group(0) if match else '.mkv'
    stem=n[:-len(suffix)] if match else n
    stem=stem.rstrip(' .') or 'video'
    # Windows reserves these device names, including names with extensions.
    if re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',stem,re.I):
        stem='_'+stem
    return stem[:180-len(suffix)]+suffix

def http_args(req):
    ua=(req.get('user_agent') or CFG.get('NETWORK','user_agent',fallback='')).strip()
    a=[]
    if ua:a += ['-user_agent',ua]
    hdr=[]
    supplied=req.get('http_headers') or {}
    allowed={'referer':'Referer','origin':'Origin','authorization':'Authorization','accept-language':'Accept-Language'}
    seen=set()
    for k,v in supplied.items():
        lk=str(k).lower()
        if lk in allowed and v:
            hdr.append(f'{allowed[lk]}: {v}');seen.add(lk)
    referer=req.get('referer','')
    if referer and 'referer' not in seen:hdr.append(f'Referer: {referer}')
    if referer and 'origin' not in seen:
        m=re.match(r'^(https?://[^/]+)',referer)
        if m:hdr.append(f'Origin: {m.group(1)}')
    cookie=req.get('cookie','')
    if cookie:hdr.append(f'Cookie: {cookie}')
    if hdr:a += ['-headers','\r\n'.join(hdr)+'\r\n']
    return a

def input_args(req,url=None):
    url=url or req.get('url','');a=[]
    if CFG.getboolean('NETWORK','reconnect',fallback=True):a += ['-reconnect','1','-reconnect_streamed','1','-reconnect_delay_max','5']
    return a+http_args(req)+['-i',url]

def reply(req,**kw):send({'response_to':req.get('request_id'),'ok':True,**kw})
def fail(req,e):send({'response_to':req.get('request_id'),'ok':False,'error':str(e)})

def ping(req):
    f,fp,pl,d=get_paths();reply(req,ffmpeg_ok=okexe(f),ffprobe_ok=okexe(fp),ffplay_ok=okexe(pl),ffmpeg=str(f),ffprobe=str(fp),ffplay=str(pl),dll_dir=str(d),output_dir=str(out_dir()),version='3.2.0')

def config_dict():
    f,fp,pl,d=get_paths();return {'ffmpeg':str(f),'ffprobe':str(fp),'ffplay':str(pl),'dll_dir':str(d),'output_dir':str(out_dir()),'overwrite':CFG.getboolean('OUTPUT','overwrite',fallback=False),'video_crf':CFG.get('CONVERSION','video_crf',fallback='22'),'video_preset':CFG.get('CONVERSION','video_preset',fallback='medium'),'audio_bitrate':CFG.get('CONVERSION','audio_bitrate',fallback='192k'),'user_agent':CFG.get('NETWORK','user_agent',fallback=''),'reconnect':CFG.getboolean('NETWORK','reconnect',fallback=True)}
def get_config(req):reply(req,config=config_dict())
def set_config(req):
    c=req.get('config') or {}
    for sec in ['FFMPEG','OUTPUT','CONVERSION','NETWORK','LOG']:
        if not CFG.has_section(sec):CFG.add_section(sec)
    mapping={'ffmpeg':('FFMPEG','ffmpeg'),'ffprobe':('FFMPEG','ffprobe'),'ffplay':('FFMPEG','ffplay'),'dll_dir':('FFMPEG','dll_dir'),'output_dir':('OUTPUT','directory'),'overwrite':('OUTPUT','overwrite'),'video_crf':('CONVERSION','video_crf'),'video_preset':('CONVERSION','video_preset'),'audio_bitrate':('CONVERSION','audio_bitrate'),'user_agent':('NETWORK','user_agent'),'reconnect':('NETWORK','reconnect')}
    for k,(s,o) in mapping.items():
        if k in c:CFG.set(s,o,str(c[k]).lower() if isinstance(c[k],bool) else str(c[k]))
    with CFG_PATH.open('w',encoding='utf-8') as f:CFG.write(f)
    reload_cfg();reply(req,message='Configuración guardada correctamente.',config=config_dict())
def auto_detect(req):
    found={}
    for name in ['ffmpeg','ffprobe','ffplay']:
        p=shutil.which(name+'.exe') or shutil.which(name)
        if p:found[name]=p
    roots=[Path('C:/ffmpeg/bin'),Path('C:/Program Files/ffmpeg/bin'),Path.home()/'ffmpeg'/'bin']
    for r in roots:
        for name in ['ffmpeg','ffprobe','ffplay']:
            if name not in found and (r/(name+'.exe')).exists():found[name]=str(r/(name+'.exe'))
    for k,v in found.items():CFG.set('FFMPEG',k,v)
    if found.get('ffmpeg'):CFG.set('FFMPEG','dll_dir',str(Path(found['ffmpeg']).parent))
    with CFG_PATH.open('w',encoding='utf-8') as f:CFG.write(f)
    reload_cfg();reply(req,message=f"Detectadas {len(found)} herramienta(s).",config=config_dict())

def probe(req):
    url=req.get('url','');_,fp,_,_=get_paths()
    if not url.startswith(('http://','https://')):raise ValueError('URL multimedia no válida.')
    cmd=[str(fp),'-v','error','-show_entries','format=filename,format_name,duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,r_frame_rate,channels,sample_rate:stream_tags=language,title','-of','json']+input_args(req)
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',env=env(),timeout=90,creationflags=creationflags())
    if p.returncode:raise RuntimeError((p.stderr or 'ffprobe falló')[-5000:])
    data=json.loads(p.stdout or '{}');lines=[];fmt=data.get('format',{})
    if fmt.get('format_name'):lines.append('Formato: '+fmt['format_name'])
    if fmt.get('duration'):
        try:sec=float(fmt['duration']);lines.append(f"Duración: {int(sec//60)}:{int(sec%60):02d}")
        except Exception:pass
    if fmt.get('bit_rate'):
        try:lines.append(f"Bitrate: {int(fmt['bit_rate'])/1_000_000:.2f} Mbps")
        except Exception:pass
    for s in data.get('streams',[]):
        if s.get('codec_type')=='video':lines.append(f"Video: {s.get('codec_name','?')} · {s.get('width','?')}x{s.get('height','?')} · {s.get('r_frame_rate','?')}")
        elif s.get('codec_type')=='audio':lines.append(f"Audio: {s.get('codec_name','?')} · {s.get('channels','?')} ch · {s.get('tags',{}).get('language','und')}")
        elif s.get('codec_type')=='subtitle':lines.append(f"Sub: {s.get('codec_name','?')} · {s.get('tags',{}).get('language','und')}")
    reply(req,data=data,summary='\n'.join(lines) or 'Fuente analizada.')

def inspect_manifest(req):
    url=req.get('url','');kind=(req.get('kind') or '').upper()
    if not url.startswith(('http://','https://')):raise ValueError('URL de manifiesto no válida.')
    hdr={'User-Agent':req.get('user_agent') or CFG.get('NETWORK','user_agent',fallback='Mozilla/5.0')}
    for k,v in (req.get('http_headers') or {}).items():
        lk=str(k).lower()
        if lk in ('referer','origin','authorization','accept-language') and v:hdr[k]=v
    if req.get('referer') and not any(str(k).lower()=='referer' for k in hdr):hdr['Referer']=req['referer']
    if req.get('cookie'):hdr['Cookie']=req['cookie']
    rq=urllib.request.Request(url,headers=hdr)
    with urllib.request.urlopen(rq,timeout=30) as r:text=r.read().decode('utf-8','replace')
    variants=[]
    if kind=='HLS' or '.m3u8' in url.lower():
        lines=text.splitlines()
        for i,line in enumerate(lines):
            if not line.startswith('#EXT-X-STREAM-INF:'):continue
            meta=line[len('#EXT-X-STREAM-INF:'):];nxt=''
            for cand in lines[i+1:]:
                cand=cand.strip()
                if cand and not cand.startswith('#'):nxt=cand;break
            if not nxt:continue
            res=(re.search(r'RESOLUTION=(\d+x\d+)',meta,re.I) or [None,''])[1]
            bw_m=re.search(r'BANDWIDTH=(\d+)',meta,re.I);bw=int(bw_m.group(1)) if bw_m else 0
            co_m=re.search(r'CODECS="([^"]+)"',meta,re.I);codecs=co_m.group(1) if co_m else ''
            label=' · '.join(x for x in [res,f'{round(bw/1000)} kbps' if bw else '',codecs] if x) or 'HLS variante'
            variants.append({'url':urllib.parse.urljoin(url,nxt),'label':label,'resolution':res,'bandwidth':bw,'codecs':codecs})
    elif kind=='DASH' or '.mpd' in url.lower():
        for i,m in enumerate(re.finditer(r'<Representation\b([^>]*)>',text,re.I)):
            attrs=m.group(1)
            def attr(name):
                mm=re.search(r'\b'+re.escape(name)+r'=["\']([^"\']*)["\']',attrs,re.I);return mm.group(1) if mm else ''
            rid=attr('id') or str(i+1);w=attr('width');h=attr('height');bw=int(attr('bandwidth') or 0);codecs=attr('codecs')
            label=' · '.join(x for x in [f'{w}x{h}' if w and h else '',f'{round(bw/1000)} kbps' if bw else '',codecs] if x) or f'DASH rep {i+1}'
            variants.append({'id':rid,'label':label,'bandwidth':bw,'codecs':codecs})
    reply(req,variants=variants)

def preview(req):
    url=req.get('url','');_,_,pl,_=get_paths()
    cmd=[str(pl),'-autoexit']+http_args(req)+[url]
    subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=env(),creationflags=creationflags());reply(req,message='FFplay iniciado.')

def unique_output(name,directory=None):
    d=Path(expand(directory)) if directory else out_dir();d.mkdir(parents=True,exist_ok=True);p=d/clean_name(name)
    if CFG.getboolean('OUTPUT','overwrite',fallback=False) or not p.exists():return p
    i=2
    while True:
        q=p.with_name(f'{p.stem} ({i}){p.suffix}')
        if not q.exists():return q
        i+=1

def ff_time(v):
    try:
        h,m,s=v.split(':');return int(h)*3600+int(m)*60+float(s)
    except Exception:return 0.0

def build_codec_args(mode,req):
    audio=req.get('audio_track','all');subs=req.get('subtitle_track','all')
    args=[]
    if mode in ('audio_mp3','audio_flac'):
        args += ['-vn'];args += ['-map','0:a:0?'] if audio=='all' else ['-map',f'0:a:{audio}?']
        args += ['-c:a','libmp3lame','-b:a',CFG.get('CONVERSION','audio_bitrate',fallback='192k')] if mode=='audio_mp3' else ['-c:a','flac']
    else:
        args += ['-map','0:v?'];args += ['-map','0:a?'] if audio=='all' else ['-map',f'0:a:{audio}?']
        if subs!='none':args += ['-map','0:s?'] if subs=='all' else ['-map',f'0:s:{subs}?']
        if mode=='copy':args += ['-c','copy']
        elif mode=='h264':args += ['-c:v','libx264','-preset',CFG.get('CONVERSION','video_preset',fallback='medium'),'-crf',CFG.get('CONVERSION','video_crf',fallback='22'),'-c:a','aac','-b:a',CFG.get('CONVERSION','audio_bitrate',fallback='192k'),'-c:s','copy']
        elif mode=='hevc':args += ['-c:v','libx265','-preset',CFG.get('CONVERSION','video_preset',fallback='medium'),'-crf',CFG.get('CONVERSION','video_crf',fallback='24'),'-c:a','aac','-b:a',CFG.get('CONVERSION','audio_bitrate',fallback='192k'),'-c:s','copy']
        else:raise ValueError('Modo de conversión desconocido.')
    return args

def drain_stderr(pipe,buf):
    try:
        for line in iter(pipe.readline,''):
            if line:buf.append(line.rstrip())
    except Exception:pass

def run_ffmpeg_attempt(jid,req,output,mode,duration,meta):
    f,_,_,_=get_paths();max_seconds=float(req.get('max_seconds') or 0)
    cmd=[str(f),'-hide_banner','-loglevel','warning','-nostdin']+input_args(req)
    if max_seconds>0:cmd += ['-t',str(max_seconds)]
    cmd += build_codec_args(mode,req)
    cmd += ['-progress','pipe:1','-nostats','-y' if CFG.getboolean('OUTPUT','overwrite',fallback=False) else '-n',str(output)]
    log('CMD: '+' '.join(map(str,cmd)))
    errbuf=deque(maxlen=220)
    p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',env=env(),bufsize=1,creationflags=creationflags())
    with JOB_LOCK:JOBS[jid]=p
    t=threading.Thread(target=drain_stderr,args=(p.stderr,errbuf),daemon=True);t.start()
    data={};last=0
    for line in p.stdout:
        line=line.strip()
        if '=' in line:
            k,v=line.split('=',1);data[k]=v
        if line=='progress=continue' and time.time()-last>.25:
            last=time.time();sec=ff_time(data.get('out_time','0:0:0'));pct=(sec/duration*100) if duration>0 else 0
            speed=data.get('speed','--');eta='--'
            try:
                sp=float(speed.rstrip('x'));eta=time.strftime('%H:%M:%S',time.gmtime(max(0,(duration-sec)/sp))) if sp>0 and duration else '--'
            except Exception:pass
            send({'event':'progress','job_id':jid,'filename':output.name,'output':str(output),'percent':min(99.9,pct),'speed':speed,'eta':eta,'out_time':data.get('out_time',''),'total_size':int(data.get('total_size','0') or 0),'mode_running':mode,**meta})
    rc=p.wait();t.join(timeout=1)
    with JOB_LOCK:JOBS.pop(jid,None)
    return rc,'\n'.join(errbuf),data

def job_worker(jid,req,output,batch_id='',batch_index=0,batch_total=0):
    meta={'batch_id':batch_id,'batch_index':batch_index,'batch_total':batch_total} if batch_id else {}
    duration=0
    try:
        _,fp,_,_=get_paths();q=subprocess.run([str(fp),'-v','error','-show_entries','format=duration','-of','default=nk=1:nw=1']+input_args(req),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,env=env(),timeout=30,creationflags=creationflags())
        try:duration=float((q.stdout or '0').strip())
        except Exception:duration=0
    except Exception:pass
    send({'event':'started','job_id':jid,'filename':output.name,'output':str(output),'startedAt':int(time.time()*1000),'percent':0,**meta})
    requested=req.get('mode','copy')
    attempts=['copy','h264'] if requested=='auto' else [requested]
    last_err=''
    for attempt_no,mode in enumerate(attempts,1):
        if attempt_no>1:
            try:
                if output.exists():output.unlink()
            except Exception:pass
            send({'event':'retry','job_id':jid,'filename':output.name,'output':str(output),'percent':0,'message':'Remux no compatible; reintentando automáticamente en H.264 + AAC.','mode_running':mode,**meta})
        try:
            rc,err,data=run_ffmpeg_attempt(jid,req,output,mode,duration,meta)
        except Exception as e:
            rc=-999;err=str(e);data={}
        last_err=err
        if rc==0:
            send({'event':'complete','job_id':jid,'filename':output.name,'output':str(output),'percent':100,'speed':data.get('speed',''),'eta':'00:00:00','out_time':data.get('out_time',''),'total_size':int(data.get('total_size','0') or 0),'mode_running':mode,**meta});return
        if rc in (-15,-9,255):
            send({'event':'cancelled','job_id':jid,'filename':output.name,'percent':0,**meta});return
    send({'event':'error','job_id':jid,'filename':output.name,'error':(last_err or 'FFmpeg finalizó con error.')[-7000:],**meta})

def select_folder(req):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk();root.withdraw();root.attributes('-topmost',True);root.update()
        initial=str(out_dir())
        folder=filedialog.askdirectory(title='Selecciona la carpeta para descargar todos los videos',initialdir=initial if Path(initial).exists() else str(Path.home()))
        root.destroy();reply(req,folder=folder or '')
    except Exception as e:raise RuntimeError(f'No se pudo abrir el selector de carpeta: {e}')

def batch_worker(batch_id,items,directory):
    total=len(items)
    for i,item in enumerate(items,1):
        try:
            if not item.get('url','').startswith(('http://','https://')):continue
            jid=f'{batch_id}-{i:03d}';output=unique_output(item.get('filename',f'video_{i:03d}.mkv'),directory)
            job_worker(jid,dict(item),output,batch_id,i,total)
        except Exception as e:send({'event':'error','job_id':f'{batch_id}-{i:03d}','filename':item.get('filename',f'video_{i:03d}.mkv'),'error':str(e),'batch_id':batch_id,'batch_index':i,'batch_total':total})
    send({'event':'batch_complete','batch_id':batch_id,'batch_total':total,'folder':directory})

def batch_download(req):
    f,_,_,_=get_paths()
    if not okexe(f):raise RuntimeError(f'FFmpeg no está disponible: {f}')
    items=req.get('items') or []
    if not items:raise ValueError('No se recibieron videos para el lote.')
    directory=expand(req.get('output_dir') or str(out_dir()));Path(directory).mkdir(parents=True,exist_ok=True)
    bid=uuid.uuid4().hex[:8];reply(req,batch_id=bid,count=len(items),folder=directory)
    threading.Thread(target=batch_worker,args=(bid,[dict(x) for x in items],directory),daemon=True).start()

def download(req):
    f,_,_,_=get_paths()
    if not okexe(f):raise RuntimeError(f'FFmpeg no está disponible: {f}')
    if not req.get('url','').startswith(('http://','https://')):raise ValueError('URL multimedia no válida.')
    jid=uuid.uuid4().hex[:12];output=unique_output(req.get('filename','video.mkv'));reply(req,job_id=jid,output=str(output));threading.Thread(target=job_worker,args=(jid,dict(req),output),daemon=True).start()

def cancel(req):
    jid=req.get('job_id','')
    with JOB_LOCK:p=JOBS.get(jid)
    if p and p.poll() is None:p.terminate();reply(req,message='Cancelación solicitada.')
    else:reply(req,message='El trabajo ya no está activo.')

def open_output(req):
    d=out_dir();d.mkdir(parents=True,exist_ok=True)
    if os.name=='nt':os.startfile(str(d))
    else:subprocess.Popen(['xdg-open',str(d)])
    reply(req,message='Carpeta abierta.')


# Optional YouTube provider. Does not affect legacy FFmpeg downloads.
def youtube_inspect(req):
    import youtube_provider
    reply(req, video=youtube_provider.inspect(req.get('url', '')))

def youtube_download_worker(jid, req, directory):
    import youtube_provider
    url = req.get('url', '')
    quality = str(req.get('quality', 'best'))
    output_format = str(req.get('format', 'mkv'))
    try:
        f, _, _, _ = get_paths()
        command = youtube_provider.download_args(url, directory, quality, output_format,
                                                  str(f.parent) if f.exists() else None)
        send({'event':'started','job_id':jid,'filename':'YouTube','percent':0,'startedAt':int(time.time()*1000)})
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding='utf-8', errors='replace',
                                creationflags=creationflags(), bufsize=1)
        with JOB_LOCK:
            JOBS[jid] = proc
        output_name = ''
        progress_re = re.compile(r'\[download\]\s+(\d+(?:\.\d+)?)%')
        for line in proc.stdout:
            match = progress_re.search(line)
            if match:
                send({'event':'progress','job_id':jid,'filename':output_name or 'YouTube',
                      'percent':float(match.group(1)), 'speed':'', 'eta':'--'})
            if '[Merger] Merging formats into ' in line or '[ExtractAudio] Destination: ' in line:
                output_name = line.split(': ', 1)[-1].strip().strip('"')
        rc = proc.wait()
        with JOB_LOCK:
            JOBS.pop(jid, None)
        if rc == 0:
            send({'event':'complete','job_id':jid,'filename':output_name or 'YouTube',
                  'output':output_name or str(directory),'percent':100})
        elif rc in (-15,-9,255):
            send({'event':'cancelled','job_id':jid,'filename':'YouTube'})
        else:
            send({'event':'error','job_id':jid,'filename':'YouTube',
                  'error':'yt-dlp no pudo completar el trabajo. Verifica la fuente y las dependencias.'})
    except Exception as exc:
        with JOB_LOCK:
            JOBS.pop(jid, None)
        send({'event':'error','job_id':jid,'filename':'YouTube','error':str(exc)[:500]})

def youtube_download(req):
    import youtube_provider
    youtube_provider.normalize_video_url(req.get('url', ''))
    youtube_provider.download_args(req['url'], out_dir(), str(req.get('quality','best')),
                                   str(req.get('format','mkv')))
    if not youtube_provider.check_installed():
        raise RuntimeError('Falta yt-dlp. Instálalo con: python -m pip install -U yt-dlp')
    directory = out_dir()
    directory.mkdir(parents=True, exist_ok=True)
    jid = uuid.uuid4().hex[:12]
    reply(req, job_id=jid, output=str(directory))
    threading.Thread(target=youtube_download_worker, args=(jid, dict(req), directory), daemon=True).start()

def dispatch(req):
    c=req.get('command');fn={'ping':ping,'get_config':get_config,'set_config':set_config,'auto_detect':auto_detect,'probe':probe,'inspect_manifest':inspect_manifest,'preview':preview,'select_folder':select_folder,'batch_download':batch_download,'download':download,'cancel':cancel,'open_output':open_output,'youtube_inspect':youtube_inspect,'youtube_download':youtube_download}.get(c)
    if not fn:raise ValueError(f'Comando desconocido: {c}')
    fn(req)

def main():
    while True:
        try:
            req=read_msg()
            if req is None:break
            try:dispatch(req)
            except Exception as e:log(traceback.format_exc());fail(req,e)
        except Exception:log(traceback.format_exc());break
if __name__=='__main__':main()
