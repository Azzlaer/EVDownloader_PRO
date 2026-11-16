# Video MKV Downloader PRO

**Video MKV Downloader PRO** es una extensin para **Google Chrome** diseada para detectar videos y streams multimedia reproducidos desde el navegador y permitir su descarga, anlisis y conversin utilizando **FFmpeg** como motor local.

El objetivo del proyecto es ofrecer una herramienta avanzada de descarga y conversin de video directamente desde Chrome, manteniendo toda la interaccin principal dentro de la extensin.

> La extensin est pensada para descargar contenido propio, contenido con permiso del autor o contenido cuyo uso y descarga estn permitidos.

---

## Caractersticas principales

Video MKV Downloader PRO puede:

-  Detectar videos reproducidos dentro de una pgina web.
-  Inspeccionar elementos HTML `<video>` y `<audio>`.
-  Detectar solicitudes multimedia realizadas por la pestaa.
-  Detectar streams HLS mediante archivos `.m3u8`.
-  Detectar streams DASH mediante archivos `.mpd`.
-  Detectar archivos MP4, WebM y otros formatos compatibles.
-  Analizar video y audio mediante `ffprobe`.
-  Abrir una vista previa mediante `ffplay`.
-  Descargar y guardar videos en formato MKV.
-  Hacer remux sin prdida de calidad utilizando `-c copy`.
-  Convertir video a H.264 + AAC.
-  Convertir video a H.265/HEVC + AAC.
-  Extraer audio a MP3.
-  Extraer audio a FLAC.
-  Seleccionar pistas de audio.
-  Mantener, seleccionar o excluir subttulos.
-  Utilizar cookies de la sesin de Chrome cuando sean necesarias.
-  Reutilizar headers como `Referer`, `Origin` y `Authorization`.
-  Mantener una cola de descargas.
-  Mostrar progreso de procesamiento.
-  Mostrar velocidad de FFmpeg.
-  Mostrar tiempo estimado restante cuando sea posible.
-  Cancelar trabajos activos.
-  Descargar automticamente todos los videos detectados.
-  Elegir una carpeta de destino para descargas masivas.
-  Utilizar un modo automtico que intenta remux y, si falla, convierte a H.264.

---

# Arquitectura del proyecto

Chrome no permite que una extensin ejecute directamente programas como:

- `ffmpeg.exe`
- `ffprobe.exe`
- `ffplay.exe`

Tampoco permite cargar directamente DLL nativas como:

- `avcodec-*.dll`
- `avformat-*.dll`
- `avutil-*.dll`
- `swscale-*.dll`
- `swresample-*.dll`

Por este motivo el proyecto utiliza dos componentes.

```text
Google Chrome
      |
      v
+-----------------------------+
| Video MKV Downloader PRO    |
| Extensin Manifest V3       |
+--------------+--------------+
               |
               | Native Messaging
               v
+-----------------------------+
| Native Host local           |
| Python                      |
+--------------+--------------+
               |
               v
+-----------------------------+
| FFmpeg / FFprobe / FFplay   |
| DLL de FFmpeg               |
+-----------------------------+
```

La extensin es la interfaz principal.

El Native Host solamente funciona como puente entre Chrome y FFmpeg.

No es necesario utilizar manualmente el programa Python durante el funcionamiento normal.

---

# Deteccin de videos

La extensin utiliza varios mtodos de deteccin.

## Elementos HTML

Busca reproductores como:

```html
<video>
<audio>
<source>
```

y registra sus URLs.

---

## Trfico multimedia

La extensin observa determinadas solicitudes realizadas por la pestaa para identificar recursos multimedia.

Puede detectar, entre otros:

```text
.mp4
.webm
.mov
.m4v
.ts
.m2ts
.m3u8
.mpd
.m4s
.mp3
.aac
.ogg
.wav
```

Los fragmentos internos de streams se utilizan nicamente como informacin auxiliar y normalmente no se muestran como videos independientes.

---

# HLS

Los streams HLS normalmente utilizan archivos:

```text
.m3u8
```

