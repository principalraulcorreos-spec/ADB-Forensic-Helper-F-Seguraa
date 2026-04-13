"""
Base de datos de dispositivos Android para uso forense.
Contiene: VID/PID por fabricante, instrucciones de depuración USB,
URLs de drivers y rutas de configuración específicas por modelo.
"""

from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────
#  VID/PID  →  Fabricante
# ─────────────────────────────────────────────
VENDOR_ID_MAP: dict[str, str] = {
    "04e8": "Samsung",
    "18d1": "Google",
    "0bb4": "HTC",
    "22d9": "OPPO",
    "2a45": "OPPO",           # variante OnePlus/OPPO
    "22b8": "Motorola",
    "2717": "Xiaomi",
    "2a96": "Xiaomi",
    "12d1": "Huawei",
    "1004": "LG",
    "0fce": "Sony",
    "0421": "Nokia",
    "05c6": "Qualcomm/Generic",  # muchos dispositivos chinos
    "19d2": "ZTE",
    "1ebf": "Asus",
    "0489": "Fujitsu/Acer",
    "04dd": "Sharp",
    "2d95": "vivo",
    "1bbb": "TCL/Alcatel",
    "1f3a": "Allwinner",
    "2e04": "HMD/Nokia",
    "413c": "Dell",
    "03f0": "HP",
    "0a5c": "Broadcom",
    "0e8d": "MediaTek",
    "2109": "VIA Labs (hub genérico)",
}


@dataclass
class ManufacturerProfile:
    name: str
    driver_url: str
    driver_name: str
    # Instrucciones para activar Depuración USB
    # Cada elemento es un paso numerado
    debug_steps_generic: list[str] = field(default_factory=list)
    # Pasos específicos por versión de Android o modelo
    debug_steps_android10_plus: list[str] = field(default_factory=list)
    # Nota forense especial (e.g., advertencias de cifrado, permisos)
    forensic_note: str = ""


