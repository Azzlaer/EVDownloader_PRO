# Video MKV Downloader PRO v3.1\n\nExtensión **Google Chrome Manifest V3** con motor local FFmpeg mediante Native Messaging. Inspirada en el flujo de los descargadores multimedia avanzados, pero **sin cuotas artificiales, temporizadores, marcas de agua ni límite de descargas HLS/DASH**.\n\n## Funciones PRO\n\n- Detección de MP4, WebM, HLS (`.m3u8`), DASH (`.mpd`), audio y segmentos.\n- Detección desde DOM + tráfico de red.\n- Lectura de variantes HLS (resolución/bitrate/codecs).\n- Inspección de representaciones DASH.\n- Pasa **cookies de la sesión de Chrome**, Referer y Origin a FFmpeg para mejorar compatibilidad con streams autenticados.\n- Descarga/remux ilimitado a MKV.\n- Conversión H.264/AAC o H.265/AAC.\n- Extracción de audio MP3 o FLAC.\n- Grabación de streams LIVE por minutos o hasta cancelar.\n- Audio/subtítulos seleccionables.\n- Cola, progreso, velocidad, ETA y cancelación.\n- FFprobe y FFplay integrados desde la interfaz Chrome.\n- Configuración de FFmpeg/FFprobe/FFplay y DLL desde Opciones.\n\n## Límites reales\n\nNo intenta descifrar **DRM/Widevine/EME**. Los medios cifrados/protegidos no son compatibles. También pueden existir restricciones propias de sitios concretos o de las políticas de distribución de Chrome Web Store.\n\n## Instalación\n\n1. `chrome://extensions` → activa **Modo desarrollador**.\n2. **Cargar descomprimida** → selecciona `extension`.\n3. Copia el ID asignado a la extensión.\n4. Ejecuta `native_host/INSTALL_NATIVE_HOST.bat` y pega el ID.\n5. Reinicia Chrome.\n6. Abre **Opciones** de la extensión y configura/autodetecta FFmpeg.\n\n## FFmpeg shared build\n\nSi usas DLL, configura `dll_dir` con la carpeta que contiene `avcodec-*.dll`, `avformat-*.dll`, `avutil-*.dll`, `swresample-*.dll`, etc.\n

## 📦 Descarga masiva automática (v3.1)

La pestaña **Detector** ahora incluye **Descargar todos los videos detectados**.

1. Reproduce o navega por los videos de la página.
2. Pulsa **Detectar**.
3. Elige el modo de conversión (Remux MKV, H.264, H.265, MP3 o FLAC).
4. Pulsa **Descargar todos los videos detectados**.
5. Windows mostrará un selector de carpeta.
6. La extensión elimina URLs duplicadas exactas y descarta fragmentos HLS/DASH (`SEGMENT`).
7. Los videos se procesan **uno por uno** para no saturar CPU/red/disco.
8. La pestaña **Cola** muestra el progreso individual y el progreso global del lote.

Los nombres quedan numerados, por ejemplo `Pagina_001_hls.mkv`, `Pagina_002_mp4.mkv`, etc.

---

## v3.2 Stability Update

Esta revisión se centra en estabilidad real bajo Chrome Manifest V3 y FFmpeg:

- Persistencia de videos detectados y cola en `chrome.storage.session` para sobrevivir a suspensiones del service worker.
- Captura de headers multimedia útiles (`Referer`, `Origin`, `Authorization`, `Accept-Language`) y reutilización local con FFmpeg.
- Lectura Native Messaging robusta mediante `read_exact`, evitando mensajes parciales.
- Drenaje concurrente de `stderr` de FFmpeg para impedir bloqueos por buffer lleno.
- Nuevo modo **Automático**: primero intenta remux sin pérdida y, si falla por incompatibilidad, reintenta H.264 + AAC.
- Mejor deduplicación del botón **Descargar todos**.
- Estado de trabajos persistente mientras Chrome siga abierto.
- Mejor progreso para fuentes cuya duración no puede conocerse de antemano.
- Limpieza de trabajos finalizados desde la pestaña Cola.

### Actualización desde v3.1

1. Desactiva o elimina la v3.1 en `chrome://extensions`.
2. Carga como descomprimida la carpeta `extension` de v3.2.
3. Ejecuta nuevamente `native_host/INSTALL_NATIVE_HOST.bat` y pega el ID mostrado por Chrome.
4. Abre Opciones y prueba el estado de FFmpeg/FFprobe/FFplay.

El Native Host sigue siendo únicamente el motor técnico; la interfaz de uso continúa siendo la extensión de Google Chrome.

No se implementa bypass de DRM/Widevine/EME.
