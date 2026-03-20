@echo off
:: ============================================================
::  backup_tpe.bat — Backup diario de base de datos TPE/TSP
::  Guarda el .sql en OneDrive automáticamente
::  Ejecutar al terminar el trabajo cada día
:: ============================================================

:: --- CONFIGURACIÓN — ajusta estos valores en cada PC ---
set DB_USER=root
set DB_NAME=db_sumarios_militares
set DB_HOST=127.0.0.1
set DB_PORT=3306

:: Carpeta de destino en OneDrive — cambia el path según tu PC
set ONEDRIVE=C:\Users\%USERNAME%\OneDrive\backups_tpe

:: Path de mysqldump — ajusta si MySQL está en otra ruta
set MYSQLDUMP="C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"

:: --- NO MODIFICAR DESDE AQUÍ ---
:: Construir fecha en formato YYYYMMDD
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set DT=%%I
set FECHA=%DT:~0,4%%DT:~4,2%%DT:~6,2%
set HORA=%DT:~8,2%%DT:~10,2%

set ARCHIVO=backup_%FECHA%_%HORA%.sql

:: Crear carpeta de backups si no existe
if not exist "%ONEDRIVE%" (
    mkdir "%ONEDRIVE%"
    echo [OK] Carpeta creada: %ONEDRIVE%
)

:: Mensaje de inicio
echo.
echo ============================================================
echo  BACKUP TPE/TSP — %DATE% %TIME%
echo ============================================================
echo  Base de datos : %DB_NAME%
echo  Destino       : %ONEDRIVE%\%ARCHIVO%
echo.

:: Solicitar password de MySQL
set /p DB_PASS=Ingresa la contraseña de MySQL (root): 

:: Ejecutar el backup
echo.
echo Generando backup...
%MYSQLDUMP% -h %DB_HOST% -P %DB_PORT% -u %DB_USER% -p%DB_PASS% %DB_NAME% > "%ONEDRIVE%\%ARCHIVO%"

:: Verificar si se generó correctamente
if %ERRORLEVEL% == 0 (
    echo.
    echo [OK] Backup completado exitosamente
    echo [OK] Archivo: %ONEDRIVE%\%ARCHIVO%

    :: Mostrar tamaño del archivo
    for %%F in ("%ONEDRIVE%\%ARCHIVO%") do echo [OK] Tamaño: %%~zF bytes

    :: Eliminar backups con más de 30 días para no llenar OneDrive
    echo.
    echo Limpiando backups antiguos (más de 30 días)...
    forfiles /p "%ONEDRIVE%" /s /m backup_*.sql /d -30 /c "cmd /c del @path" 2>nul
    echo [OK] Limpieza completada

) else (
    echo.
    echo [ERROR] El backup falló. Verifica:
    echo   - Que MySQL esté corriendo
    echo   - Que la contraseña sea correcta
    echo   - Que el path de mysqldump sea correcto:
    echo     %MYSQLDUMP%
)

echo.
echo ============================================================
echo  Recuerda hacer git push antes de cerrar el proyecto
echo    git add .
echo    git commit -m "wip: avance del dia %FECHA%"
echo    git push origin main
echo ============================================================
echo.
pause
