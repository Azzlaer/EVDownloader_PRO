#!/usr/bin/env python3
import json,sys,winreg
from pathlib import Path
BASE=Path(__file__).resolve().parent;NAME='com.azzlaer.videomkvhost'
def main():
    ext=(sys.argv[1] if len(sys.argv)>1 else input('ID de la extensión Chrome: ')).strip()
    if not ext or any(c not in 'abcdefghijklmnopqrstuvwxyz' for c in ext):raise SystemExit('ID de extensión inválido.')
    py=Path(sys.executable).resolve();bat=BASE/'native_host.bat';bat.write_text(f'@echo off\r\n"{py}" "{BASE/"host.py"}"\r\n',encoding='utf-8')
    mf=BASE/'native_host_manifest.json';mf.write_text(json.dumps({'name':NAME,'description':'Video MKV Downloader Native Host','path':str(bat),'type':'stdio','allowed_origins':[f'chrome-extension://{ext}/']},indent=2),encoding='utf-8')
    key=rf'Software\Google\Chrome\NativeMessagingHosts\{NAME}'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,key) as k:winreg.SetValueEx(k,'',0,winreg.REG_SZ,str(mf))
    print('Native Host instalado correctamente. Reinicia Chrome.')
if __name__=='__main__':main()
