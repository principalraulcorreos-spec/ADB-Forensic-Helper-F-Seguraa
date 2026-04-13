@echo off
:: ADB Forensic Helper - Setup y ejecucion rapida
:: Ejecutar este .bat la primera vez para instalar dependencias

:: Auto-elevacion a administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permisos de administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs -WorkingDirectory '%~dp0'"
    exit /b
)

title ADB Forensic Helper - Setup

:: Cambiar al directorio donde está el .bat
cd /d "%~dp0"

echo ============================================
echo  ADB Forensic Helper - Instalacion inicial
echo ============================================
echo.

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado en el sistema.
    echo Descarga Python 3.10+ desde https://www.python.org/downloads/
    echo Asegurate de marcar "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

echo [OK] Python encontrado:
python --version
echo.

:: Instalar dependencias
echo Instalando dependencias...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de dependencias.
    pause
    exit /b 1
)

:: Post-instalacion de pywin32 (necesario para pythoncom/wmi)
echo Configurando pywin32...
python -c "import pywin32_postinstall; pywin32_postinstall.install()" 2>nul
python Scripts\pywin32_postinstall.py -install 2>nul
echo.

echo.
echo [OK] Dependencias instaladas correctamente.
echo.

:: Ejecutar la herramienta
echo Iniciando ADB Forensic Helper...
python main.py

pause
