@echo off
rem Construye la carpeta portable dist\UDI.
rem Se ejecuta en una PC con Windows y Python 3.10 o mas nuevo (no en la tableta).
setlocal
cd /d "%~dp0.."

if not exist .venv py -3 -m venv .venv
if errorlevel 1 goto error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
if errorlevel 1 goto error

echo.
echo === Pruebas ===
python -m pytest -q
if errorlevel 1 goto error

set ENTRADA=main.py
set MODO=--windowed
if exist main.py goto empaquetar
set ENTRADA=despliegue\main_de_prueba.py
set MODO=--console
echo AVISO: no hay main.py del frontend. Se construye la version de prueba.

:empaquetar
echo.
echo === Empaquetado ===
pyinstaller --noconfirm --clean --onedir %MODO% --name UDI --paths . %ENTRADA%
if errorlevel 1 goto error

echo.
echo Listo. Copia la carpeta dist\UDI completa a la tableta.
exit /b 0

:error
echo.
echo ALGO FALLO. Revisa los mensajes de arriba. No copies nada a la tableta.
exit /b 1
