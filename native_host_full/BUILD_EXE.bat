@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo   EVDownloader PRO - Compilador Native Host Manager
echo ============================================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Python no esta instalado o no esta en PATH.
        pause
        exit /b 1
    )
    set "PY=python"
)

echo [1/4] Actualizando pip...
%PY% -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [2/4] Instalando PyInstaller...
%PY% -m pip install --upgrade pyinstaller
if errorlevel 1 goto :error

echo [3/4] Limpiando compilaciones anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist EVDownloader_NativeHost_Manager.spec del /q EVDownloader_NativeHost_Manager.spec

echo [4/4] Compilando EXE unico...
%PY% -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --console ^
  --name "EVDownloader_NativeHost_Manager" ^
  --icon "app.ico" ^
  --add-data "config.ini;." ^
  --hidden-import host_runtime ^
  manager.py
if errorlevel 1 goto :error

echo.
echo ============================================================
echo [OK] Compilacion terminada.
echo EXE: %CD%\dist\EVDownloader_NativeHost_Manager.exe
echo ============================================================
explorer "%CD%\dist"
pause
exit /b 0

:error
echo.
echo [ERROR] No se pudo compilar el programa.
pause
exit /b 1
