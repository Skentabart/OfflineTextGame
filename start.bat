@echo off
chcp 65001 >nul
setlocal EnableExtensions

title OfflineGame

cd /d "%~dp0"

echo.
echo ============================================
echo              OFFLINE GAME
echo ============================================
echo.
echo Запуск локальной AI...
echo.

if not exist "bin\llama-server.exe" (
    echo.
    echo ОШИБКА:
    echo bin\llama-server.exe не найден.
    echo.
    pause
    exit /b 1
)

if not exist "model\Qwen3-1.7B-Q4_K_M.gguf" (
    echo.
    echo ОШИБКА:
    echo Модель Qwen3-1.7B-Q4_K_M.gguf не найдена.
    echo.
    pause
    exit /b 1
)

if not exist "saves" mkdir saves

echo Проверяю старый AI процесс...

taskkill /F /IM llama-server.exe >nul 2>&1

echo.
echo ============================================
echo        ЗАГРУЗКА ЛОКАЛЬНОЙ МОДЕЛИ
echo ============================================
echo.
echo Модель:
echo Qwen3-1.7B-Q4_K_M.gguf
echo.
echo Запускаю llama-server...
echo.

start "OfflineGame AI" /MIN cmd /c ^
"bin\llama-server.exe ^
-m ""model\Qwen3-1.7B-Q4_K_M.gguf"" ^
--host 127.0.0.1 ^
--port 8080 ^
-c 4096 ^
-t 8 ^
-ngl 0 ^
--jinja ^
--reasoning off"

echo.
echo Жду загрузки модели...
echo.

set SERVER_READY=0

for /L %%i in (1,1,120) do (

    powershell -NoProfile -Command ^
    "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8080/health' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"

    if not errorlevel 1 (
        set SERVER_READY=1
        goto SERVER_OK
    )

    echo Ожидание... %%i/120
    timeout /t 1 /nobreak >nul
)

echo.
echo ============================================
echo       НЕ УДАЛОСЬ ЗАПУСТИТЬ AI
echo ============================================
echo.
echo Проверь:
echo.
echo 1. llama-server.exe
echo 2. GGUF модель
echo 3. доступность порта 8080
echo.
pause
exit /b 1


:SERVER_OK

echo.
echo ============================================
echo       AI МОДЕЛЬ ЗАГРУЖЕНА
echo ============================================
echo.
echo Qwen3 готова к работе.
echo.
echo Сервер:
echo http://127.0.0.1:8080
echo.
echo Запускаю игру...
echo.

python game.py

echo.
echo Игра завершена.
echo.

taskkill /F /IM llama-server.exe >nul 2>&1

pause