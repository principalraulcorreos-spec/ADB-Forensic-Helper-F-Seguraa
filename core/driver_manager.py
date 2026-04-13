"""
Gestor de drivers USB para Windows.
Detecta si el driver correcto está instalado y, si no, guía al usuario
para instalarlo o lo instala usando el driver universal de Google.
"""

import os
import sys
import subprocess
import logging
import tempfile
import zipfile
import shutil
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# URL del driver universal ADB de Google (plataform-tools incluye ADB)
GOOGLE_USB_DRIVER_PAGE = "https://developer.android.com/studio/run/win-usb"
PLATFORM_TOOLS_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
GOOGLE_USB_DRIVER_URL = "https://dl.google.com/android/repository/usb_driver_r13-windows.zip"

# INF del driver universal de Google (parte del Android SDK)
GOOGLE_DRIVER_INF = "android_winusb.inf"

# URLs de descarga directa de drivers por fabricante
DRIVER_DOWNLOAD_URLS: dict[str, str] = {
    "Samsung":  "https://dl.google.com/android/repository/usb_driver_r13-windows.zip",
    "Huawei":   "https://dl.google.com/android/repository/usb_driver_r13-windows.zip",
    "Xiaomi":   "https://dl.google.com/android/repository/usb_driver_r13-windows.zip",
    "OPPO":     "https://dl.google.com/android/repository/usb_driver_r13-windows.zip",
    "Motorola": "https://dl.google.com/android/repository/usb_driver_r13-windows.zip",
    "LG":       "https://dl.google.com/android/repository/usb_driver_r13-windows.zip",
    "Sony":     "https://dl.google.com/android/repository/usb_driver_r13-windows.zip",
    "Nokia":    "https://dl.google.com/android/repository/usb_driver_r13-windows.zip",
    "Google":   "https://dl.google.com/android/repository/usb_driver_r13-windows.zip",
    "vivo":     "https://dl.google.com/android/repository/usb_driver_r13-windows.zip",
    "Generic":  "https://dl.google.com/android/repository/usb_driver_r13-windows.zip",
}


