# ADB Forensic Helper

Asistente de conexión forense para dispositivos Android. Diseñado para facilitar la configuración de ADB (Android Debug Bridge) antes de usar herramientas forenses como **Avilla Forensics**.

---

## ¿Qué hace?

- Detecta automáticamente cuando conectas un celular Android por USB
- Identifica el fabricante del dispositivo (Samsung, Huawei, Xiaomi, OPPO, etc.)
- Descarga e instala el driver USB correcto automáticamente
- Muestra instrucciones paso a paso para activar la Depuración USB según el modelo
- Verifica que el dispositivo esté listo para ser analizado

---

## Capturas

> Interfaz con tema oscuro forense, indicador de estado en tiempo real y pestañas de instrucciones, driver y log ADB.

---

## Requisitos

- Windows 10 / 11
- Python 3.10 o superior
- Conexión a internet (solo la primera vez, para descargar ADB y drivers)

---

## Instalación y uso

### Opción 1 — Ejecutable (recomendado, sin instalar nada)

1. Descarga el ZIP desde la sección [Releases](../../releases)
2. Descomprime en cualquier carpeta
3. Doble clic en `ADB_Forensic_Helper.exe`
4. Acepta el aviso de administrador

### Opción 2 — Desde el código fuente

```bash
git clone https://github.com/principalraulcorreos-spec/ADB-Forensic-Helper-F-Seguraa.git
cd ADB-Forensic-Helper-F-Seguraa
setup_and_run.bat
```

> Ejecutar `setup_and_run.bat` como administrador. Instala dependencias y lanza el programa automáticamente.

---

## Compilar a .exe

```bash
build_exe.bat
```

El ejecutable se genera en `dist\ADB_Forensic_Helper\`.

---

## Fabricantes soportados

| Fabricante | Driver automático |
|---|---|
| Samsung | Google USB Driver |
| Huawei | Google USB Driver |
| Xiaomi / Redmi / POCO | Google USB Driver |
| OPPO / OnePlus / Realme | Google USB Driver |
| Motorola / Lenovo | Google USB Driver |
| Sony Xperia | Google USB Driver |
| Nokia / HMD | Google USB Driver |
| Google Pixel | Google USB Driver |
| vivo | Google USB Driver |
| Genérico / otros | Google USB Driver |

---

## Estructura del proyecto

```
ADB_Forensic_Helper/
├── main.py                  # Interfaz gráfica principal (Tkinter)
├── core/
│   ├── adb_manager.py       # Comunicación con ADB
│   ├── usb_monitor.py       # Detección de dispositivos USB en tiempo real
│   ├── driver_manager.py    # Descarga e instalación de drivers
│   └── device_database.py   # Base de datos de fabricantes e instrucciones
├── assets/
│   └── adb/                 # ADB se descarga aquí automáticamente
├── setup_and_run.bat        # Instalación y ejecución
├── build_exe.bat            # Compilar a ejecutable
├── build.spec               # Configuración de PyInstaller
└── requirements.txt         # Dependencias Python
```

---

## Licencia

MIT License — libre para usar, modificar y distribuir.