Un manifiesto HLS puede contener varias calidades.

Ejemplo:

```text
360p
480p
720p
1080p
1440p
2160p / 4K
```

La extensin puede detectar el manifiesto para que FFmpeg procese automticamente los segmentos correspondientes.

---

# DASH

Los streams DASH normalmente utilizan archivos:

```text
.mpd
```

Un manifiesto DASH puede contener representaciones separadas para:

```text
Video
Audio
Subttulos
```

FFmpeg puede combinar estos streams durante la descarga o conversin.

---

# Modo Automtico

El modo recomendado es:

```text
 Automtico
```

Primero intenta realizar un remux:

```bash
ffmpeg -i INPUT -c copy OUTPUT.mkv
```

Esto evita volver a codificar el video.

Ventajas:

- Mxima calidad.
- Muy rpido.
- Bajo uso de CPU.
- Sin prdida generacional.

Si el remux falla por incompatibilidad de codecs o contenedor, el sistema realiza automticamente un segundo intento utilizando:

```text
H.264 + AAC
```

De esta forma se obtiene un archivo MKV ampliamente compatible.

---

# Remux MKV

El modo:

```text
 Remux MKV
```

copia los streams originales.

Conceptualmente:

```bash
ffmpeg -i video -map 0 -c copy video.mkv
```

No existe recodificacin.

Por tanto:

```text
Calidad original -> Calidad original
```

---

# Conversin H.264

El modo H.264 utiliza normalmente:

```text
Video : H.264 / AVC
Audio : AAC
Contenedor : MKV
```

Es una buena opcin cuando se busca mxima compatibilidad.

---

# Conversin H.265 / HEVC

El modo H.265 utiliza:

```text
Video : H.265 / HEVC
Audio : AAC
Contenedor : MKV
```

H.265 puede generar archivos ms pequeos manteniendo buena calidad, aunque requiere ms CPU y tarda ms en codificar.

---

# Extraccin de audio

La extensin tambin permite extraer nicamente el audio.

Formatos disponibles:

```text
MP3
FLAC
```

MP3 es recomendable para compatibilidad general.

FLAC es recomendable cuando se desea conservar audio sin prdida.

---

# Descargar todos

La funcin:

```text
 Descargar todos los videos detectados
```

permite procesar automticamente todos los videos encontrados en la pestaa.

El sistema:

1. Analiza todos los recursos detectados.
2. Elimina duplicados.
3. Ignora fragmentos internos de HLS/DASH.
4. Permite elegir una carpeta.
5. Genera una cola.
6. Procesa los videos uno por uno.
7. Aplica automticamente el modo de conversin seleccionado.
8. Guarda cada archivo en la carpeta seleccionada.

Ejemplo:

```text
Videos\
|
+-- video_001.mkv
+-- video_002.mkv
+-- video_003.mkv
+-- video_004.mkv
```

El procesamiento secuencial evita saturar:

```text
CPU
Memoria
Disco
Conexin de red
```

---

# Cola de trabajos

Cada descarga o conversin genera un trabajo.

Los estados posibles pueden incluir:

```text
Esperando
Iniciando
Procesando
Reintentando
Completado
Cancelado
Error
```

La extensin conserva el estado de los trabajos mediante almacenamiento de sesin de Chrome para evitar perder informacin si el Service Worker de Manifest V3 se suspende.

---

# Cookies y sesiones

Algunos servidores no permiten descargar un video utilizando solamente su URL.

Pueden requerir:

```text
Cookies
Referer
Origin
Authorization
User-Agent
```

La extensin puede reutilizar informacin de la sesin actual del navegador para que FFmpeg pueda solicitar el mismo contenido.

Esto ayuda en situaciones donde FFmpeg responde con errores como:

```text
HTTP 401 Unauthorized
HTTP 403 Forbidden
```

---

# Configuracin de FFmpeg

El proyecto permite configurar:

```text
ffmpeg.exe
ffprobe.exe
ffplay.exe
directorio de DLL
carpeta de salida
CRF
preset
bitrate de audio
User-Agent
reconexin de streams
```

