"""
Monitor USB para Windows.
Detecta dispositivos USB conectados/desconectados en tiempo real usando WMI.
Extrae VID/PID para identificar fabricante.
"""

import threading
import logging
import re
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False
    logger.warning("wmi no disponible. Usando polling como fallback.")

try:
    import win32api
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


# ─────────────────────────────────────────────
#  Detección de dispositivos USB
# ─────────────────────────────────────────────

def get_connected_usb_devices() -> list[dict]:
    """
    Retorna lista de dispositivos USB conectados con:
    { 'name', 'vid', 'pid', 'device_id', 'description' }
    """
    devices = []

    if not WMI_AVAILABLE:
        return _get_usb_devices_fallback()

    try:
        c = wmi.WMI()
        for device in c.Win32_PnPEntity():
            device_id = device.DeviceID or ""
            if "USB" not in device_id.upper():
                continue

            vid, pid = _extract_vid_pid(device_id)
            if not vid:
                continue

            name = device.Name or "Desconocido"
            description = device.Description or ""

            devices.append({
                "name": name,
                "vid": vid,
                "pid": pid,
                "device_id": device_id,
                "description": description,
                "status": device.Status or "",
            })
    except Exception as e:
        logger.error(f"Error obteniendo dispositivos USB via WMI: {e}")
        return _get_usb_devices_fallback()

    return devices


def _extract_vid_pid(device_id: str) -> tuple[str, str]:
    """
    Extrae VID y PID de un DeviceID de WMI.
    Ejemplo: USB\\VID_04E8&PID_6860\\...
    """
    vid_match = re.search(r"VID_([0-9A-Fa-f]{4})", device_id)
    pid_match = re.search(r"PID_([0-9A-Fa-f]{4})", device_id)
    vid = vid_match.group(1).lower() if vid_match else ""
    pid = pid_match.group(1).lower() if pid_match else ""
    return vid, pid


def _get_usb_devices_fallback() -> list[dict]:
    """Fallback usando subprocess + PowerShell si WMI no está disponible."""
    import subprocess
    devices = []
    try:
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "Get-PnpDevice -Class USB | Select-Object InstanceId, FriendlyName, Status | ConvertTo-Csv -NoTypeInformation"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        for line in result.stdout.splitlines()[1:]:  # saltar cabecera CSV
            parts = line.strip('"').split('","')
            if len(parts) >= 3:
                device_id = parts[0]
                name = parts[1]
                vid, pid = _extract_vid_pid(device_id)
                if vid:
                    devices.append({
                        "name": name, "vid": vid, "pid": pid,
                        "device_id": device_id, "description": "",
                        "status": parts[2],
                    })
    except Exception as e:
        logger.error(f"Fallback USB detection error: {e}")
    return devices


# ─────────────────────────────────────────────
#  Monitor en tiempo real (hilo de fondo)
# ─────────────────────────────────────────────

class USBMonitor:
    """
    Monitorea conexiones/desconexiones USB en tiempo real.
    Llama on_connect(device_info) / on_disconnect(device_info) en el hilo de fondo.
    """

    def __init__(
        self,
        on_connect: Optional[Callable[[dict], None]] = None,
        on_disconnect: Optional[Callable[[dict], None]] = None,
        poll_interval: float = 2.0,
    ):
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._known_devices: dict[str, dict] = {}

    def start(self) -> None:
        """Inicia el monitoreo en un hilo de fondo."""
        self._stop_event.clear()
        # Snapshot inicial
        for d in get_connected_usb_devices():
            self._known_devices[d["device_id"]] = d

        if WMI_AVAILABLE:
            self._thread = threading.Thread(target=self._wmi_loop, daemon=True)
        else:
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("USBMonitor iniciado.")

    def stop(self) -> None:
        """Detiene el monitoreo."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("USBMonitor detenido.")

    # ── WMI event-based ──────────────────────

    def _wmi_loop(self) -> None:
        """Escucha eventos WMI de creación/eliminación de dispositivos USB."""
        import pythoncom
        pythoncom.CoInitialize()
        try:
            c = wmi.WMI()
            watcher_create = c.Win32_PnPEntity.watch_for(
                notification_type="creation",
                delay_secs=1,
            )
            watcher_delete = c.Win32_PnPEntity.watch_for(
                notification_type="deletion",
                delay_secs=1,
            )

            while not self._stop_event.is_set():
                # Chequear conexiones nuevas
                try:
                    new_device = watcher_create(timeout_ms=500)
                    device_id = new_device.DeviceID or ""
                    if "USB" in device_id.upper():
                        vid, pid = _extract_vid_pid(device_id)
                        if vid:
                            info = {
                                "name": new_device.Name or "Desconocido",
                                "vid": vid, "pid": pid,
                                "device_id": device_id,
                                "description": new_device.Description or "",
                                "status": new_device.Status or "",
                            }
                            self._known_devices[device_id] = info
                            if self.on_connect:
                                self.on_connect(info)
                except wmi.x_wmi_timed_out:
                    pass

                # Chequear desconexiones
                try:
                    del_device = watcher_delete(timeout_ms=500)
                    device_id = del_device.DeviceID or ""
                    if device_id in self._known_devices:
                        info = self._known_devices.pop(device_id)
                        if self.on_disconnect:
                            self.on_disconnect(info)
                except wmi.x_wmi_timed_out:
                    pass

        except Exception as e:
            logger.error(f"Error en WMI loop: {e}. Cambiando a polling.")
            self._poll_loop()
        finally:
            pythoncom.CoUninitialize()

    # ── Polling fallback ──────────────────────

    def _poll_loop(self) -> None:
        """Detecta cambios comparando snapshots periódicos."""
        try:
            while not self._stop_event.wait(self.poll_interval):
                current = {d["device_id"]: d for d in get_connected_usb_devices()}

                # Nuevos dispositivos
                for dev_id, info in current.items():
                    if dev_id not in self._known_devices:
                        self._known_devices[dev_id] = info
                        if self.on_connect:
                            self.on_connect(info)

                # Dispositivos desconectados
                for dev_id in list(self._known_devices.keys()):
                    if dev_id not in current:
                        info = self._known_devices.pop(dev_id)
                        if self.on_disconnect:
                            self.on_disconnect(info)
        except Exception as e:
            logger.error(f"Error en poll loop: {e}")
