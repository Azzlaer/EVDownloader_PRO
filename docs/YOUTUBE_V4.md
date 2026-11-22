# EVDownloader PRO 4.0 — YouTube (primera fase)

Esta rama agrega un proveedor **opcional** basado en yt-dlp para videos públicos de YouTube que el usuario tenga derecho a descargar. Conserva el detector y el motor FFmpeg originales.

## Requisitos

- Python 3.10+ y el Native Messaging Host actual.
- FFmpeg configurado como antes (para fusionar y convertir pistas).
- yt-dlp instalado **en el mismo entorno Python del Native Host**:

```powershell
python -m pip install -U yt-dlp
python -m yt_dlp --version
```

Si el host usa la versión compilada EXE, **recompilar con PyInstaller** incluyendo `yt_dlp` y `native_host_full/youtube_provider.py`. El ejecutable anterior no recibe automáticamente estos cambios. La variante Python directa resulta más simple para probar esta primera fase.

## Uso

1. Actualiza la extensión desde `chrome://extensions`.
2. Confirma que el Native Host funciona.
3. Abre la nueva pestaña YouTube del popup.
4. Introduce un enlace HTTPS de un video público autorizado (watch, shorts, live o youtu.be).
5. Pulsa **Analizar video** para ver metadatos y cantidad de formatos.
6. Elige una calidad máxima y contenedor, pulsa **Descargar** y revisa la pestaña Cola.

Actualmente se admite un video por operación; playlists, autenticación y transmisión en vivo no están implementadas ni garantizadas. La calidad seleccionada es un techo, no una promesa de disponibilidad. La conversión a FLAC no mejora el audio de origen. La salida se almacena en el directorio configurado por el host, con nombres restringidos para Windows.

## Comandos Native Messaging

- `{"command":"youtube_inspect","url":"https://www.youtube.com/watch?v=abcdefghijk"}`
- `{"command":"youtube_download","url":"https://www.youtube.com/watch?v=abcdefghijk","quality":"1080","format":"mkv"}`

Los trabajos generan eventos `started`, `progress`, `complete`, `error` y `cancelled` y reutilizan la cola de Chrome. La cancelación utiliza el comando existente `cancel`.

## Pruebas

```shell
python -m unittest discover -s tests -v
node --test tests/service_worker.test.js
```

## Limitaciones y cumplimiento

- No descarga contenido protegido con DRM ni implementa evasión de restricciones.
- No importa cookies de Chrome; la primera fase trabaja con URLs públicas.
- YouTube puede cambiar el funcionamiento de sus servicios y condiciones de acceso; la compatibilidad no está garantizada.
- Esta funcionalidad puede no ser apta para publicación en Chrome Web Store; revisar las políticas antes de distribuirla.
- En esta primera fase los trabajos son procesos del Native Host y no sobreviven necesariamente a su cierre; persistencia SQLite y reanudación son tareas posteriores.
