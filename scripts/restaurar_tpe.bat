@echo off
:: ============================================================
::  restaurar_tpe.bat — Restaurar backup de BD en otra PC
::  Usar al llegar a una nueva computadora con el .sql de OneDrive
:: ============================================================

:: --- CONFIGURACIÓN ---
set DB_USER=root
set DB_NAME=db_sumarios_militares
set DB_HOST=127.0.0.1
set DB_PORT=3306
set ONEDRIVE=C:\Users\%USERNAME%\OneDrive\backups_tpe
set MYSQL="C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"

echo.
echo ============================================================
echo  RESTAURAR BACKUP TPE/TSP
echo ============================================================
echo.

:: Listar backups disponibles en OneDrive
echo Backups disponibles en %ONEDRIVE%:
echo.
dir "%ONEDRIVE%\backup_*.sql" /b /o-d 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] No se encontraron backups en %ONEDRIVE%
    pause
    exit /b 1
)

echo.
set /p ARCHIVO=Escribe el nombre del archivo a restaurar (ej: backup_20260320_1800.sql): 
set /p DB_PASS=Ingresa la contraseña de MySQL (root): 

if not exist "%ONEDRIVE%\%ARCHIVO%" (
    echo.
    echo [ERROR] Archivo no encontrado: %ONEDRIVE%\%ARCHIVO%
    pause
    exit /b 1
)

echo.
echo Restaurando %ARCHIVO% en la base de datos %DB_NAME%...
echo ADVERTENCIA: Esto reemplazará todos los datos actuales.
set /p CONFIRMAR=¿Continuar? (S/N): 

if /i "%CONFIRMAR%" neq "S" (
    echo Operación cancelada.
    pause
    exit /b 0
)

%MYSQL% -h %DB_HOST% -P %DB_PORT% -u %DB_USER% -p%DB_PASS% %DB_NAME% < "%ONEDRIVE%\%ARCHIVO%"

if %ERRORLEVEL% == 0 (
    echo.
    echo [OK] Base de datos restaurada correctamente
    echo [OK] Desde: %ARCHIVO%
) else (
    echo.
    echo [ERROR] La restauración falló. Verifica la contraseña y que MySQL esté activo.
)

echo.
pause
