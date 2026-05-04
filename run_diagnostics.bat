@echo off
REM Script para ejecutar el servidor con diagnósticos de sesión activados

echo Iniciando servidor Django con diagnósticos de sesión...
echo.
echo Los logs aparecerán en la consola para diagnosticar el problema paso3.
echo.

python manage.py runserver 127.0.0.1:8000 --verbosity=2

pause
