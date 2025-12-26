@echo off
REM ========================================
REM EXTRACTOR LOCAL - ALMANSA INFORMA
REM Ejecutar desde Windows
REM ========================================

echo.
echo ====================================
echo EXTRACTOR DE EVENTOS - LOCAL
echo ====================================
echo.

REM Ir a la carpeta del proyecto
cd /d "%~dp0"
cd scripts

echo [1/3] Instalando dependencias...
pip install requests beautifulsoup4 --quiet

echo.
echo [2/3] Extrayendo eventos...
python extractor_eventos_LOCAL.py

echo.
echo [3/3] Subiendo a GitHub...
cd ..
git add eventos_agenda.json
git commit -m "Actualizar eventos - %date% %time%"
git push

echo.
echo ====================================
echo COMPLETADO
echo ====================================
echo.
echo Los eventos se han actualizado en:
echo https://hctop.github.io/almansa-eventos/eventos_agenda.json
echo.
pause