# ─────────────────────────────────────────────
#  Perfiles de fabricantes
# ─────────────────────────────────────────────
MANUFACTURER_PROFILES: dict[str, ManufacturerProfile] = {

    "Samsung": ManufacturerProfile(
        name="Samsung",
        driver_url="https://developer.samsung.com/mobile/android-usb-driver.html",
        driver_name="Samsung USB Driver for Mobile Phones",
        debug_steps_generic=[
            "1. Ve a  Ajustes  →  Acerca del teléfono",
            "2. Pulsa  Información de software  (en algunos modelos está directo).",
            "3. Toca  Número de compilación  7 veces rápido.",
            "   → Aparecerá: '¡Ahora eres desarrollador!'",
            "4. Regresa a  Ajustes  →  Opciones de desarrollador.",
            "5. Activa el interruptor principal de  Opciones de desarrollador.",
            "6. Busca y activa  Depuración USB.",
            "7. Conecta el cable USB y selecciona  'Transferencia de archivos (MTP)'.",
            "8. En el teléfono aparecerá un aviso — pulsa  PERMITIR.",
        ],
        debug_steps_android10_plus=[
            "1. Ajustes  →  Acerca del teléfono  →  Información de software.",
            "2. Toca  Número de compilación  7 veces.",
            "3. Ajustes  →  Opciones de desarrollador  →  activa  Depuración USB.",
            "4. Si pide autorización de huella/PIN para activar opciones de desarrollador, ingrésala.",
        ],
        forensic_note=(
            "Samsung Knox puede mostrar advertencia de 'modo desarrollador activado'. "
            "En algunos Galaxy S/A recientes (Android 13+) el menú es: "
            "Ajustes → Administración general → Información de software → Número de compilación."
        ),
    ),

    "OPPO": ManufacturerProfile(
        name="OPPO / OnePlus / Realme",
        driver_url="https://community.oneplus.com/thread/1478264",
        driver_name="OPPO/OnePlus USB Driver (MTK o Qualcomm)",
        debug_steps_generic=[
            "1. Ve a  Ajustes  →  Acerca del teléfono  →  Versión.",
            "2. Toca  Número de compilación  7 veces.",
            "   (En ColorOS puede estar en: Ajustes → Acerca del dispositivo → Versión de ColorOS)",
            "3. Ingresa el PIN/contraseña de la pantalla si lo solicita.",
            "4. Regresa a  Ajustes  →  Opciones adicionales  →  Opciones de desarrollador.",
            "   (O: Ajustes → Sistema → Opciones de desarrollador)",
            "5. Activa  Depuración USB.",
            "6. Conecta el cable — selecciona  'Cargar solamente'  o  'Transferencia de archivos'.",
            "7. Acepta el aviso de autorización en pantalla.",
        ],
        debug_steps_android10_plus=[
            "ColorOS 14 / Android 14-16 (OPPO RENO, Find X, A-series):",
            "1. Ajustes → Acerca del dispositivo → Número de versión  (tocar 7 veces).",
            "2. Ajustes → Opciones adicionales → Opciones de desarrollador.",
            "3. Activar  Depuración USB.",
            "4. Conectar cable → popup de autorización RSA → ACEPTAR.",
        ],
        forensic_note=(
            "OPPO con Android 16 / ColorOS 15: la ruta puede ser "
            "Ajustes → Sistema → Acerca del dispositivo → Número de compilación. "
            "Algunos modelos muestran la autorización RSA solo si ADB ya está instalado en la PC; "
            "instala primero el driver y luego vuelve a conectar."
        ),
    ),

    "Xiaomi": ManufacturerProfile(
        name="Xiaomi / Redmi / POCO",
        driver_url="https://xiaomifirmwareupdater.com/drivers/",
        driver_name="Xiaomi USB Driver (MIUI)",
        debug_steps_generic=[
            "1. Ve a  Ajustes  →  Acerca del teléfono  →  Información de MIUI.",
            "2. Toca  Número de versión de MIUI  7 veces.",
            "3. Ajustes  →  Ajustes adicionales  →  Opciones de desarrollador.",
            "4. Activa  Depuración USB.",
            "5. Conecta el cable y acepta el aviso RSA.",
        ],
        debug_steps_android10_plus=[
            "HyperOS / MIUI 14+ (Android 13-15):",
            "1. Ajustes → Mi cuenta → Acerca del teléfono → Número de versión de MIUI (×7).",
            "2. Ajustes → Ajustes adicionales → Opciones de desarrollador.",
            "3. Activar Depuración USB + Depuración USB (modo de seguridad) si aparece.",
            "4. Autorizar el equipo en el popup.",
            "ATENCIÓN: Xiaomi puede pedir vincular cuenta Mi para desbloquear OEM. "
            "No es necesario para solo habilitar ADB en lectura.",
        ],
        forensic_note=(
            "Algunos Xiaomi requieren también activar 'Instalación vía USB' para "
            "aceptar la clave RSA. Si el dispositivo aparece como 'unauthorized', "
            "activa también esa opción."
        ),
    ),

    "Huawei": ManufacturerProfile(
        name="Huawei / Honor",
        driver_url="https://consumer.huawei.com/en/support/hisuite/",
        driver_name="Huawei HiSuite (incluye drivers USB)",
        debug_steps_generic=[
            "1. Ve a  Ajustes  →  Acerca del teléfono  →  Número de compilación.",
            "2. Toca el número  7 veces.",
            "3. Ajustes  →  Sistema  →  Opciones de desarrollador.",
            "4. Activa  Depuración USB.",
            "5. Conecta el cable — selecciona  'Transferencia de archivos'.",
            "6. Acepta el aviso de autorización RSA.",
        ],
        debug_steps_android10_plus=[
            "EMUI 10+ / HarmonyOS:",
            "1. Ajustes → Sistema → Acerca del teléfono → Número de compilación (×7).",
            "2. Ajustes → Sistema → Opciones de desarrollador → Depuración USB.",
            "NOTA: HarmonyOS 4+ puede no soportar ADB de la misma forma que Android.",
            "Si el dispositivo usa HarmonyOS puro (sin capa Android), la detección ADB puede fallar.",
        ],
        forensic_note=(
            "Huawei post-2020 sin GMS: instala HiSuite para asegurar el driver correcto. "
            "Algunos P-series y Mate-series requieren EMUI en modo desarrollador Y "
            "aceptar la clave RSA en pantalla para autenticar el host."
        ),
    ),

    "Motorola": ManufacturerProfile(
        name="Motorola / Lenovo",
        driver_url="https://motorola-global-portal.custhelp.com/app/answers/detail/a_id/88481",
        driver_name="Motorola Device Manager (incluye drivers)",
        debug_steps_generic=[
            "1. Ve a  Ajustes  →  Acerca del teléfono  →  Número de compilación.",
            "2. Toca 7 veces.",
            "3. Ajustes  →  Sistema  →  Opciones de desarrollador.",
            "4. Activa  Depuración USB.",
            "5. Conecta el cable y acepta el aviso.",
        ],
        debug_steps_android10_plus=[
            "Android 12+ (Moto G, Edge, Razr):",
            "1. Ajustes → Acerca del teléfono → Número de compilación (×7).",
            "2. Ajustes → Sistema → Opciones de desarrollador avanzadas → Depuración USB.",
        ],
        forensic_note="Motorola generalmente usa drivers genéricos de Google. El driver universal ADB suele funcionar.",
    ),

    "LG": ManufacturerProfile(
        name="LG Electronics",
        driver_url="https://www.lg.com/us/support/software-firmware",
        driver_name="LG USB Driver for Mobile Phones",
        debug_steps_generic=[
            "1. Ve a  Ajustes  →  Acerca del teléfono  →  Información del software.",
            "2. Toca  Número de compilación  7 veces.",
            "3. Ajustes  →  Opciones de desarrollador.",
            "4. Activa  Depuración USB.",
            "5. Conecta el cable y acepta.",
        ],
        forensic_note="LG dejó de fabricar móviles en 2021. El soporte de drivers puede estar limitado.",
    ),

    "Sony": ManufacturerProfile(
        name="Sony Xperia",
        driver_url="https://developer.sony.com/posts/xperia-usb-driver-for-windows/",
        driver_name="Sony Xperia USB Driver",
        debug_steps_generic=[
            "1. Ajustes  →  Acerca del teléfono  →  Número de compilación  (×7).",
            "2. Ajustes  →  Sistema  →  Opciones de desarrollador.",
            "3. Activa  Depuración USB.",
            "4. Conecta el cable → acepta autorización.",
        ],
        forensic_note="Sony Xperia: si el dispositivo aparece como 'FastBoot' en lugar de ADB, mantén volumen abajo al conectar.",
    ),

    "Nokia": ManufacturerProfile(
        name="Nokia / HMD Global",
        driver_url="https://www.nokia.com/phones/en_us/support",
        driver_name="Nokia USB Driver (usa driver Google genérico)",
        debug_steps_generic=[
            "1. Ajustes  →  Acerca del teléfono  →  Número de compilación  (×7).",
            "2. Ajustes  →  Sistema  →  Opciones de desarrollador.",
            "3. Activa  Depuración USB.",
        ],
        forensic_note="Nokia/HMD usa Android One; compatible con driver Google universal.",
    ),

    "Google": ManufacturerProfile(
        name="Google Pixel",
        driver_url="https://developer.android.com/studio/run/win-usb",
        driver_name="Google USB Driver",
        debug_steps_generic=[
            "1. Ajustes  →  Acerca del teléfono  →  Número de compilación  (×7).",
            "2. Ajustes  →  Sistema  →  Opciones de desarrollador.",
            "3. Activa  Depuración USB.",
            "4. Conecta el cable y acepta.",
        ],
        forensic_note="Google Pixel: usar Google USB Driver oficial. Android puro, sin capas adicionales.",
    ),

    "vivo": ManufacturerProfile(
        name="vivo",
        driver_url="https://www.vivo.com/en/support",
        driver_name="vivo USB Driver",
        debug_steps_generic=[
            "1. Ajustes  →  Acerca del teléfono  →  Versión  (×7).",
            "2. Ajustes  →  Sistema  →  Opciones de desarrollador.",
            "3. Activa  Depuración USB.",
        ],
        forensic_note="vivo usa OriginOS/FunTouch OS. La ruta puede variar según la versión de la ROM.",
    ),

    "Generic": ManufacturerProfile(
        name="Dispositivo Android Genérico",
        driver_url="https://developer.android.com/studio/run/win-usb",
        driver_name="Google USB Driver (universal)",
        debug_steps_generic=[
            "1. Abre  Ajustes  en el dispositivo.",
            "2. Ve a  Acerca del teléfono  (o 'Información del dispositivo').",
            "3. Busca  Número de compilación  y tócalo 7 veces.",
            "   → Verás el mensaje '¡Ahora eres desarrollador!'",
            "4. Regresa a  Ajustes  →  Sistema  (o 'Opciones adicionales').",
            "5. Entra a  Opciones de desarrollador.",
            "6. Activa el interruptor  Depuración USB.",
            "7. Conecta el cable USB al PC y acepta el aviso de autorización.",
        ],
        forensic_note="Dispositivo desconocido. Instala Google USB Driver universal y consulta la documentación del fabricante.",
    ),
}


def get_manufacturer_from_vid(vid: str) -> str:
    """Retorna el nombre del fabricante dado un Vendor ID (hex, minúsculas)."""
    return VENDOR_ID_MAP.get(vid.lower(), "Generic")


def get_profile(manufacturer: str) -> ManufacturerProfile:
    """Retorna el perfil del fabricante o el genérico si no existe."""
    return MANUFACTURER_PROFILES.get(manufacturer, MANUFACTURER_PROFILES["Generic"])


def get_instructions_for_android_version(profile: ManufacturerProfile, android_version: int) -> list[str]:
    """Selecciona las instrucciones más adecuadas según versión de Android."""
    if android_version >= 10 and profile.debug_steps_android10_plus:
        return profile.debug_steps_android10_plus
    return profile.debug_steps_generic
