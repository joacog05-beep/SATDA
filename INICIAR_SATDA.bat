@echo off
setlocal
cd /d "%~dp0"
title SATDA - Prototipo institucional
where py >nul 2>nul
if errorlevel 1 (
    set "PYCMD=python"
) else (
    set "PYCMD=py"
)
if not exist ".venv\Scripts\python.exe" (
    echo Preparando entorno virtual de SATDA...
    %PYCMD% -m venv .venv
    if errorlevel 1 (
        echo No se encontro Python. Instale Python 3.11 o superior.
        pause
        exit /b 1
    )
)
echo Instalando o verificando librerias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Error al instalar dependencias. Revise su conexion a Internet.
    pause
    exit /b 1
)
echo Abriendo SATDA en http://localhost:8501 ...
".venv\Scripts\python.exe" -m streamlit run app.py
pause
