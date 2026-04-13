"""
Verificador de compatibilidad con Avilla Forensics.
"""

AVILLA_MIN_ANDROID = 5
AVILLA_MAX_ANDROID = 16

COMPATIBLE_MANUFACTURERS = {
    "Samsung", "Huawei", "Xiaomi", "Oppo", "Motorola",
    "Lg", "Sony", "Nokia", "Google", "Vivo", "Htc",
}

AVILLA_NOTES: dict[str, str] = {
    "Samsung":  "Compatible con extracción ADB y backup. Desactiva OEM Lock para imagen completa.",
    "Huawei":   "Compatible vía ADB. HarmonyOS puro puede limitar acceso. Usa HiSuite para backup.",
    "Xiaomi":   "Compatible. Activa también 'Depuración USB (modo seguridad)' en Opciones de desarrollador.",
    "Oppo":     "Compatible. En ColorOS 14+ activa también 'Instalación por USB' para mejor acceso.",
    "Google":   "Totalmente compatible. Android puro, máxima compatibilidad con Avilla.",
    "Motorola": "Compatible. Sin capas adicionales, buena compatibilidad general.",
    "Sony":     "Compatible. Verifica que el bootloader no bloquee ADB shell.",
    "Nokia":    "Compatible. Android One — excelente compatibilidad.",
    "Lg":       "Compatible. Soporte limitado en modelos post-2021.",
    "Vivo":     "Compatible. OriginOS puede requerir pasos adicionales.",
}


def check_avilla_compatibility(manufacturer: str, android_version_int: int) -> dict:
    """
    Retorna {'compatible': bool, 'level': str, 'note': str, 'color': str}
    """
    mfr = manufacturer.capitalize() if manufacturer else "Generic"

    version_ok = AVILLA_MIN_ANDROID <= android_version_int <= AVILLA_MAX_ANDROID
    mfr_known = any(m.lower() in mfr.lower() for m in COMPATIBLE_MANUFACTURERS)

    if version_ok and mfr_known:
        level, color = "Alta", "#2ecc71"
    elif version_ok:
        level, color = "Media", "#f39c12"
    elif mfr_known:
        level, color = "Limitada", "#f39c12"
    else:
        level, color = "Desconocida", "#e74c3c"

    compatible = level in ("Alta", "Media", "Limitada")

    note = next(
        (AVILLA_NOTES[k] for k in AVILLA_NOTES if k.lower() in mfr.lower()),
        "Compatibilidad no verificada. Prueba la extracción ADB básica primero."
    )

    return {
        "compatible": compatible,
        "level": level,
        "note": note,
        "color": color,
        "android_ok": version_ok,
        "manufacturer_known": mfr_known,
    }
