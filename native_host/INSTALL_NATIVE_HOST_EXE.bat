@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title EVDownloader PRO - Instalar Native Host

set "HOSTNAME=com.azzlaer.videomkvhost"
set "HOSTEXE=%~dp0dist\native_host.exe"
set "MANIFEST=%~dp0native_host_manifest.json"

echo ============================================================
echo   EVDownloader PRO - INSTALAR NATIVE HOST
 echo ============================================================
echo.

if not exist "%HOSTEXE%" (
    echo [ERROR] No existe el ejecutable:
    echo         %HOSTEXE%
    echo.
    echo Ejecuta primero COMPILE_NATIVE_HOST.bat
    pause
    exit /b 1
)

set /p "EXTID=ID de la extension Chrome: "
if "%EXTID%"=="" (
    echo [ERROR] Debes ingresar el ID de la extension.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$id='%EXTID%'; if($id -notmatch '^[a-p]{32}$'){Write-Host '[ERROR] ID de extension invalido.' -ForegroundColor Red; exit 2}"
if errorlevel 1 (
    pause
    exit /b 1
)

echo.
echo [1/3] Creando manifiesto Native Messaging...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$m=[ordered]@{name='%HOSTNAME%';description='EVDownloader PRO Native Host';path='%HOSTEXE%';type='stdio';allowed_origins=@('chrome-extension://%EXTID%/')};" ^
  "$m ^| ConvertTo-Json -Depth 4 ^| Set-Content -LiteralPath '%MANIFEST%' -Encoding UTF8"
if errorlevel 1 goto :error

echo [2/3] Registrando host para Google Chrome...
reg add "HKCU\Software\Google\Chrome\NativeMessagingHosts\%HOSTNAME%" /ve /t REG_SZ /d "%MANIFEST%" /f >nul
if errorlevel 1 goto :error

echo [3/3] Verificando registro...
reg query "HKCU\Software\Google\Chrome\NativeMessagingHosts\%HOSTNAME%" /ve
if errorlevel 1 goto :error

echo.
echo ============================================================
echo [OK] Native Host instalado correctamente.
echo.
echo Host:      %HOSTEXE%
echo Manifest:  %MANIFEST%
echo Extension: %EXTID%
echo.
echo Cierra completamente Chrome y vuelve a abrirlo.
echo ============================================================
pause
exit /b 0

:error
echo.
echo [ERROR] No se pudo instalar/registrar el Native Host.
pause
exit /b 1
