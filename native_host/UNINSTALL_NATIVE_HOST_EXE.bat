@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title EVDownloader PRO - Desinstalar Native Host

set "HOSTNAME=com.azzlaer.videomkvhost"
set "MANIFEST=%~dp0native_host_manifest.json"

echo ============================================================
echo   EVDownloader PRO - DESINSTALAR NATIVE HOST
 echo ============================================================
echo.

echo [1/2] Eliminando registro de Google Chrome...
reg query "HKCU\Software\Google\Chrome\NativeMessagingHosts\%HOSTNAME%" >nul 2>nul
if errorlevel 1 (
    echo       El host no estaba registrado en Chrome.
) else (
    reg delete "HKCU\Software\Google\Chrome\NativeMessagingHosts\%HOSTNAME%" /f >nul
    if errorlevel 1 goto :error
    echo       Registro eliminado.
)

echo [2/2] Eliminando manifiesto generado...
if exist "%MANIFEST%" (
    del /Q "%MANIFEST%"
    echo       Manifiesto eliminado.
) else (
    echo       No habia manifiesto para eliminar.
)

echo.
echo ============================================================
echo [OK] Native Host desinstalado.
echo El EXE compilado se conserva en dist\native_host.exe.
echo ============================================================
pause
exit /b 0

:error
echo.
echo [ERROR] No se pudo completar la desinstalacion.
pause
exit /b 1
