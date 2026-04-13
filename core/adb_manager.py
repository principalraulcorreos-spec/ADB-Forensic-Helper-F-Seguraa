"""
Gestor de operaciones ADB para uso forense.
Todas las operaciones son de solo lectura. No se instala nada en el dispositivo.
"""

import subprocess
import os
import sys
import re
import time
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ADBStatus(Enum):
    NOT_FOUND      = "adb_not_found"        # adb.exe no está disponible
    NO_DEVICES     = "no_devices"           # adb devices no lista nada
    UNAUTHORIZED   = "unauthorized"         # dispositivo conectado pero no autorizado
    OFFLINE        = "offline"              # dispositivo offline/reiniciando
    CONNECTED      = "connected"            # listo para usar


@dataclass
class DeviceInfo:
    serial: str
    status: str                             # "device", "unauthorized", "offline"
    manufacturer: str = "Desconocido"
    model: str = "Desconocido"
    android_version: str = "Desconocido"
    android_version_int: int = 0
    build_id: str = "Desconocido"
    product: str = "Desconocido"
    vid: str = ""
    pid: str = ""


class ADBManager:
    """
    Gestiona la comunicación con ADB.
    Usa adb.exe embebido en assets/ o el del PATH del sistema.
    """

    def __init__(self, adb_path: Optional[str] = None):
        self.adb_path = adb_path or self._find_adb()

    # ─────────────────────────────────────────
    #  Localización de adb.exe
    # ─────────────────────────────────────────

    def _find_adb(self) -> str:
        """Busca adb.exe: primero en assets/, luego en PATH."""
        # Directorio del ejecutable / script
        if getattr(sys, "frozen", False):
            base = sys._MEIPASS  # PyInstaller bundle
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        embedded = os.path.join(base, "assets", "adb", "adb.exe")
        if os.path.exists(embedded):
            logger.info(f"ADB encontrado (embebido): {embedded}")
            return embedded

        # Buscar en PATH
        try:
            result = subprocess.run(
                ["where", "adb"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                path = result.stdout.strip().splitlines()[0]
                logger.info(f"ADB encontrado en PATH: {path}")
                return path
        except Exception:
            pass

        logger.warning("adb.exe no encontrado. Descarga requerida.")
        return "adb"  # intentar igualmente; fallará con mensaje claro

    def is_available(self) -> bool:
        """Verifica que adb.exe es ejecutable."""
        try:
            r = subprocess.run(
                [self.adb_path, "version"],
                capture_output=True, text=True, timeout=5
            )
            return r.returncode == 0
        except Exception:
            return False

    # ─────────────────────────────────────────
    #  Operaciones ADB
    # ─────────────────────────────────────────

    def _run(self, *args, timeout: int = 10) -> tuple[int, str, str]:
        """Ejecuta un comando ADB y retorna (returncode, stdout, stderr)."""
        cmd = [self.adb_path] + list(args)
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout, encoding="utf-8", errors="replace"
            )
            return r.returncode, r.stdout.strip(), r.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Timeout"
        except FileNotFoundError:
            return -2, "", f"No se encontró: {self.adb_path}"

    def start_server(self) -> bool:
        """Inicia el servidor ADB."""
        code, _, err = self._run("start-server", timeout=15)
        if code != 0:
            logger.error(f"Error iniciando servidor ADB: {err}")
        return code == 0

    def kill_server(self) -> None:
        """Detiene el servidor ADB."""
        self._run("kill-server", timeout=5)

    def list_devices(self) -> list[tuple[str, str]]:
        """
        Retorna lista de (serial, estado).
        Estado puede ser: 'device', 'unauthorized', 'offline'.
        """
        _, out, _ = self._run("devices", timeout=10)
        devices = []
        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith("List of"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                devices.append((parts[0], parts[1]))
        return devices

    def get_overall_status(self) -> ADBStatus:
        """Determina el estado global de ADB + dispositivos."""
        if not self.is_available():
            return ADBStatus.NOT_FOUND

        devices = self.list_devices()
        if not devices:
            return ADBStatus.NO_DEVICES

        for serial, state in devices:
            if state == "device":
                return ADBStatus.CONNECTED
            if state == "unauthorized":
                return ADBStatus.UNAUTHORIZED
            if state == "offline":
                return ADBStatus.OFFLINE

        return ADBStatus.NO_DEVICES

    def get_device_property(self, serial: str, prop: str) -> str:
        """Lee una propiedad del sistema del dispositivo (solo lectura)."""
        _, out, _ = self._run("-s", serial, "shell", "getprop", prop, timeout=8)
        return out.strip()

    def get_full_device_info(self, serial: str) -> DeviceInfo:
        """
        Recopila información del dispositivo vía ADB (solo lectura).
        No instala ni modifica nada en el dispositivo.
        """
        def prop(key: str) -> str:
            return self.get_device_property(serial, key)

        manufacturer = prop("ro.product.manufacturer") or "Desconocido"
        model        = prop("ro.product.model")        or "Desconocido"
        android_ver  = prop("ro.build.version.release") or "Desconocido"
        build_id     = prop("ro.build.id")             or "Desconocido"
        product      = prop("ro.product.name")         or "Desconocido"

        try:
            android_int = int(android_ver.split(".")[0])
        except (ValueError, AttributeError):
            android_int = 0

        return DeviceInfo(
            serial=serial,
            status="device",
            manufacturer=manufacturer.capitalize(),
            model=model,
            android_version=android_ver,
            android_version_int=android_int,
            build_id=build_id,
            product=product,
        )

    def wait_for_device(self, timeout_seconds: int = 30) -> bool:
        """
        Espera a que aparezca un dispositivo autorizado.
        Retorna True si aparece antes del timeout.
        """
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            status = self.get_overall_status()
            if status == ADBStatus.CONNECTED:
                return True
            time.sleep(2)
        return False

    def get_adb_version(self) -> str:
        """Retorna la versión de ADB instalada."""
        _, out, _ = self._run("version", timeout=5)
        match = re.search(r"Android Debug Bridge version (.+)", out)
        return match.group(1) if match else "Desconocido"


# ─────────────────────────────────────────────────
#  Helper: parsear VID/PID desde serial ADB
# ─────────────────────────────────────────────────

def parse_vid_pid_from_serial(serial: str) -> tuple[str, str]:
    """
    Algunos seriales tienen formato 'usb:VID:PID:...' o similar.
    Retorna ("", "") si no se puede parsear.
    """
    # Formato típico en algunos hosts: "xxxxxxxx" (no contiene VID/PID directamente)
    # El VID/PID se obtiene mejor vía WMI (usb_monitor.py)
    return "", ""
