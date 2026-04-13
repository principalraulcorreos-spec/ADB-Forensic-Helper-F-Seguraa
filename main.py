"""
ADB Forensic Helper
-------------------
Herramienta de asistencia forense para detectar dispositivos Android,
verificar drivers USB e instruir la activación de Depuración USB.
"""

import os
import sys
import threading
import logging
import time
import winsound
import webbrowser
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.adb_manager import ADBManager, ADBStatus, DeviceInfo
from core.usb_monitor import USBMonitor, get_connected_usb_devices
from core.driver_manager import DriverManager
from core.device_database import get_manufacturer_from_vid, get_profile, get_instructions_for_android_version
from core.history_manager import HistoryManager
from core.update_checker import check_for_updates, CURRENT_VERSION
from core.avilla_compat import check_avilla_compatibility

# ─────────────────────────────────────────────
#  Logging (consola + archivo)
# ─────────────────────────────────────────────
LOG_DIR = Path(ROOT) / "logs"
LOG_DIR.mkdir(exist_ok=True)
_log_file = LOG_DIR / time.strftime("session_%Y-%m-%d.txt")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")

# ─────────────────────────────────────────────
#  Temas
# ─────────────────────────────────────────────
DARK_THEME = {
    "bg":        "#1a1d23",
    "bg2":       "#22262f",
    "bg3":       "#2c313c",
    "accent":    "#00b4d8",
    "accent2":   "#0077b6",
    "success":   "#2ecc71",
    "warning":   "#f39c12",
    "error":     "#e74c3c",
    "text":      "#e0e6f0",
    "text_dim":  "#8892a4",
    "border":    "#3a3f4b",
    "highlight": "#00b4d820",
    "tree_bg":   "#22262f",
    "tree_fg":   "#e0e6f0",
    "select":    "#0077b6",
}
LIGHT_THEME = {
    "bg":        "#f0f2f5",
    "bg2":       "#ffffff",
    "bg3":       "#e2e6ea",
    "accent":    "#0077b6",
    "accent2":   "#005f8e",
    "success":   "#27ae60",
    "warning":   "#e67e22",
    "error":     "#c0392b",
    "text":      "#1a1d23",
    "text_dim":  "#5a6475",
    "border":    "#c8cdd6",
    "highlight": "#0077b620",
    "tree_bg":   "#ffffff",
    "tree_fg":   "#1a1d23",
    "select":    "#0077b6",
}

C = dict(DARK_THEME)

FONT_MONO  = ("Consolas", 10)
FONT_UI    = ("Segoe UI", 10)
FONT_UI_B  = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_SMALL = ("Segoe UI", 9)


# ─────────────────────────────────────────────
#  Ventana principal
# ─────────────────────────────────────────────

