@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale Python 3.11 ou superior.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto erro
python -m pip install -r requirements.txt
if errorlevel 1 goto erro
python configurar_bot.py
if errorlevel 1 goto erro
python bot.py
if errorlevel 1 goto erro
exit /b 0
:erro
echo.
echo Ocorreu um erro. Confira as mensagens acima e o arquivo .env.
pause
exit /b 1
