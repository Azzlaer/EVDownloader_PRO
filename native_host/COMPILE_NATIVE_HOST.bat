@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title EVDownloader PRO - Compilar Native Host

set "SRC=host.py"
set "TMP=.host_build.py"
set "OUTDIR=dist"
set "EXENAME=native_host"

echo ============================================================
echo   EVDownloader PRO - COMPILAR NATIVE HOST
 echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python no esta disponible en PATH.
    echo Instala Python 3.11/3.12 y activa "Add Python to PATH".
    pause
    exit /b 1
)

if not exist "%SRC%" (
    echo [ERROR] No se encontro "%SRC%" en:
    echo         %CD%
    pause
    exit /b 1
)

echo [1/5] Verificando PyInstaller...
python -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo       PyInstaller no esta instalado. Instalando...
    python -m pip install --upgrade pyinstaller
    if errorlevel 1 goto :error
)

echo [2/5] Preparando host para modo EXE...
copy /Y "%SRC%" "%TMP%" >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p='%TMP%'; $s=[IO.File]::ReadAllText($p);" ^
  "$old='BASE=Path(__file__).resolve().parent';" ^
  "$new=\"BASE=(Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent)\";" ^
  "if(-not $s.Contains($old)){Write-Error 'No se encontro la linea BASE esperada en host.py'; exit 2};" ^
  "$s=$s.Replace($old,$new); [IO.File]::WriteAllText($p,$s,[Text.UTF8Encoding]::new($false))"
if errorlevel 1 goto :error

echo [3/5] Limpiando compilaciones anteriores...
if exist "build" rmdir /S /Q "build"
if exist "%OUTDIR%\%EXENAME%.exe" del /Q "%OUTDIR%\%EXENAME%.exe"
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

echo [4/5] Compilando native_host.exe...
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --console ^
  --name "%EXENAME%" ^
  --distpath "%OUTDIR%" ^
  --workpath "build\work" ^
  --specpath "build" ^
  --hidden-import tkinter ^
  "%TMP%"
if errorlevel 1 goto :error

echo [5/5] Copiando configuracion junto al ejecutable...
if exist "config.ini" copy /Y "config.ini" "%OUTDIR%\config.ini" >nul

if exist "%TMP%" del /Q "%TMP%"

echo.
echo ============================================================
echo [OK] Native Host compilado correctamente:
echo      %CD%\%OUTDIR%\%EXENAME%.exe
echo.
echo Siguiente paso: ejecuta INSTALL_NATIVE_HOST_EXE.bat
 echo ============================================================
pause
exit /b 0

:error
echo.
echo [ERROR] No se pudo compilar el Native Host.
if exist "%TMP%" del /Q "%TMP%"
pause
exit /b 1
