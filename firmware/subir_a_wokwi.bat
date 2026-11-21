@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PUERTO=rfc2217://localhost:4000"

rem --- Python: se prefiere el venv del proyecto (..\.venv), si existe ---
rem     Orden: ..\.venv  ->  venv externo viejo  ->  python del PATH
for %%I in ("%~dp0..") do set "RAIZ=%%~fI"
set "PY=python"
if exist "%RAIZ%\.venv\Scripts\python.exe" set "PY=%RAIZ%\.venv\Scripts\python.exe"
if not exist "%RAIZ%\.venv\Scripts\python.exe" if exist "%USERPROFILE%\code\iot\Parcial2_IoT_Seguridad\venv\Scripts\python.exe" set "PY=%USERPROFILE%\code\iot\Parcial2_IoT_Seguridad\venv\Scripts\python.exe"

echo ============================================================
echo  Centinela IoT - subir los 12 modulos al Wokwi de VS Code
echo ============================================================
echo.
echo Esta carpeta YA esta lista: wokwi.toml, diagram.json, los 12 .py
echo y el firmware ESP32_GENERIC-20260824-v1.29.0.bin.
echo.
echo Pasos previos (una sola vez salvo el paso 3):
echo   1. Instalar la extension "Wokwi Simulator" en VS Code.
echo   2. F1 -^> "Wokwi: Request a License"  (licencia gratuita).
echo   3. En VS Code: File -^> Open Folder -^>  %~dp0
echo   4. F1 -^> "Wokwi: Start Simulator"  (o el boton Play del diagram.json)
echo   5. Dejar la pestana de Wokwi VISIBLE: si se oculta, la simulacion
echo      se pausa y el puerto serie no responde.
echo.
echo El filesystem del simulador NO es persistente: cada vez que arrancas
echo la simulacion hay que volver a subir los archivos. Para eso es este .bat.
echo.
pause

rem --- comprobaciones ---
if not exist "wokwi.toml" (
    echo [ERROR] No hay wokwi.toml en esta carpeta.
    pause
    exit /b 1
)
if not exist "diagram.json" (
    echo [ERROR] No hay diagram.json en esta carpeta.
    pause
    exit /b 1
)
if not exist "main.py" (
    echo [ERROR] No hay main.py en esta carpeta.
    pause
    exit /b 1
)
if not exist *.bin (
    echo [ERROR] Falta el firmware de MicroPython ^(*.bin^) en esta carpeta.
    echo Descargalo de https://micropython.org/download/ESP32_GENERIC/
    echo con el nombre que figura en wokwi.toml.
    pause
    exit /b 1
)

"%PY%" -m mpremote --version >nul 2>nul
if errorlevel 1 (
    echo.
    echo [ERROR] mpremote no esta instalado en:
    echo     %PY%
    echo.
    echo Instalalo con:
    echo     "%PY%" -m pip install mpremote
    echo.
    pause
    exit /b 1
)

echo.
echo Python: %PY%
echo Puerto: %PUERTO%
echo.
echo Subiendo los 12 modulos al MicroPython simulado...
echo.

for %%f in (main.py config.py hal.py net.py bus.py fsm.py sensors.py actuators.py display.py ssd1306.py mqtt_client.py app.py) do (
    echo   - %%f
    "%PY%" -m mpremote connect port:%PUERTO% fs cp "%%f" ":%%f"
    if errorlevel 1 (
        echo.
        echo [ERROR] Fallo la subida de %%f.
        echo Revisa:
        echo   - Que la simulacion este corriendo y la pestana de Wokwi visible.
        echo   - Que el puerto 4000 no este ocupado por otro programa.
        echo   - Si dice "could not enter raw repl": clic en la pestana de
        echo     Wokwi, Ctrl+C y despues Ctrl+A, y volve a ejecutar este .bat.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Reiniciando el nodo...
"%PY%" -m mpremote connect port:%PUERTO% reset
if errorlevel 1 (
    echo [AVISO] Los archivos se subieron pero el reset fallo:
    echo         en la pestana de Wokwi presiona Ctrl+D.
)

echo.
echo ============================================================
echo  Listo. En el monitor serie del simulador debe verse:
echo    [centinela] arranque ... firmware 2.0.2
echo    [centinela] OLED listo en 0x3C
echo    [centinela] boton nivel 1
echo    [centinela] latido estado=DISARMED boton=1 mqtt=... alertas=0
echo ============================================================
echo.
echo Ahora: apreta el pulsador verde y espera "ARMADO" en el OLED.
echo Despues: clic en el PIR -^> Simulate Motion.
echo.
pause