class DriverManager:

    def __init__(self):
        self._base_dir = self._get_base_dir()

    def _get_base_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys._MEIPASS)
        return Path(__file__).parent.parent

    # ─────────────────────────────────────────
    #  Verificación de driver instalado
    # ─────────────────────────────────────────

    def is_driver_installed(self, vid: str, pid: str) -> bool:
        """
        Verifica en el registro de Windows si hay un driver instalado
        para el VID/PID dado usando PowerShell/PnP.
        """
        if not vid or not pid:
            return False

        try:
            hardware_id = f"USB\\VID_{vid.upper()}&PID_{pid.upper()}"
            cmd = [
                "powershell", "-NoProfile", "-Command",
                f"Get-PnpDevice | Where-Object {{ $_.InstanceId -like '*{hardware_id.replace('\\\\', '\\\\')}*' }} | Select-Object Status, FriendlyName | ConvertTo-Json"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            output = result.stdout.strip()

            if not output or output == "null":
                return False

            # Si hay resultado con Status OK, el driver está instalado
            return '"Status"' in output and '"OK"' in output

        except Exception as e:
            logger.error(f"Error verificando driver: {e}")
            return False

    def get_driver_status(self, vid: str, pid: str) -> dict:
        """
        Retorna información detallada sobre el estado del driver.
        """
        status = {
            "installed": False,
            "device_name": "Desconocido",
            "driver_status": "No encontrado",
            "needs_install": True,
        }

        try:
            hardware_id = f"USB\\VID_{vid.upper()}&PID_{pid.upper()}"
            cmd = [
                "powershell", "-NoProfile", "-Command",
                (
                    f"$dev = Get-PnpDevice | Where-Object {{ $_.InstanceId -like '*VID_{vid.upper()}*PID_{pid.upper()}*' }}; "
                    "$dev | Select-Object Status, FriendlyName, Class, Problem | ConvertTo-Json"
                )
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            output = result.stdout.strip()

            if output and output != "null":
                import json
                try:
                    # Puede ser objeto o lista
                    data = json.loads(output)
                    if isinstance(data, list):
                        data = data[0] if data else {}

                    status["device_name"] = data.get("FriendlyName") or "Desconocido"
                    driver_status = data.get("Status", "")
                    status["driver_status"] = driver_status

                    if driver_status == "OK":
                        status["installed"] = True
                        status["needs_install"] = False
                    elif driver_status in ("Unknown", "Error", "Degraded"):
                        status["needs_install"] = True
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.error(f"Error obteniendo estado de driver: {e}")

        return status

    # ─────────────────────────────────────────
    #  Descarga de platform-tools (ADB)
    # ─────────────────────────────────────────

    def download_platform_tools(self, dest_dir: Optional[str] = None, progress_callback=None) -> Optional[str]:
        """
        Descarga Android Platform Tools (contiene adb.exe).
        Retorna la ruta al directorio extraído o None en caso de error.
        """
        try:
            import urllib.request

            if dest_dir is None:
                dest_dir = str(self._base_dir / "assets" / "adb")

            os.makedirs(dest_dir, exist_ok=True)

            zip_path = os.path.join(tempfile.gettempdir(), "platform-tools.zip")

            logger.info(f"Descargando platform-tools desde: {PLATFORM_TOOLS_URL}")

            def reporthook(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    pct = min(100, int(block_num * block_size * 100 / total_size))
                    progress_callback(pct)

            urllib.request.urlretrieve(PLATFORM_TOOLS_URL, zip_path, reporthook)

            # Extraer solo adb.exe y sus DLLs
            with zipfile.ZipFile(zip_path, "r") as zf:
                needed = ["platform-tools/adb.exe",
                          "platform-tools/AdbWinApi.dll",
                          "platform-tools/AdbWinUsbApi.dll"]
                for member in needed:
                    try:
                        data = zf.read(member)
                        filename = os.path.basename(member)
                        out_path = os.path.join(dest_dir, filename)
                        with open(out_path, "wb") as f:
                            f.write(data)
                        logger.info(f"Extraído: {out_path}")
                    except KeyError:
                        logger.warning(f"No encontrado en ZIP: {member}")

            os.unlink(zip_path)
            return dest_dir

        except Exception as e:
            logger.error(f"Error descargando platform-tools: {e}")
            return None

    # ─────────────────────────────────────────
    #  Instalación de driver Google Universal
    # ─────────────────────────────────────────

    def install_google_usb_driver(self) -> tuple[bool, str]:
        """
        Intenta instalar el Google USB Driver universal usando pnputil.
        Requiere privilegios de administrador.
        Retorna (éxito, mensaje).
        """
        # Buscar el INF en assets/
        inf_candidates = [
            self._base_dir / "assets" / "drivers" / GOOGLE_DRIVER_INF,
            self._base_dir / "assets" / GOOGLE_DRIVER_INF,
        ]

        inf_path = None
        for candidate in inf_candidates:
            if candidate.exists():
                inf_path = candidate
                break

        if not inf_path:
            return False, (
                "Driver INF no encontrado localmente.\n"
                f"Descarga el Google USB Driver desde:\n{GOOGLE_USB_DRIVER_PAGE}\n"
                "y coloca android_winusb.inf en assets/drivers/"
            )

        try:
            result = subprocess.run(
                ["pnputil", "/add-driver", str(inf_path), "/install"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                return True, "Driver instalado correctamente via pnputil."
            else:
                return False, f"Error al instalar driver:\n{result.stderr or result.stdout}"

        except subprocess.TimeoutExpired:
            return False, "Timeout instalando driver."
        except Exception as e:
            return False, f"Error: {e}"

    def auto_install_driver(self, manufacturer: str, progress_callback=None) -> tuple[bool, str]:
        """
        Descarga e instala automáticamente el driver correcto para el fabricante.
        Retorna (éxito, mensaje).
        """
        import urllib.request

        url = DRIVER_DOWNLOAD_URLS.get(manufacturer, GOOGLE_USB_DRIVER_URL)
        driver_dir = self._base_dir / "assets" / "drivers"
        driver_dir.mkdir(parents=True, exist_ok=True)

        # Si termina en .zip → driver tipo Google (INF + pnputil)
        if url.endswith(".zip"):
            return self._download_and_install_inf_driver(url, driver_dir, progress_callback)

        # Si termina en .exe → instalador (Samsung HiSuite, etc.)
        elif url.endswith(".exe"):
            return self._download_and_run_installer(url, driver_dir, manufacturer, progress_callback)

        else:
            return False, f"No hay descarga automática para {manufacturer}.\nVisita: {url}"

    def _download_and_install_inf_driver(self, url: str, driver_dir: Path, progress_callback=None) -> tuple[bool, str]:
        """Descarga un ZIP con INF y lo instala con pnputil."""
        import urllib.request

        zip_path = Path(tempfile.gettempdir()) / "adb_driver.zip"
        extract_dir = Path(tempfile.gettempdir()) / "adb_driver_extracted"

        try:
            if progress_callback:
                progress_callback(0, "Descargando driver...")

            def reporthook(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    pct = min(90, int(block_num * block_size * 100 / total_size))
                    progress_callback(pct, f"Descargando... {pct}%")

            urllib.request.urlretrieve(url, zip_path, reporthook)

            if progress_callback:
                progress_callback(92, "Extrayendo driver...")

            # Extraer todo el ZIP preservando estructura
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            extract_dir.mkdir(parents=True)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)

            zip_path.unlink(missing_ok=True)

            # Buscar el .inf dentro del directorio extraído
            inf_path = None
            for inf_file in extract_dir.rglob("*.inf"):
                inf_path = inf_file
                logger.info(f"INF encontrado: {inf_path}")
                break

            if not inf_path:
                return False, "No se encontró archivo .inf en el driver descargado."

            if progress_callback:
                progress_callback(96, "Instalando driver con pnputil...")

            # Instalar con pnputil usando la ruta absoluta al .inf
            # pnputil necesita que .inf y .cat estén en el mismo directorio
            result = subprocess.run(
                ["pnputil", "/add-driver", str(inf_path.resolve()), "/install"],
                capture_output=True, text=True, timeout=60,
                cwd=str(inf_path.parent)
            )

            if progress_callback:
                progress_callback(100, "Listo.")

            logger.info(f"pnputil stdout: {result.stdout}")
            logger.info(f"pnputil stderr: {result.stderr}")

            # pnputil devuelve 0 o 3010 (requiere reinicio) en éxito
            if result.returncode in (0, 3010):
                msg = "Driver instalado correctamente."
                if result.returncode == 3010:
                    msg += "\nReinicia el equipo para completar la instalación."
                return True, msg
            else:
                return False, f"Error al instalar driver (código {result.returncode}):\n{result.stdout}\n{result.stderr}"

        except Exception as e:
            logger.error(f"Error instalando driver: {e}")
            return False, f"Error durante la instalación: {e}"
        finally:
            if extract_dir.exists():
                try:
                    shutil.rmtree(extract_dir)
                except Exception:
                    pass

    def _download_and_run_installer(self, url: str, driver_dir: Path, manufacturer: str, progress_callback=None) -> tuple[bool, str]:
        """Descarga un .exe instalador y lo ejecuta."""
        import urllib.request

        exe_name = f"driver_{manufacturer.lower()}.exe"
        exe_path = driver_dir / exe_name

        try:
            if progress_callback:
                progress_callback(0, f"Descargando instalador de {manufacturer}...")

            def reporthook(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    pct = min(90, int(block_num * block_size * 100 / total_size))
                    progress_callback(pct, f"Descargando... {pct}%")

            urllib.request.urlretrieve(url, exe_path, reporthook)

            if progress_callback:
                progress_callback(95, "Ejecutando instalador...")

            subprocess.Popen([str(exe_path)], shell=False)
            return True, f"Instalador de {manufacturer} descargado y ejecutado.\nSigue los pasos en pantalla."

        except Exception as e:
            logger.error(f"Error descargando instalador: {e}")
            return False, f"Error: {e}"

    def is_admin(self) -> bool:
        """Verifica si el proceso tiene privilegios de administrador."""
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def get_install_guidance(self, manufacturer: str) -> list[str]:
        """
        Retorna instrucciones para instalar el driver del fabricante.
        """
        from core.device_database import get_profile
        profile = get_profile(manufacturer)

        steps = [
            f"Driver recomendado: {profile.driver_name}",
            f"URL de descarga: {profile.driver_url}",
            "",
            "Instrucciones de instalación:",
            "1. Descarga el driver desde la URL anterior.",
            "2. Extrae el archivo ZIP/EXE descargado.",
            "3. Abre el Administrador de dispositivos (Win+X → Administrador de dispositivos).",
            "4. Busca el dispositivo con signo de advertencia amarillo.",
            "5. Clic derecho → 'Actualizar controlador'.",
            "6. Elige 'Buscar software de controlador en mi equipo'.",
            "7. Navega a la carpeta donde extrajiste el driver.",
            "8. Acepta la instalación.",
            "9. Desconecta y vuelve a conectar el dispositivo.",
        ]

        if manufacturer == "Generic":
            steps.insert(0, "Usando Google USB Driver universal (recomendado para dispositivos sin driver específico).")

        return steps
