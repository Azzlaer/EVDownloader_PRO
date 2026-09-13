#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EVDownloader PRO - Native Host Manager
Un único ejecutable sirve como GUI de administración y como Native Messaging Host.
"""

import json
import os
import shutil
import struct
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

APP_NAME = "EVDownloader PRO Native Host"
HOST_NAME = "com.azzlaer.videomkvhost"
DESCRIPTION = "EVDownloader PRO Native Messaging Host"
APPDATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "EVDownloaderPRO" / "NativeHost"
MANIFEST_PATH = APPDATA_DIR / "native_host_manifest.json"
SETTINGS_PATH = APPDATA_DIR / "manager_settings.json"
DEFAULT_CONFIG_NAME = "config.ini"
INSTALLED_EXE_NAME = "EVDownloader_NativeHost_Manager.exe"


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def current_program_path() -> Path:
    return Path(sys.executable).resolve() if is_frozen() else Path(__file__).resolve()


def installed_exe_path() -> Path:
    return APPDATA_DIR / INSTALLED_EXE_NAME


def load_settings():
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(data):
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_runtime_files():
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    cfg = APPDATA_DIR / DEFAULT_CONFIG_NAME
    if not cfg.exists():
        src = bundle_dir() / DEFAULT_CONFIG_NAME
        if src.exists():
            shutil.copy2(src, cfg)
        else:
            cfg.write_text(
                "[FFMPEG]\nffmpeg = ffmpeg.exe\nffprobe = ffprobe.exe\nffplay = ffplay.exe\ndll_dir =\n\n"
                "[OUTPUT]\ndirectory = %USERPROFILE%\\Videos\\MKV\noverwrite = true\n\n"
                "[CONVERSION]\nvideo_crf = 22\nvideo_preset = medium\naudio_bitrate = 192k\n\n"
                "[NETWORK]\nuser_agent = Mozilla/5.0\nreconnect = true\n\n"
                "[LOG]\nfile = videomkv_host.log\n",
                encoding="utf-8",
            )
    return cfg


def valid_extension_id(ext_id: str) -> bool:
    ext_id = ext_id.strip().lower()
    return len(ext_id) == 32 and all("a" <= c <= "p" for c in ext_id)


def detect_chrome_extension_ids():
    """Busca instalaciones desempaquetadas/instaladas cuyo manifest coincida con EVDownloader."""
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    user_data = local / "Google" / "Chrome" / "User Data"
    found = []
    if not user_data.exists():
        return found

    profiles = [user_data / "Default"] + list(user_data.glob("Profile *"))
    for profile in profiles:
        ext_root = profile / "Extensions"
        if not ext_root.exists():
            continue
        for ext_dir in ext_root.iterdir():
            if not ext_dir.is_dir() or not valid_extension_id(ext_dir.name):
                continue
            versions = sorted((p for p in ext_dir.iterdir() if p.is_dir()), reverse=True)
            for ver in versions[:2]:
                mf = ver / "manifest.json"
                try:
                    data = json.loads(mf.read_text(encoding="utf-8"))
                    name = str(data.get("name", ""))
                    if "Video MKV Downloader" in name or "EVDownloader" in name:
                        found.append((ext_dir.name, profile.name, name))
                        break
                except Exception:
                    pass
    # únicos por ID
    seen = set(); out = []
    for row in found:
        if row[0] not in seen:
            seen.add(row[0]); out.append(row)
    return out


def registry_status():
    if os.name != "nt":
        return False, "Registro disponible sólo en Windows."
    try:
        import winreg
        key = rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            value, _ = winreg.QueryValueEx(k, "")
        return Path(value).exists(), value
    except FileNotFoundError:
        return False, "No registrado"
    except Exception as e:
        return False, str(e)


def write_registry(manifest_path: Path):
    import winreg
    key = rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, str(manifest_path))


def delete_registry():
    import winreg
    key = rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}"
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
    except FileNotFoundError:
        pass


def install_host(ext_id: str):
    if os.name != "nt":
        raise RuntimeError("La instalación del Native Host requiere Windows.")
    ext_id = ext_id.strip().lower()
    if not valid_extension_id(ext_id):
        raise ValueError("El ID de extensión debe tener 32 caracteres entre a-p.")

    ensure_runtime_files()
    if is_frozen():
        target = installed_exe_path()
        source = current_program_path()
        # No copiar sobre sí mismo.
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        host_path = target
    else:
        # Modo desarrollo: crear lanzador BAT estable.
        launcher = APPDATA_DIR / "native_host_dev.bat"
        launcher.write_text(
            '@echo off\r\n'
            f'set "EV_NATIVE_HOST_BASE={APPDATA_DIR}"\r\n'
            f'"{sys.executable}" "{Path(__file__).resolve()}" --native-host\r\n',
            encoding="utf-8",
        )
        host_path = launcher

    manifest = {
        "name": HOST_NAME,
        "description": DESCRIPTION,
        "path": str(host_path),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{ext_id}/"],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    write_registry(MANIFEST_PATH)
    save_settings({"extension_id": ext_id})
    return host_path


def uninstall_host(remove_files=False):
    if os.name != "nt":
        raise RuntimeError("La desinstalación del Native Host requiere Windows.")
    delete_registry()
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink(missing_ok=True)
    (APPDATA_DIR / "native_host_dev.bat").unlink(missing_ok=True)
    if remove_files:
        target = installed_exe_path()
        # Si se está ejecutando desde el EXE instalado, no puede borrarse en caliente.
        if target.exists() and current_program_path().resolve() != target.resolve():
            target.unlink(missing_ok=True)


def hide_console_window():
    if os.name == "nt" and is_frozen():
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception:
            pass


def native_host_mode_requested():
    if "--native-host" in sys.argv or "--native-host-test" in sys.argv:
        return True
    # Chrome/Chromium pasa el origin de la extensión como primer argumento.
    return any(str(a).startswith(("chrome-extension://", "extension://")) for a in sys.argv[1:])


def run_native_host():
    ensure_runtime_files()
    os.environ["EV_NATIVE_HOST_BASE"] = str(APPDATA_DIR)
    # Importación perezosa: BASE se calcula después de fijar EV_NATIVE_HOST_BASE.
    import host_runtime
    host_runtime.main()


def send_native_message(proc, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    proc.stdin.write(struct.pack("<I", len(data)))
    proc.stdin.write(data)
    proc.stdin.flush()


def read_exact(stream, n):
    buf = b""
    while len(buf) < n:
        chunk = stream.read(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def read_native_message(proc):
    raw = read_exact(proc.stdout, 4)
    if not raw:
        raise RuntimeError("El host no devolvió respuesta.")
    length = struct.unpack("<I", raw)[0]
    body = read_exact(proc.stdout, length)
    if body is None:
        raise RuntimeError("Respuesta incompleta del host.")
    return json.loads(body.decode("utf-8"))


def self_test_host(timeout=10):
    ensure_runtime_files()
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    env = os.environ.copy(); env["EV_NATIVE_HOST_BASE"] = str(APPDATA_DIR)
    if is_frozen():
        cmd = [str(current_program_path()), "--native-host-test"]
    else:
        cmd = [sys.executable, str(Path(__file__).resolve()), "--native-host-test"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=env, creationflags=creationflags)
    try:
        send_native_message(proc, {"command": "ping", "request_id": "manager-test"})
        result_box = {}
        error_box = {}
        def reader():
            try: result_box["value"] = read_native_message(proc)
            except Exception as e: error_box["error"] = e
        t = threading.Thread(target=reader, daemon=True); t.start(); t.join(timeout)
        if t.is_alive():
            raise TimeoutError("El host no respondió dentro del tiempo esperado.")
        if "error" in error_box:
            raise error_box["error"]
        return result_box["value"]
    finally:
        try: proc.terminate()
        except Exception: pass


class ManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("900x610")
        self.minsize(820, 560)
        self.configure(bg="#111318")
        self._setup_style()
        self._build_ui()
        self.after(150, self.refresh_status)
        self.after(250, self.auto_detect_extension)

    def _setup_style(self):
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except Exception: pass
        style.configure("TFrame", background="#111318")
        style.configure("Card.TFrame", background="#1b1f27")
        style.configure("TLabel", background="#111318", foreground="#e9edf5", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#111318", foreground="#ffffff", font=("Segoe UI Semibold", 23))
        style.configure("Sub.TLabel", background="#111318", foreground="#9aa4b2", font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background="#1b1f27", foreground="#ffffff", font=("Segoe UI Semibold", 11))
        style.configure("CardText.TLabel", background="#1b1f27", foreground="#b8c0cc", font=("Segoe UI", 9))
        style.configure("TEntry", fieldbackground="#252a34", foreground="#ffffff", insertcolor="#ffffff")
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=(14, 10))
        style.configure("Primary.TButton", font=("Segoe UI Semibold", 11), padding=(18, 13))
        style.configure("Danger.TButton", font=("Segoe UI Semibold", 11), padding=(18, 13))

    def _build_ui(self):
        header = ttk.Frame(self); header.pack(fill="x", padx=26, pady=(24, 12))
        ttk.Label(header, text="EVDownloader PRO", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Administrador integral del Native Messaging Host para Google Chrome", style="Sub.TLabel").pack(anchor="w", pady=(3, 0))

        card = ttk.Frame(self, style="Card.TFrame", padding=20); card.pack(fill="x", padx=26, pady=10)
        ttk.Label(card, text="Extensión de Chrome", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(card, text="ID de la extensión (chrome://extensions)", style="CardText.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 8))
        self.ext_var = tk.StringVar(value=load_settings().get("extension_id", ""))
        self.ext_entry = ttk.Entry(card, textvariable=self.ext_var, font=("Consolas", 11))
        self.ext_entry.grid(row=2, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(card, text="Detectar", command=self.auto_detect_extension).grid(row=2, column=1, padx=(0, 8))
        ttk.Button(card, text="Abrir chrome://extensions", command=self.open_extensions).grid(row=2, column=2)
        card.columnconfigure(0, weight=1)

        status = ttk.Frame(self, style="Card.TFrame", padding=20); status.pack(fill="x", padx=26, pady=10)
        ttk.Label(status, text="Estado del Native Host", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.status_var = tk.StringVar(value="Comprobando...")
        self.path_var = tk.StringVar(value="")
        ttk.Label(status, textvariable=self.status_var, style="CardText.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 2))
        ttk.Label(status, textvariable=self.path_var, style="CardText.TLabel", wraplength=780).grid(row=2, column=0, sticky="w")

        actions = ttk.Frame(self); actions.pack(fill="x", padx=26, pady=(10, 8))
        ttk.Button(actions, text="▶  INICIAR / PROBAR", style="Primary.TButton", command=self.action_test).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ttk.Button(actions, text="⬇  INSTALAR", style="Primary.TButton", command=self.action_install).pack(side="left", expand=True, fill="x", padx=6)
        ttk.Button(actions, text="✖  DESINSTALAR", style="Danger.TButton", command=self.action_uninstall).pack(side="left", expand=True, fill="x", padx=(6, 0))

        logcard = ttk.Frame(self, style="Card.TFrame", padding=16); logcard.pack(fill="both", expand=True, padx=26, pady=(6, 22))
        top = ttk.Frame(logcard, style="Card.TFrame"); top.pack(fill="x")
        ttk.Label(top, text="Registro", style="CardTitle.TLabel").pack(side="left")
        ttk.Button(top, text="Limpiar", command=lambda: self.log.delete("1.0", "end")).pack(side="right")
        self.log = tk.Text(logcard, height=11, bg="#0d0f13", fg="#cfd6e4", insertbackground="white",
                           relief="flat", font=("Consolas", 9), padx=10, pady=10, wrap="word")
        self.log.pack(fill="both", expand=True, pady=(10, 0))
        self._log("Administrador listo.")

    def _log(self, text):
        stamp = time.strftime("%H:%M:%S")
        self.log.insert("end", f"[{stamp}] {text}\n")
        self.log.see("end")

    def refresh_status(self):
        ok, detail = registry_status()
        if ok:
            self.status_var.set("● INSTALADO Y REGISTRADO")
            self.path_var.set(f"Manifiesto: {detail}")
        else:
            self.status_var.set("○ NO INSTALADO")
            self.path_var.set(str(detail))

    def auto_detect_extension(self):
        rows = detect_chrome_extension_ids()
        if rows:
            self.ext_var.set(rows[0][0])
            self._log(f"Extensión detectada: {rows[0][0]} ({rows[0][1]})")
        elif not self.ext_var.get().strip():
            self._log("No pude detectar automáticamente la extensión. Copia su ID desde chrome://extensions.")

    def open_extensions(self):
        try:
            os.startfile("chrome://extensions")
        except Exception:
            try: subprocess.Popen(["cmd", "/c", "start", "", "chrome://extensions"], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except Exception as e: messagebox.showerror(APP_NAME, str(e))

    def action_test(self):
        def worker():
            self._log("Iniciando prueba de comunicación Native Messaging...")
            try:
                result = self_test_host()
                ffmpeg_ok = result.get("ffmpeg_ok", False)
                self._log(f"Host respondió correctamente. FFmpeg: {'OK' if ffmpeg_ok else 'NO DISPONIBLE'}")
                self._log(f"Salida: {result.get('output_dir', '')}")
                self.after(0, lambda: messagebox.showinfo(APP_NAME, "Native Host funcionando correctamente.\n\n" + ("FFmpeg detectado." if ffmpeg_ok else "El host funciona, pero revisa la ruta de FFmpeg en config.ini.")))
            except Exception as e:
                self._log(f"ERROR de prueba: {e}")
                self.after(0, lambda: messagebox.showerror(APP_NAME, f"La prueba falló:\n\n{e}"))
        threading.Thread(target=worker, daemon=True).start()

    def action_install(self):
        ext = self.ext_var.get().strip()
        try:
            host_path = install_host(ext)
            self._log(f"Native Host instalado: {host_path}")
            self._log(f"Registro creado para {HOST_NAME}")
            self.refresh_status()
            messagebox.showinfo(APP_NAME, "Instalación completada.\n\nCierra completamente Google Chrome y vuelve a abrirlo para que cargue el Native Host.")
        except Exception as e:
            self._log(f"ERROR de instalación: {e}")
            messagebox.showerror(APP_NAME, str(e))

    def action_uninstall(self):
        if not messagebox.askyesno(APP_NAME, "¿Deseas desregistrar el Native Host de Chrome?"):
            return
        try:
            uninstall_host(remove_files=False)
            self._log("Native Host desinstalado del registro de Chrome.")
            self.refresh_status()
            messagebox.showinfo(APP_NAME, "Native Host desinstalado correctamente.")
        except Exception as e:
            self._log(f"ERROR de desinstalación: {e}")
            messagebox.showerror(APP_NAME, str(e))


def main_gui():
    hide_console_window()
    ensure_runtime_files()
    app = ManagerApp()
    app.mainloop()


if __name__ == "__main__":
    if native_host_mode_requested():
        run_native_host()
    else:
        main_gui()
