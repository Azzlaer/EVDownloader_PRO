"""Optional yt-dlp backend for media the user is authorized to download.

No browser cookies are imported. The backend only accepts public YouTube video
URLs, never shell commands or arbitrary extractor options.
"""
import json
import re
import subprocess
import sys
from urllib.parse import parse_qs, urlparse

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"}

def normalize_video_url(url):
    if not isinstance(url, str) or len(url) > 2048:
        raise ValueError("URL de YouTube inválida.")
    u = urlparse(url)
    host = (u.hostname or "").lower()
    if u.scheme != "https" or host not in HOSTS or u.username or u.password or u.port:
        raise ValueError("Solo se admiten enlaces HTTPS de videos públicos de YouTube.")
    if host in {"youtu.be", "www.youtu.be"}:
        ident = u.path.strip("/")
    elif u.path == "/watch":
        ident = parse_qs(u.query).get("v", [""])[0]
    elif u.path.startswith("/shorts/") or u.path.startswith("/live/"):
        ident = u.path.split("/")[2]
    else:
        raise ValueError("Se requiere un enlace a un video, no a una lista o canal.")
    if not VIDEO_ID.fullmatch(ident):
        raise ValueError("Identificador de video inválido.")
    return "https://www.youtube.com/watch?v=" + ident

def executable_prefix():
    return [sys.executable, "-m", "yt_dlp"]

def check_installed(run=subprocess.run):
    result = run(executable_prefix() + ["--version"], capture_output=True, text=True, timeout=10)
    return result.returncode == 0

def inspect(url, run=subprocess.run):
    canonical = normalize_video_url(url)
    try:
        result = run(executable_prefix() + ["--dump-single-json", "--no-playlist", "--skip-download", "--no-warnings", canonical],
                     capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError("yt-dlp no está disponible o no respondió.") from e
    if result.returncode:
        raise RuntimeError("No se pudo consultar este video. Verifica permisos y versión de yt-dlp.")
    raw = json.loads(result.stdout)
    formats = []
    for fmt in raw.get("formats") or []:
        if fmt.get("vcodec") == "none" and fmt.get("acodec") == "none":
            continue
        formats.append({"id": str(fmt.get("format_id", "")), "ext": fmt.get("ext"),
                        "height": fmt.get("height"), "fps": fmt.get("fps"),
                        "vcodec": fmt.get("vcodec"), "acodec": fmt.get("acodec")})
    return {"url": canonical, "id": raw.get("id"), "title": raw.get("title"),
            "duration": raw.get("duration"), "channel": raw.get("channel"),
            "thumbnail": raw.get("thumbnail"), "formats": formats}

def download_args(url, directory, quality="best", output_format="mkv", ffmpeg_location=None):
    canonical = normalize_video_url(url)
    if output_format not in {"mkv", "mp4", "webm", "mp3", "flac", "m4a"}:
        raise ValueError("Formato de salida inválido.")
    if quality not in {"best", "2160", "1440", "1080", "720", "480", "360"}:
        raise ValueError("Calidad inválida.")
    args = executable_prefix() + ["--no-playlist", "--newline", "--no-overwrites",
                                  "--restrict-filenames", "-P", str(directory),
                                  "-o", "%(title).160B [%(id)s].%(ext)s"]
    if ffmpeg_location:
        args += ["--ffmpeg-location", str(ffmpeg_location)]
    if output_format in {"mp3", "flac", "m4a"}:
        args += ["-f", "bestaudio/best", "-x", "--audio-format", output_format]
    else:
        limit = "" if quality == "best" else "[height<=" + quality + "]"
        args += ["-f", "bv*" + limit + "+ba/b" + limit, "--merge-output-format", output_format]
    return args + [canonical]