Ejemplo:

```ini
[FFMPEG]

ffmpeg = C:\ffmpeg\bin\ffmpeg.exe
ffprobe = C:\ffmpeg\bin\ffprobe.exe
ffplay = C:\ffmpeg\bin\ffplay.exe

dll_dir = C:\ffmpeg\bin
```

---

# DLL de FFmpeg

Si utilizas una compilacin Shared de FFmpeg, probablemente encontrars archivos similares a:

```text
avcodec-62.dll
avformat-62.dll
avutil-60.dll
swscale-9.dll
swresample-6.dll
avfilter-11.dll
avdevice-62.dll
```

El directorio configurado en:

```text
dll_dir
```

se agrega temporalmente al entorno de ejecucin del Native Host.

---

# Carpeta de salida

Puedes definir una carpeta predeterminada.

Ejemplo:

```ini
[OUTPUT]

directory = D:\Videos\MKV
```

Los archivos descargados individualmente se guardarn all salvo que una funcin especfica utilice otra carpeta.

---

# Requisitos

## Google Chrome

Se recomienda utilizar una versin reciente de Google Chrome compatible con Manifest V3.

---

## Python

El Native Host requiere:

```text
Python 3.10+
```

Se recomienda:

```text
Python 3.11
Python 3.12
```

---

## FFmpeg

Debes disponer de una compilacin de FFmpeg que incluya:

```text
ffmpeg.exe
ffprobe.exe
ffplay.exe
```

FFmpeg debe tener soporte para los codecs que quieras utilizar.

---

# Instalacin de la extensin

Abre Chrome y entra a:

```text
chrome://extensions
```

Activa:

```text
Modo de desarrollador
```

Selecciona:

```text
Cargar descomprimida
```

y elige:

```text
extension\
```

Chrome asignar un identificador a la extensin.

Ejemplo:

```text
abcdefghijklmnopqrstuvwxyzabcdef
```

Guarda ese ID.

---

# Instalacin del Native Host

Dentro de:

```text
native_host\
```

ejecuta:

```text
INSTALL_NATIVE_HOST.bat
```

El instalador solicitar:

```text
ID de la extensin
```

Introduce el ID mostrado en:

```text
chrome://extensions
```

El instalador registrar el Native Messaging Host en Windows.

---

# Registro de Windows

El Native Host se registra en:

```text
HKEY_CURRENT_USER
```

bajo una ruta similar a:

```text
Software\Google\Chrome\NativeMessagingHosts\
```

Esto permite que Chrome encuentre el programa local autorizado.

---

# Flujo normal de uso

```text
1. Abrir una pgina con video

2. Comenzar la reproduccin

3. Abrir Video MKV Downloader PRO

4. Pulsar Detectar

5. Seleccionar el video

6. Opcionalmente analizarlo con FFprobe

7. Seleccionar modo

   Automtico
   Remux
   H.264
   H.265
   MP3
   FLAC

8. Pulsar Descargar

9. Seguir el progreso

10. Abrir el archivo generado
```

---

# FFprobe

FFprobe permite identificar:

```text
Formato
Duracin
Resolucin
Codec
FPS
Bitrate
Audio
Nmero de canales
Frecuencia de audio
Subttulos
```

Esto ayuda a decidir si es mejor hacer remux o conversin.

---

# FFplay

FFplay puede utilizarse para comprobar rpidamente una fuente detectada antes de descargarla.

Permite verificar:

```text
Es el video correcto?
Tiene audio?
La URL todava funciona?
```

---

# Estabilidad de Manifest V3

Google Chrome utiliza Service Workers para las extensiones Manifest V3.

Estos procesos pueden suspenderse cuando no estn siendo utilizados.

Por este motivo Video MKV Downloader PRO guarda informacin relevante mediante:

```text
chrome.storage.session
```

incluyendo datos de deteccin y cola.

Esto evita depender solamente de variables temporales en memoria.

---

# Native Messaging

