@echo off
chcp 65001 >nul
setlocal EnableExtensions

title OfflineGame Setup

cd /d "%~dp0"

echo.
echo ============================================
echo          OFFLINE GAME - SETUP
echo ============================================
echo.
echo Этот установщик подготовит:
echo.
echo  1. llama.cpp
echo  2. локальную GGUF модель Qwen3 1.7B
echo.
echo После установки игра не требует интернета.
echo.
echo ============================================
echo.

if not exist "bin" mkdir bin
if not exist "model" mkdir model
if not exist "saves" mkdir saves

echo.
echo [1/3] Проверка Python...

where python >nul 2>nul

if errorlevel 1 (
    echo.
    echo Python не найден.
    echo Установи Python 3.11+.
    echo.
    pause
    exit /b 1
)

python --version

echo.
echo [2/3] Загрузка llama.cpp...
echo.

if exist "bin\llama-cli.exe" (

    echo llama-cli.exe уже существует.
    goto MODEL

)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$url='https://github.com/ggml-org/llama.cpp/releases/latest/download/llama-b-bin-win-cpu-x64.zip'; ^
$out='llama.zip'; ^
Write-Host 'Downloading llama.cpp...'; ^
Invoke-WebRequest -Uri $url -OutFile $out; ^
Write-Host 'Download complete.'"

if not exist "llama.zip" (

    echo.
    echo Не удалось скачать llama.cpp.
    echo.
    echo Открой:
    echo https://github.com/ggml-org/llama.cpp/releases
    echo.
    echo И скачай Windows x64 CPU архив.
    echo.
    pause
    exit /b 1
)

echo.
echo Распаковка llama.cpp...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"Expand-Archive -Path 'llama.zip' -DestinationPath 'bin\llama_temp' -Force"

echo Поиск llama-cli.exe...

for /r "bin\llama_temp" %%F in (llama-cli.exe) do (
    copy /Y "%%F" "bin\llama-cli.exe" >nul
    goto LLAMA_FOUND
)

echo.
echo llama-cli.exe не найден внутри архива.
echo.
pause
exit /b 1

:LLAMA_FOUND

echo llama-cli.exe установлен.

rmdir /s /q "bin\llama_temp" 2>nul
del /q "llama.zip" 2>nul


:MODEL

echo.
echo [3/3] Проверка модели...
echo.

if exist "model\Qwen3-1.7B-Q4_K_M.gguf" (

    echo Модель уже установлена.
    goto FINISH

)

echo.
echo Будет загружена:
echo.
echo Qwen3 1.7B Q4_K_M
echo Размер примерно 1.28 GB
echo.
echo Источник:
echo ggml-org/Qwen3-1.7B-GGUF
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$url='https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf?download=true'; ^
$out='model\Qwen3-1.7B-Q4_K_M.gguf'; ^
Write-Host 'Downloading model...'; ^
Invoke-WebRequest -Uri $url -OutFile $out; ^
Write-Host 'Model download complete.'"

if not exist "model\Qwen3-1.7B-Q4_K_M.gguf" (

    echo.
    echo Ошибка загрузки модели.
    echo.
    pause
    exit /b 1
)


:FINISH

echo.
echo ============================================
echo              SETUP COMPLETE
echo ============================================
echo.
echo llama.cpp:
if exist "bin\llama-cli.exe" (
    echo OK
) else (
    echo ERROR
)

echo.
echo Model:
if exist "model\Qwen3-1.7B-Q4_K_M.gguf" (
    echo OK
) else (
    echo ERROR
)

echo.
echo Теперь можно запускать:
echo.
echo     start.bat
echo.
echo После завершения установки интернет игре
echo больше не нужен.
echo.
echo ============================================
echo.

pause