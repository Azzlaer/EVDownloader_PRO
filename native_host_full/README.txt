EVDownloader PRO - Native Host Manager
======================================

Este proyecto compila UN SOLO ejecutable:

    EVDownloader_NativeHost_Manager.exe

El mismo archivo tiene dos funciones:

1) Si lo abres tú:
   - Muestra una interfaz gráfica.
   - Detecta el ID de la extensión Chrome cuando es posible.
   - INICIAR / PROBAR: lanza una prueba real del protocolo Native Messaging y ejecuta el comando ping del host.
   - INSTALAR: copia el EXE a una ruta estable dentro de LocalAppData, crea el manifiesto y registra el host en HKCU.
   - DESINSTALAR: elimina el registro del host y el manifiesto.

2) Si Google Chrome lo ejecuta:
   - Detecta el argumento chrome-extension://... que Chrome entrega al Native Messaging Host.
   - No abre la GUI.
   - Ejecuta directamente el host original de EVDownloader PRO mediante stdin/stdout.

RUTA DE INSTALACION
-------------------
%LOCALAPPDATA%\EVDownloaderPRO\NativeHost\

Archivos importantes:
- EVDownloader_NativeHost_Manager.exe
- native_host_manifest.json
- config.ini
- videomkv_host.log

REGISTRO
--------
HKEY_CURRENT_USER\Software\Google\Chrome\NativeMessagingHosts\com.azzlaer.videomkvhost

COMPILAR
--------
1. Tener Python instalado en Windows.
2. Ejecutar BUILD_EXE.bat.
3. El EXE quedará en:
   dist\EVDownloader_NativeHost_Manager.exe

USO
---
1. Carga tu extensión desde chrome://extensions si todavía no está cargada.
2. Abre EVDownloader_NativeHost_Manager.exe.
3. Verifica que aparezca el ID de extensión correcto.
4. Pulsa INSTALAR.
5. Pulsa INICIAR / PROBAR.
6. Cierra completamente Chrome y vuelve a abrirlo.

IMPORTANTE
----------
El EXE se compila como aplicación de consola porque Native Messaging necesita stdin/stdout binarios.
Cuando lo abres normalmente, el programa oculta automáticamente la consola y muestra sólo la GUI.
Cuando Chrome lo inicia, conserva stdin/stdout para que el protocolo Native Messaging funcione correctamente.
