@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo Python Launcher ^(py^) nao foi encontrado. Instale Python 3.10 ou superior.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    py -m venv .venv
    if errorlevel 1 goto erro
)

echo Instalando/verificando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto erro

echo Iniciando VitaPulse em http://127.0.0.1:5000
".venv\Scripts\python.exe" app.py
pause
exit /b 0

:erro
echo Ocorreu um erro ao preparar o VitaPulse. Confira a mensagem acima.
pause
exit /b 1