class ForensicADBHelper(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(f"ADB Forensic Helper  v{CURRENT_VERSION}  —  Asistente de Conexión Forense")
        self.geometry("920x780")
        self.minsize(800, 620)
        self.configure(bg=C["bg"])
        self.resizable(True, True)

        self.adb            = ADBManager()
        self.driver_mgr     = DriverManager()
        self.history_mgr    = HistoryManager(ROOT)
        self.usb_monitor    = USBMonitor(
            on_connect=self._on_usb_connect,
            on_disconnect=self._on_usb_disconnect,
        )

        self._current_device: Optional[DeviceInfo] = None
        self._detected_manufacturer: str = "Generic"
        self._retry_active   = False
        self._retry_thread: Optional[threading.Thread] = None
        self._theme          = "dark"
        self._all_devices: list[tuple[str, str]] = []   # [(serial, estado), ...]
        self._selected_serial: str = ""

        self._build_ui()
        self._apply_styles()
        self.usb_monitor.start()
        self.after(500, self._full_check)
        self.after(3000, self._start_update_check)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────────────
    #  UI principal
    # ─────────────────────────────────────────

    def _build_ui(self):
        # ── Header ──────────────────────────
        header = tk.Frame(self, bg=C["bg2"], pady=10)
        header.pack(fill="x")

        tk.Label(
            header, text="ADB Forensic Helper",
            font=FONT_TITLE, bg=C["bg2"], fg=C["accent"]
        ).pack(side="left", padx=18)

        tk.Label(
            header, text=f"v{CURRENT_VERSION}  —  Avilla Forensics",
            font=FONT_SMALL, bg=C["bg2"], fg=C["text_dim"]
        ).pack(side="left", padx=4)

        # Botón tema
        self.btn_theme = tk.Button(
            header, text="☀ Claro",
            font=FONT_SMALL,
            bg=C["bg3"], fg=C["text_dim"],
            relief="flat", padx=10, pady=4,
            cursor="hand2",
            command=self._toggle_theme,
        )
        self.btn_theme.pack(side="right", padx=8)

        self.lbl_adb_ver = tk.Label(
            header, text="ADB: verificando...",
            font=FONT_SMALL, bg=C["bg2"], fg=C["text_dim"]
        )
        self.lbl_adb_ver.pack(side="right", padx=18)

        # Banner de actualización (oculto por defecto)
        self.update_banner = tk.Frame(self, bg="#f39c12")
        self.lbl_update = tk.Label(
            self.update_banner,
            text="",
            font=FONT_SMALL, bg="#f39c12", fg="white",
            cursor="hand2",
        )
        self.lbl_update.pack(side="left", padx=12, pady=4)
        self.lbl_update.bind("<Button-1>", self._open_releases)

        tk.Button(
            self.update_banner, text="✕",
            font=FONT_SMALL, bg="#f39c12", fg="white",
            relief="flat", cursor="hand2",
            command=lambda: self.update_banner.pack_forget()
        ).pack(side="right", padx=8)

        # ── Estado del dispositivo ───────────
        status_frame = tk.Frame(self, bg=C["bg3"], pady=12, padx=18)
        status_frame.pack(fill="x", padx=10, pady=(8, 0))

        self.canvas_indicator = tk.Canvas(
            status_frame, width=24, height=24,
            bg=C["bg3"], highlightthickness=0
        )
        self.canvas_indicator.pack(side="left", padx=(0, 12))
        self._indicator_oval = self.canvas_indicator.create_oval(
            2, 2, 22, 22, fill=C["text_dim"], outline=""
        )

        info_col = tk.Frame(status_frame, bg=C["bg3"])
        info_col.pack(side="left", fill="x", expand=True)

        self.lbl_status = tk.Label(
            info_col, text="Esperando dispositivo...",
            font=FONT_UI_B, bg=C["bg3"], fg=C["text"]
        )
        self.lbl_status.pack(anchor="w")

        self.lbl_device = tk.Label(
            info_col, text="Conecta un dispositivo Android por USB",
            font=FONT_UI, bg=C["bg3"], fg=C["text_dim"]
        )
        self.lbl_device.pack(anchor="w")

        # Selector de dispositivo (múltiples)
        self.device_selector_frame = tk.Frame(status_frame, bg=C["bg3"])
        self.device_selector_frame.pack(side="left", padx=(16, 0))

        self.lbl_select = tk.Label(
            self.device_selector_frame, text="Dispositivo:",
            font=FONT_SMALL, bg=C["bg3"], fg=C["text_dim"]
        )
        self.cmb_devices = ttk.Combobox(
            self.device_selector_frame,
            state="readonly", width=22, font=FONT_SMALL
        )
        self.cmb_devices.bind("<<ComboboxSelected>>", self._on_device_selected)

        self.btn_retry = tk.Button(
            status_frame,
            text="Reintentar",
            font=FONT_UI_B,
            bg=C["accent2"], fg="white",
            activebackground=C["accent"], activeforeground="white",
            relief="flat", padx=14, pady=6,
            cursor="hand2",
            command=self._full_check,
        )
        self.btn_retry.pack(side="right", padx=(10, 0))

        # ── Info del dispositivo ─────────────
        self.device_info_frame = tk.Frame(self, bg=C["bg"], padx=10, pady=4)
        self.device_info_frame.pack(fill="x")

        self._info_labels: dict[str, tk.Label] = {}
        fields = [
            ("Fabricante", "manufacturer"),
            ("Modelo",     "model"),
            ("Android",    "android_version"),
            ("Build ID",   "build_id"),
            ("Serial",     "serial"),
        ]

        row_frame = tk.Frame(self.device_info_frame, bg=C["bg"])
        row_frame.pack(fill="x")

        for i, (label, key) in enumerate(fields):
            col = tk.Frame(row_frame, bg=C["bg2"], padx=10, pady=6)
            col.grid(row=0, column=i, padx=4, pady=4, sticky="ew")
            row_frame.columnconfigure(i, weight=1)
            tk.Label(col, text=label, font=FONT_SMALL,
                     bg=C["bg2"], fg=C["text_dim"]).pack(anchor="w")
            val_lbl = tk.Label(col, text="—", font=FONT_UI_B,
                               bg=C["bg2"], fg=C["text"])
            val_lbl.pack(anchor="w")
            self._info_labels[key] = val_lbl

        # ── Compatibilidad Avilla (segunda fila, siempre visible) ──
        avilla_row = tk.Frame(self.device_info_frame, bg=C["bg"], padx=4, pady=2)
        avilla_row.pack(fill="x")

        avilla_card = tk.Frame(avilla_row, bg=C["bg3"], padx=12, pady=8)
        avilla_card.pack(fill="x")

        tk.Label(avilla_card, text="Compatibilidad Avilla Forensics:",
                 font=FONT_UI_B, bg=C["bg3"], fg=C["text_dim"]).pack(side="left")

        self.lbl_avilla_level = tk.Label(
            avilla_card, text="—",
            font=FONT_UI_B, bg=C["bg3"], fg=C["text_dim"]
        )
        self.lbl_avilla_level.pack(side="left", padx=(8, 16))

        self.lbl_avilla_note = tk.Label(
            avilla_card, text="Conecta un dispositivo para verificar.",
            font=FONT_SMALL, bg=C["bg3"], fg=C["text_dim"],
            wraplength=700, justify="left"
        )
        self.lbl_avilla_note.pack(side="left", fill="x", expand=True)

        # ── Separador ───────────────────────
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x", padx=10, pady=6)

        # ── Pestañas ────────────────────────
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self.tab_instructions = tk.Frame(self.notebook, bg=C["bg"])
        self.tab_driver       = tk.Frame(self.notebook, bg=C["bg"])
        self.tab_history      = tk.Frame(self.notebook, bg=C["bg"])
        self.tab_log          = tk.Frame(self.notebook, bg=C["bg"])

        self.notebook.add(self.tab_instructions, text="  Instrucciones  ")
        self.notebook.add(self.tab_driver,       text="  Driver USB  ")
        self.notebook.add(self.tab_history,      text="  Historial  ")
        self.notebook.add(self.tab_log,          text="  Log ADB  ")

        self._build_tab_instructions()
        self._build_tab_driver()
        self._build_tab_history()
        self._build_tab_log()

        # ── Footer ──────────────────────────
        footer = tk.Frame(self, bg=C["bg2"], pady=6)
        footer.pack(fill="x", side="bottom")

        self.lbl_footer = tk.Label(
            footer, text="Listo. Conecta el dispositivo por USB.",
            font=FONT_SMALL, bg=C["bg2"], fg=C["text_dim"]
        )
        self.lbl_footer.pack(side="left", padx=12)

        self.lbl_retry_counter = tk.Label(
            footer, text="", font=FONT_SMALL, bg=C["bg2"], fg=C["warning"]
        )
        self.lbl_retry_counter.pack(side="right", padx=12)

    def _build_tab_instructions(self):
        tk.Label(
            self.tab_instructions,
            text="Pasos para activar Depuración USB en el dispositivo:",
            font=FONT_UI_B, bg=C["bg"], fg=C["accent"]
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.txt_instructions = scrolledtext.ScrolledText(
            self.tab_instructions,
            font=FONT_MONO, bg=C["bg2"], fg=C["text"],
            insertbackground=C["text"],
            relief="flat", borderwidth=0,
            wrap="word", state="disabled",
            padx=12, pady=10,
        )
        self.txt_instructions.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        note_frame = tk.Frame(self.tab_instructions, bg=C["bg3"], padx=12, pady=8)
        note_frame.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(note_frame, text="Nota forense:", font=FONT_UI_B,
                 bg=C["bg3"], fg=C["warning"]).pack(anchor="w")
        self.lbl_forensic_note = tk.Label(
            note_frame,
            text="Conecta el dispositivo para ver instrucciones específicas.",
            font=FONT_SMALL, bg=C["bg3"], fg=C["text_dim"],
            wraplength=820, justify="left"
        )
        self.lbl_forensic_note.pack(anchor="w")

    def _build_tab_driver(self):
        tk.Label(
            self.tab_driver,
            text="Estado del driver USB:",
            font=FONT_UI_B, bg=C["bg"], fg=C["accent"]
        ).pack(anchor="w", padx=12, pady=(10, 4))

        driver_status_frame = tk.Frame(self.tab_driver, bg=C["bg2"], padx=12, pady=10)
        driver_status_frame.pack(fill="x", padx=10, pady=4)

        self.lbl_driver_status = tk.Label(
            driver_status_frame,
            text="Esperando dispositivo para verificar driver...",
            font=FONT_UI, bg=C["bg2"], fg=C["text_dim"]
        )
        self.lbl_driver_status.pack(anchor="w")

        self.lbl_driver_name = tk.Label(
            driver_status_frame, text="",
            font=FONT_SMALL, bg=C["bg2"], fg=C["text_dim"]
        )
        self.lbl_driver_name.pack(anchor="w")

        btn_frame = tk.Frame(self.tab_driver, bg=C["bg"], pady=8)
        btn_frame.pack(fill="x", padx=10)

        self.btn_install_driver = tk.Button(
            btn_frame,
            text="Descargar e instalar driver automáticamente",
            font=FONT_UI_B,
            bg=C["accent2"], fg="white",
            activebackground=C["accent"], activeforeground="white",
            relief="flat", padx=14, pady=8,
            cursor="hand2",
            command=self._auto_install_driver,
        )
        self.btn_install_driver.pack(side="left")

        tk.Label(
            btn_frame,
            text="  (requiere administrador)",
            font=FONT_SMALL, bg=C["bg"], fg=C["text_dim"]
        ).pack(side="left")

        self.driver_progress_frame = tk.Frame(self.tab_driver, bg=C["bg"])
        self.driver_progress_frame.pack(fill="x", padx=10, pady=(0, 4))

        self.lbl_driver_progress = tk.Label(
            self.driver_progress_frame, text="",
            font=FONT_SMALL, bg=C["bg"], fg=C["text_dim"]
        )
        self.lbl_driver_progress.pack(anchor="w")

        self.driver_progressbar = ttk.Progressbar(
            self.driver_progress_frame,
            mode="determinate", length=400
        )

        tk.Label(
            self.tab_driver,
            text="Información del driver:",
            font=FONT_UI_B, bg=C["bg"], fg=C["text"]
        ).pack(anchor="w", padx=12, pady=(6, 4))

        self.txt_driver = scrolledtext.ScrolledText(
            self.tab_driver,
            font=FONT_MONO, bg=C["bg2"], fg=C["text"],
            relief="flat", borderwidth=0,
            wrap="word", state="disabled",
            padx=12, pady=10, height=10,
        )
        self.txt_driver.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _build_tab_history(self):
        header = tk.Frame(self.tab_history, bg=C["bg"])
        header.pack(fill="x", padx=10, pady=(10, 4))

        tk.Label(
            header, text="Dispositivos procesados:",
            font=FONT_UI_B, bg=C["bg"], fg=C["accent"]
        ).pack(side="left")

        tk.Button(
            header, text="Limpiar historial",
            font=FONT_SMALL, bg=C["bg3"], fg=C["text_dim"],
            relief="flat", padx=8, pady=3, cursor="hand2",
            command=self._clear_history,
        ).pack(side="right")

        # Tabla
        cols = ("Fecha", "Fabricante", "Modelo", "Android", "Serial")
        self.history_tree = ttk.Treeview(
            self.tab_history,
            columns=cols, show="headings",
            selectmode="browse",
        )
        for col in cols:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=140, minwidth=80)
        self.history_tree.column("Fecha", width=150)
        self.history_tree.column("Serial", width=180)

        scrollbar = ttk.Scrollbar(self.tab_history, orient="vertical",
                                  command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=(0, 10))

        self._refresh_history()

    def _build_tab_log(self):
        header = tk.Frame(self.tab_log, bg=C["bg"])
        header.pack(fill="x", padx=10, pady=(8, 4))

        tk.Label(
            header, text="Registro ADB en tiempo real:",
            font=FONT_UI_B, bg=C["bg"], fg=C["accent"]
        ).pack(side="left")

        tk.Label(
            header, text=f"  Guardado en: logs/",
            font=FONT_SMALL, bg=C["bg"], fg=C["text_dim"]
        ).pack(side="left")

        tk.Button(
            header, text="Limpiar",
            font=FONT_SMALL, bg=C["bg3"], fg=C["text_dim"],
            relief="flat", padx=8, pady=3, cursor="hand2",
            command=self._clear_log,
        ).pack(side="right")

        self.txt_log = scrolledtext.ScrolledText(
            self.tab_log,
            font=FONT_MONO, bg=C["bg2"], fg=C["text"],
            relief="flat", borderwidth=0,
            wrap="none", state="disabled",
            padx=10, pady=8,
        )
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.txt_log.tag_config("INFO",    foreground=C["text"])
        self.txt_log.tag_config("OK",      foreground=C["success"])
        self.txt_log.tag_config("WARN",    foreground=C["warning"])
        self.txt_log.tag_config("ERROR",   foreground=C["error"])
        self.txt_log.tag_config("SECTION", foreground=C["accent"])

    # ─────────────────────────────────────────
    #  Estilos ttk
    # ─────────────────────────────────────────

    def _apply_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=C["bg"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=C["bg3"], foreground=C["text_dim"],
            padding=[10, 5], font=FONT_UI,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", C["bg2"])],
            foreground=[("selected", C["accent"])],
        )
        style.configure(
            "Treeview",
            background=C["tree_bg"], foreground=C["tree_fg"],
            fieldbackground=C["tree_bg"], rowheight=24,
            font=FONT_UI,
        )
        style.configure("Treeview.Heading", font=FONT_UI_B,
                        background=C["bg3"], foreground=C["text"])
        style.map("Treeview", background=[("selected", C["select"])])

    # ─────────────────────────────────────────
    #  Tema claro / oscuro
    # ─────────────────────────────────────────

    def _toggle_theme(self):
        old_theme = DARK_THEME if self._theme == "dark" else LIGHT_THEME
        self._theme = "light" if self._theme == "dark" else "dark"
        new_theme = LIGHT_THEME if self._theme == "light" else DARK_THEME
        C.update(new_theme)
        self.btn_theme.config(
            text="🌙 Oscuro" if self._theme == "light" else "☀ Claro"
        )
        self._apply_styles()
        self._recolor_all_widgets(old_theme, new_theme)

    def _recolor_all_widgets(self, old_theme: dict, new_theme: dict):
        """Recorre todos los widgets y reemplaza colores del tema anterior por los nuevos."""
        # Mapa de color_viejo → color_nuevo (en minúsculas)
        color_map = {
            old_theme[k].lower(): new_theme[k]
            for k in old_theme
            if old_theme[k].lower() != new_theme[k].lower()
        }

        def recolor(widget):
            for prop in ("bg", "fg", "background", "foreground",
                         "activebackground", "activeforeground",
                         "insertbackground", "highlightbackground"):
                try:
                    val = widget.cget(prop)
                    if isinstance(val, str) and val.lower() in color_map:
                        widget.configure(**{prop: color_map[val.lower()]})
                except Exception:
                    pass
            # Canvas: recolorear óvalos (indicador de estado)
            if isinstance(widget, tk.Canvas):
                try:
                    for item in widget.find_all():
                        fill = widget.itemcget(item, "fill")
                        if fill.lower() in color_map:
                            widget.itemconfig(item, fill=color_map[fill.lower()])
                except Exception:
                    pass
            for child in widget.winfo_children():
                recolor(child)

        recolor(self)

    # ─────────────────────────────────────────
    #  Selector de múltiples dispositivos
    # ─────────────────────────────────────────

    def _update_device_selector(self, devices: list[tuple[str, str]]):
        """Actualiza el combobox con la lista de dispositivos conectados."""
        self._all_devices = devices
        if len(devices) <= 1:
            self.lbl_select.pack_forget()
            self.cmb_devices.pack_forget()
            self._selected_serial = devices[0][0] if devices else ""
            return

        # Múltiples dispositivos: mostrar selector
        self.lbl_select.pack(anchor="w")
        self.cmb_devices.pack(anchor="w", pady=2)
        values = [f"{s}  ({st})" for s, st in devices]
        self.cmb_devices["values"] = values
        if not self._selected_serial:
            self.cmb_devices.current(0)
            self._selected_serial = devices[0][0]

    def _on_device_selected(self, event=None):
        idx = self.cmb_devices.current()
        if 0 <= idx < len(self._all_devices):
            self._selected_serial = self._all_devices[idx][0]
            self._full_check()

    # ─────────────────────────────────────────
    #  Lógica principal de detección
    # ─────────────────────────────────────────

    def _full_check(self):
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self):
        self._ui(self._set_status, "Verificando...", C["warning"], "checking")
        self._log("─── Iniciando verificación ───", "SECTION")

        # 1. Verificar ADB
        if not self.adb.is_available():
            self._log("adb.exe no encontrado. Descargando...", "WARN")
            self._ui(self._set_status, "Descargando ADB...", C["warning"], "checking")
            dest = self.driver_mgr.download_platform_tools(
                progress_callback=lambda p: self._log(f"Descargando... {p}%", "INFO")
            )
            if dest:
                self.adb = ADBManager(os.path.join(dest, "adb.exe"))
                self._log(f"ADB descargado en: {dest}", "OK")
            else:
                self._log("ERROR: No se pudo descargar ADB.", "ERROR")
                self._ui(self._set_status, "ADB no disponible", C["error"], "error")
                return

        adb_ver = self.adb.get_adb_version()
        self._log(f"ADB disponible: versión {adb_ver}", "OK")
        self._ui(lambda: self.lbl_adb_ver.config(text=f"ADB {adb_ver}", fg=C["success"]))

        self.adb.start_server()

        # 2. Listar todos los dispositivos
        all_devs = self.adb.list_devices()
        self._ui(self._update_device_selector, all_devs)

        # Seleccionar serial a usar
        serial = self._selected_serial
        if not serial and all_devs:
            serial = all_devs[0][0]
            self._selected_serial = serial

        status = self.adb.get_overall_status()
        self._log(f"Estado ADB: {status.value} | Dispositivos: {len(all_devs)}", "INFO")

        # 3. Detectar USB
        usb_devices = get_connected_usb_devices()
        android_usb = self._find_android_device_usb(usb_devices)
        vid = android_usb.get("vid", "") if android_usb else ""
        pid = android_usb.get("pid", "") if android_usb else ""
        manufacturer_from_usb = get_manufacturer_from_vid(vid) if vid else ""

        if vid and pid:
            self._detected_manufacturer = manufacturer_from_usb or "Generic"
            self._check_and_show_driver(vid, pid, manufacturer_from_usb)

        # 4. Procesar estado
        if status == ADBStatus.CONNECTED:
            device_info = self.adb.get_full_device_info(serial)
            self._current_device = device_info
            self._log(f"Dispositivo: {device_info.manufacturer} {device_info.model}", "OK")
            self._log(f"Android {device_info.android_version} | Serial: {device_info.serial}", "INFO")

            # Guardar en historial
            self.history_mgr.add_device(
                device_info.manufacturer, device_info.model,
                device_info.serial, device_info.android_version
            )
            self._ui(self._refresh_history)
            self._ui(self._show_device_ready, device_info)

        elif status == ADBStatus.UNAUTHORIZED:
            self._log("Dispositivo NO AUTORIZADO — acepta el aviso en pantalla.", "WARN")
            manufacturer = manufacturer_from_usb or "Generic"

            # Detectar si la pantalla puede estar bloqueada
            locked_hint = self._is_likely_locked(android_usb)
            self._ui(self._show_unauthorized, manufacturer, vid, android_usb, locked_hint)
            self._start_auto_retry()

        elif status == ADBStatus.NO_DEVICES:
            if android_usb:
                self._log(f"USB detectado (VID:{vid}) pero ADB no lo ve.", "WARN")
                manufacturer = manufacturer_from_usb or "Generic"
                self._ui(self._show_needs_setup, manufacturer, android_usb)
                self._start_auto_retry()
            else:
                self._log("Sin dispositivos Android detectados.", "INFO")
                self._ui(self._set_status, "Sin dispositivo conectado", C["text_dim"], "idle")
                self._ui(self._clear_device_info)
                self._ui(self._clear_avilla_info)

        elif status == ADBStatus.OFFLINE:
            self._log("Dispositivo offline. Puede estar reiniciando.", "WARN")
            self._ui(self._set_status, "Dispositivo offline — espera...", C["warning"], "checking")
            self._start_auto_retry()

        elif status == ADBStatus.NOT_FOUND:
            self._ui(self._set_status, "ADB no encontrado", C["error"], "error")

    def _is_likely_locked(self, usb_info: Optional[dict]) -> bool:
        """
        Intenta determinar si la pantalla está bloqueada.
        Sin acceso ADB shell en modo unauthorized, solo podemos inferirlo
        por el nombre del dispositivo USB (modo MTP vs ADB).
        """
        if not usb_info:
            return False
        name = (usb_info.get("name") or "").lower()
        # Si el dispositivo aparece como MTP/PTP en lugar de ADB, probablemente bloqueado
        return any(k in name for k in ["mtp", "ptp", "media transfer"])

    def _find_android_device_usb(self, usb_devices: list[dict]) -> Optional[dict]:
        from core.device_database import VENDOR_ID_MAP
        known_vids = set(VENDOR_ID_MAP.keys())

        for dev in usb_devices:
            if dev.get("vid", "").lower() in known_vids:
                return dev

        keywords = ["android", "mobile", "phone", "adb", "composite"]
        for dev in usb_devices:
            name = (dev.get("name") or "").lower()
            desc = (dev.get("description") or "").lower()
            if any(k in name or k in desc for k in keywords):
                return dev
        return None

    # ─────────────────────────────────────────
    #  Acciones de UI
    # ─────────────────────────────────────────

    def _show_device_ready(self, info: DeviceInfo):
        self._stop_auto_retry()
        self._set_status("LISTO para Avilla Forensics", C["success"], "ok")
        self.lbl_device.config(
            text=f"{info.manufacturer} {info.model}  —  Android {info.android_version}",
            fg=C["success"]
        )
        self._update_device_info(info)
        self._update_instructions(info.manufacturer, info.android_version_int)
        self.lbl_forensic_note.config(
            text="Dispositivo autorizado y listo. Puedes lanzar Avilla Forensics.",
            fg=C["success"]
        )
        self._update_avilla_compat(info.manufacturer, info.android_version_int)
        self._log("DISPOSITIVO LISTO para uso forense.", "OK")
        self.lbl_footer.config(
            text=f"Dispositivo listo: {info.manufacturer} {info.model}",
            fg=C["success"]
        )
        # Sonido de notificación
        threading.Thread(target=self._play_ready_sound, daemon=True).start()

    def _play_ready_sound(self):
        try:
            winsound.Beep(1000, 200)
            time.sleep(0.1)
            winsound.Beep(1200, 300)
        except Exception:
            pass

    def _show_unauthorized(self, manufacturer: str, vid: str,
                           usb_info: Optional[dict], locked: bool = False):
        self._set_status("Autorización pendiente en el teléfono", C["warning"], "warn")
        device_name = usb_info.get("name", "Dispositivo Android") if usb_info else "Dispositivo Android"

        if locked:
            status_text = f"{device_name}  —  Pantalla bloqueada o modo MTP activo"
            locked_lines = [
                "⚠ PANTALLA POSIBLEMENTE BLOQUEADA",
                "",
                "El dispositivo está en modo MTP/PTP, lo que indica que la pantalla",
                "puede estar bloqueada. Para continuar:",
                "",
                "  1. Desbloquea la pantalla del teléfono",
                "  2. Si aparece un aviso de 'Depuración USB', pulsa PERMITIR",
                "  3. Si no aparece, activa la Depuración USB manualmente:",
                "─────────────────────────────────────────────",
            ]
        else:
            status_text = f"{device_name}  —  Acepta el aviso de depuración USB en pantalla"
            locked_lines = [
                "*** ACCIÓN REQUERIDA ***",
                "",
                "El dispositivo está conectado pero espera tu autorización.",
                "En la pantalla del teléfono debería aparecer un aviso:",
                "",
                "  '¿Permitir la depuración USB?'",
                "  → Marca 'Permitir siempre desde este equipo'",
                "  → Pulsa ACEPTAR / PERMITIR",
                "",
                "Si el aviso no aparece, activa primero la Depuración USB:",
                "─────────────────────────────────────────────",
            ]

        self.lbl_device.config(text=status_text, fg=C["warning"])
        self._clear_device_info()
        self._update_instructions(manufacturer, 0, extra_top=locked_lines)
        self.lbl_footer.config(
            text="Esperando autorización en el dispositivo...", fg=C["warning"]
        )

    def _show_needs_setup(self, manufacturer: str, usb_info: Optional[dict]):
        self._set_status("Dispositivo detectado — ADB no activo", C["warning"], "warn")
        device_name = usb_info.get("name", "Dispositivo Android") if usb_info else "Dispositivo Android"
        self.lbl_device.config(
            text=f"{device_name}  —  Activa la Depuración USB siguiendo los pasos",
            fg=C["warning"]
        )
        self._clear_device_info()
        self._update_instructions(manufacturer, 0)
        self.lbl_footer.config(
            text="Sigue las instrucciones para activar ADB.", fg=C["warning"]
        )

    def _update_instructions(self, manufacturer: str, android_version: int,
                             extra_top: list[str] = None):
        profile = get_profile(manufacturer)
        steps = get_instructions_for_android_version(profile, android_version)
        lines = []
        if extra_top:
            lines.extend(extra_top)
        lines.append(f"Fabricante detectado: {profile.name}")
        lines.append("")
        lines.extend(steps)
        self._set_text(self.txt_instructions, "\n".join(lines))
        self.lbl_forensic_note.config(
            text=profile.forensic_note or "Sin notas adicionales.",
            fg=C["text_dim"]
        )

    def _update_avilla_compat(self, manufacturer: str, android_version_int: int):
        result = check_avilla_compatibility(manufacturer, android_version_int)
        self.lbl_avilla_level.config(
            text=f"Compatibilidad: {result['level']}",
            fg=result["color"]
        )
        self.lbl_avilla_note.config(
            text=result["note"],
            fg=C["text_dim"]
        )

    def _clear_avilla_info(self):
        self.lbl_avilla_level.config(text="—", fg=C["text_dim"])
        self.lbl_avilla_note.config(
            text="Conecta un dispositivo para verificar.",
            fg=C["text_dim"]
        )

    def _check_and_show_driver(self, vid: str, pid: str, manufacturer: str):
        profile = get_profile(manufacturer)
        driver_status = self.driver_mgr.get_driver_status(vid, pid)

        if driver_status["installed"]:
            msg   = f"Driver instalado correctamente: {driver_status['device_name']}"
            color = C["success"]
            self._log(f"Driver OK: {driver_status['device_name']}", "OK")
        else:
            msg   = f"Driver NO instalado para VID:{vid.upper()} PID:{pid.upper()}"
            color = C["error"]
            self._log(f"Driver no encontrado para VID:{vid} PID:{pid}", "WARN")

        def update():
            self.lbl_driver_status.config(text=msg, fg=color)
            self.lbl_driver_name.config(
                text=f"Driver recomendado: {profile.driver_name}",
                fg=C["text_dim"]
            )
            steps = self.driver_mgr.get_install_guidance(manufacturer)
            self._set_text(self.txt_driver, "\n".join(steps))

        self._ui(update)

    def _update_device_info(self, info: DeviceInfo):
        self._info_labels["manufacturer"].config(text=info.manufacturer, fg=C["text"])
        self._info_labels["model"].config(text=info.model, fg=C["text"])
        self._info_labels["android_version"].config(text=f"Android {info.android_version}", fg=C["text"])
        self._info_labels["build_id"].config(text=info.build_id, fg=C["text"])
        self._info_labels["serial"].config(text=info.serial, fg=C["text"])

    def _clear_device_info(self):
        for lbl in self._info_labels.values():
            lbl.config(text="—", fg=C["text_dim"])

    # ─────────────────────────────────────────
    #  Historial
    # ─────────────────────────────────────────

    def _refresh_history(self):
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        for entry in self.history_mgr.get_all():
            self.history_tree.insert("", "end", values=(
                entry.get("timestamp", ""),
                entry.get("manufacturer", ""),
                entry.get("model", ""),
                entry.get("android_version", ""),
                entry.get("serial", ""),
            ))

    def _clear_history(self):
        if messagebox.askyesno("Limpiar historial",
                               "¿Borrar todo el historial de dispositivos?"):
            self.history_mgr.clear()
            self._refresh_history()

    # ─────────────────────────────────────────
    #  Auto-reintento
    # ─────────────────────────────────────────

    def _start_auto_retry(self, interval: int = 5, max_retries: int = 60):
        if self._retry_active:
            return
        self._retry_active = True

        def retry_loop():
            count = 0
            while self._retry_active and count < max_retries:
                count += 1
                self._ui(
                    lambda c=count, m=max_retries:
                    self.lbl_retry_counter.config(
                        text=f"Reintento {c}/{m} — próximo en {interval}s"
                    )
                )
                time.sleep(interval)
                if not self._retry_active:
                    break
                status = self.adb.get_overall_status()
                if status == ADBStatus.CONNECTED:
                    self._retry_active = False
                    self._check_worker()
                    return
            self._retry_active = False
            self._ui(lambda: self.lbl_retry_counter.config(text=""))

        self._retry_thread = threading.Thread(target=retry_loop, daemon=True)
        self._retry_thread.start()

    def _stop_auto_retry(self):
        self._retry_active = False
        self._ui(lambda: self.lbl_retry_counter.config(text=""))

    # ─────────────────────────────────────────
    #  Eventos USB
    # ─────────────────────────────────────────

    def _on_usb_connect(self, device_info: dict):
        name = device_info.get("name", "Desconocido")
        vid  = device_info.get("vid", "")
        pid  = device_info.get("pid", "")
        self._log(f"USB conectado: {name} (VID:{vid} PID:{pid})", "INFO")

        from core.device_database import VENDOR_ID_MAP
        if vid.lower() in VENDOR_ID_MAP or "android" in name.lower():
            self._log("Dispositivo Android detectado. Verificando...", "INFO")
            self.after(1500, self._full_check)

    def _on_usb_disconnect(self, device_info: dict):
        name = device_info.get("name", "Desconocido")
        self._log(f"USB desconectado: {name}", "WARN")
        self._stop_auto_retry()
        self._selected_serial = ""
        self._current_device = None
        self._ui(self._set_status, "Dispositivo desconectado", C["text_dim"], "idle")
        self._ui(self._clear_device_info)
        self._ui(self._clear_avilla_info)
        self._ui(lambda: self.lbl_device.config(
            text="Conecta un dispositivo Android por USB", fg=C["text_dim"]
        ))
        self._ui(lambda: self.lbl_footer.config(
            text="Dispositivo desconectado.", fg=C["text_dim"]
        ))
        self._ui(lambda: self._update_device_selector([]))

    # ─────────────────────────────────────────
    #  Driver automático
    # ─────────────────────────────────────────

    def _auto_install_driver(self):
        if not self.driver_mgr.is_admin():
            messagebox.showwarning(
                "Privilegios insuficientes",
                "La instalación de drivers requiere ejecutar como Administrador.\n\n"
                "Cierra y vuelve a abrir el programa con el .bat (ya pide admin automáticamente)."
            )
            return
        threading.Thread(target=self._auto_install_driver_worker, daemon=True).start()

    def _auto_install_driver_worker(self):
        manufacturer = (
            self._current_device.manufacturer
            if self._current_device else self._detected_manufacturer
        )

        self._log(f"Buscando driver para: {manufacturer}", "INFO")
        self._ui(lambda: self.btn_install_driver.config(
            text="Instalando...", state="disabled"
        ))
        self._ui(lambda: self.driver_progressbar.pack(fill="x", pady=4))

        def on_progress(pct, msg=""):
            self._ui(lambda p=pct, m=msg: [
                self.driver_progressbar.config(value=p),
                self.lbl_driver_progress.config(text=m),
            ])

        success, msg = self.driver_mgr.auto_install_driver(
            manufacturer, progress_callback=on_progress
        )

        self._log(msg, "OK" if success else "ERROR")
        self._ui(lambda: [
            self.btn_install_driver.config(
                text="Descargar e instalar driver automáticamente", state="normal"
            ),
            self.driver_progressbar.pack_forget(),
            self.lbl_driver_progress.config(text=""),
        ])

        if success:
            self._ui(lambda: messagebox.showinfo("Driver instalado", msg))
            self._full_check()
        else:
            self._ui(lambda: messagebox.showerror("Error de instalación", msg))

    # ─────────────────────────────────────────
    #  Verificador de actualizaciones
    # ─────────────────────────────────────────

    def _start_update_check(self):
        threading.Thread(target=self._check_updates_worker, daemon=True).start()

    def _check_updates_worker(self):
        has_update, latest_ver, url = check_for_updates()
        if has_update:
            self._ui(self._show_update_banner, latest_ver, url)

    def _show_update_banner(self, version: str, url: str):
        self._update_url = url
        self.lbl_update.config(
            text=f"  Nueva versión disponible: v{version}  —  Clic aquí para descargar"
        )
        self.update_banner.pack(fill="x", after=self.nametowidget(self.winfo_children()[0]))

    def _open_releases(self, event=None):
        webbrowser.open(getattr(self, "_update_url", ""))

    # ─────────────────────────────────────────
    #  Helpers de UI
    # ─────────────────────────────────────────

    def _set_status(self, text: str, color: str, mode: str = "idle"):
        self.lbl_status.config(text=text, fg=color)
        colors = {
            "ok":       C["success"],
            "warn":     C["warning"],
            "error":    C["error"],
            "checking": C["accent"],
            "idle":     C["text_dim"],
        }
        self.canvas_indicator.itemconfig(
            self._indicator_oval, fill=colors.get(mode, C["text_dim"])
        )

    def _log(self, text: str, level: str = "INFO"):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {text}\n"
        self._ui(self._append_log, line, level)

    def _append_log(self, line: str, level: str):
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", line, level)
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def _set_text(self, widget: scrolledtext.ScrolledText, text: str):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.config(state="disabled")

    def _ui(self, func, *args):
        self.after(0, func, *args)

    def _clear_log(self):
        self.txt_log.config(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.config(state="disabled")

    # ─────────────────────────────────────────
    #  Cierre
    # ─────────────────────────────────────────

    def _on_close(self):
        self._retry_active = False
        self.usb_monitor.stop()
        self.adb.kill_server()
        self.destroy()


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

def main():
    app = ForensicADBHelper()
    app.mainloop()


if __name__ == "__main__":
    main()
