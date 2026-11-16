@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PUERTO=rfc2217://localhost:4000"

echo ============================================================
echo  Centinela IoT - subir modulos al simulador de Wokwi
echo ============================================================
echo.
echo Este .bat SOLO se usa con la extension de Wokwi en VS Code.
echo No se usa en Wokwi web: alla los archivos ya estan en el proyecto.
echo.
echo Antes de ejecutarlo:
echo   1. Abri esta carpeta en VS Code.
echo   2. F1 - Wokwi: Request a new License (solo la primera vez).
echo   3. F1 - Wokwi: Start Simulator.
echo   4. Espera a que la placa arranque y deja la pestana de Wokwi VISIBLE.
echo.
pause

echo.
echo Si la subida falla con "could not enter raw repl":
echo   - Hace clic en la pestana de Wokwi y verifica que este corriendo.
echo   - Presiona Ctrl+C (detiene main.py) y despues Ctrl+A.
echo   - Volve a ejecutar este .bat.
echo.
timeout /t 3 /nobreak >nul

if not exist "wokwi.toml" (
    echo.
    echo [ERROR] No se encontro wokwi.toml en esta carpeta.
    echo Abri la carpeta entregables\Wokwi_Centinela_IoT y ejecuta el .bat desde ahi.
    pause
    exit /b 1
)

if not exist "main.py" (
    echo.
    echo [ERROR] No se encontro main.py en esta carpeta.
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo [ERROR] No se encontro Python en el PATH.
    pause
    exit /b 1
)

python -m mpremote --version >nul 2>nul
if errorlevel 1 (
    echo.
    echo [ERROR] mpremote no esta instalado.
    echo Instalalo con:  pip install mpremote
    pause
    exit /b 1
)

echo.
echo Subiendo los 12 modulos al MicroPython simulado...
echo.

for %%f in (main.py config.py hal.py net.py bus.py fsm.py sensors.py actuators.py display.py ssd1306.py mqtt_client.py app.py) do (
    echo Subiendo %%f ...
    python -m mpremote connect port:%PUERTO% fs cp "%%f" ":%%f"
    if errorlevel 1 (
        echo.
        echo [ERROR] Fallo la subida de %%f.
        echo Revisa:
        echo   - La simulacion esta corriendo y la pestana de Wokwi visible.
        echo   - El puerto 4000 no esta ocupado.
        echo   - mpremote instalado: pip install mpremote
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Reiniciando el nodo...
python -m mpremote connect port:%PUERTO% reset
if errorlevel 1 (
    echo.
    echo [AVISO] Los archivos se subieron, pero el reset fallo.
    echo Proba Ctrl+D en la pestana de Wokwi o reinicia la simulacion.
)

echo.
echo Listo: mira el OLED y el monitor serie.
echo Si el OLED queda negro, revisa que SDA este en GPIO21 y SCL en GPIO22.
pause
