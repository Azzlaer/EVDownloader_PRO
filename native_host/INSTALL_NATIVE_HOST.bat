@echo off
title Video MKV Downloader - Native Host
cd /d "%~dp0"
echo Carga primero la extension en chrome://extensions y copia su ID.
set /p EXTID=ID de la extension: 
python install_host.py %EXTID%
pause
