@echo off
REM ============================================================
REM  TPEsystem — Script de inicio en producción
REM  Ejecutar como Administrador la primera vez
REM ============================================================
cd /d C:\proyectos\TPEsystem

REM Activar entorno virtual (ajusta la ruta si es diferente)
call venv\Scripts\activate.bat

REM Recolectar archivos estáticos (solo si hubo cambios)
REM python manage.py collectstatic --noinput

REM Iniciar servidor Waitress en puerto 8080
REM --threads=4 es suficiente para 19 usuarios
waitress-serve --host=0.0.0.0 --port=8080 --threads=4 config.wsgi:application
