@echo off
echo ============================================================
echo 🚀 HH.ru Parser - Quick Start
echo ============================================================
echo.

REM Активация виртуального окружения (если есть)
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Проверка зависимостей
echo Checking dependencies...
pip install -r requirements.txt --quiet

REM Запуск приложения
echo.
echo Starting HH Parser...
echo.
python run.py

pause
