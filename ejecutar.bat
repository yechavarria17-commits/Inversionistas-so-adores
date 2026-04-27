@echo off
echo Instalando dependencias...
pip install -r requirements.txt
echo.
echo Iniciando servidor...
echo Abre tu navegador en: http://localhost:5000
echo.
python app.py
pause
