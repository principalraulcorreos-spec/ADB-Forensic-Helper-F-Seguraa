@echo off
:: Compila ADB Forensic Helper a un .exe standalone usando PyInstaller

title ADB Forensic Helper - Build EXE

:: Ir al directorio del script (NO correr desde System32)
cd /d "%~dp0"

echo ============================================
echo  ADB Forensic Helper - Compilar a .exe
echo ============================================
echo.

:: Verificar PyInstaller
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

:: Limpiar builds anteriores
if exist "dist\ADB_Forensic_Helper" (
    echo Limpiando build anterior...
    rmdir /s /q "dist\ADB_Forensic_Helper"
)
if exist "build" rmdir /s /q "build"

:: Compilar SIN admin (PyInstaller no lo necesita)
echo Compilando...
pyinstaller build.spec

if errorlevel 1 (
    echo.
    echo [ERROR] La compilacion fallo. Revisa los mensajes anteriores.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  BUILD EXITOSO
echo  Ejecutable: dist\ADB_Forensic_Helper\ADB_Forensic_Helper.exe
echo ============================================
echo.

:: Abrir carpeta de destino
explorer dist\ADB_Forensic_Helper

pause