Native Messaging es el mecanismo mediante el cual la extensin se comunica con Python.

Conceptualmente:

```text
Chrome
  v JSON
Native Messaging
  v
Python
  v
FFmpeg
```

El Native Host puede responder tambin con eventos como:

```text
progreso
velocidad
estado
errores
resultado
```

---

# DRM

El proyecto **no elimina ni intenta romper sistemas DRM**.

Entre ellos:

```text
Widevine
Encrypted Media Extensions (EME)
PlayReady
FairPlay
```

Si el contenido est cifrado mediante DRM, disponer de la URL del manifiesto no significa disponer del video descifrado.

El proyecto no incluye herramientas destinadas a evadir este tipo de proteccin.

---

# Limitaciones

Ningn detector de video basado en navegador puede garantizar compatibilidad con el 100% de las pginas.

Algunas pginas pueden:

- generar URLs temporales;
- modificar tokens constantemente;
- utilizar reproductores propietarios;
- usar WebSockets;
- utilizar Media Source Extensions;
- cifrar segmentos;
- requerir APIs internas;
- utilizar DRM;
- separar audio y video;
- generar manifiestos dinmicamente.

Por esta razn el proyecto utiliza varios mtodos de deteccin en conjunto.

---

# Privacidad

Video MKV Downloader PRO procesa la informacin localmente.

La conversin mediante FFmpeg se realiza en el equipo del usuario.

Las URLs detectadas se utilizan exclusivamente para realizar las operaciones solicitadas.

No es necesario enviar los videos a un servidor externo para convertirlos.

---

# Estructura general

```text
VideoMKV_Downloader/
|
+-- extension/
|   |
|   +-- manifest.json
|   +-- service_worker.js
|   +-- content.js
|   +-- popup.html
|   +-- popup.css
|   +-- popup.js
|   +-- options.html
|   +-- options.css
|   +-- options.js
|
+-- native_host/
|   |
|   +-- host.py
|   +-- config.ini
|   +-- install_host.py
|   +-- uninstall_host.py
|   +-- INSTALL_NATIVE_HOST.bat
|   +-- UNINSTALL_NATIVE_HOST.bat
|
+-- README.md
```

---

# Objetivo del proyecto

El objetivo de Video MKV Downloader PRO es construir una herramienta multimedia para Google Chrome que combine:

```text
Detector de videos
+
Gestor de streams
+
Descargador
+
FFmpeg
+
Conversor
+
Cola de trabajos
+
Interfaz integrada en Chrome
```

manteniendo FFmpeg como motor local y utilizando la extensin Chrome como interfaz principal.

---

# Recomendacin de uso

Para la mayora de los videos:

```text
 Automtico
```

es la opcin recomendada.

El sistema intenta conservar primero el contenido original mediante remux y solamente recodifica cuando es necesario.

Descarga esto para que puedas usar el script: https://www.mediafire.com/file/36vvlviz8kku0v6/bin.rar

---

# Uso responsable

Utiliza esta herramienta nicamente con contenido que tengas derecho a descargar.

El usuario es responsable de respetar:

- derechos de autor;
- licencias;
- trminos de servicio;
- restricciones del sitio;
- legislacin aplicable.

---

## Video MKV Downloader PRO

**Google Chrome + Native Messaging + Python + FFmpeg**

Una extensin avanzada para detectar, descargar, analizar y convertir contenido multimedia desde el navegador.

## Pruebas de regresión

Las pruebas no requieren instalar dependencias ni disponer de FFmpeg:

```bash
python -m unittest discover -s tests -v
node --test tests/service_worker.test.js
```

Se comprueban los nombres de salida de ambas versiones del Native Host y la
limpieza de peticiones y temporizadores del service worker. GitHub Actions ejecuta
estas pruebas en Linux y Windows con Python 3.12 y Node.js 22.

Los cambios en `native_host/host.py` y `native_host_full/host_runtime.py` requieren
recompilar los ejecutables si utilizas la distribución EXE. El flujo de pruebas
no regenera los binarios incluidos en el repositorio.
