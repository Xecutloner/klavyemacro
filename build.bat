@echo off
echo KlavyeMacro - EXE Olusturuluyor (--onedir)...
echo.

pyinstaller ^
    --onedir ^
    --windowed ^
    --name "KlavyeMacro" ^
    --add-data "macros.json;." ^
    --add-data "keyboard_guard.py;." ^
    --add-data "webhook_server.py;." ^
    --add-data "ai_helper.py;." ^
    --hidden-import "pystray._win32" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "win32gui" ^
    --hidden-import "win32process" ^
    --hidden-import "psutil" ^
    --hidden-import "keyboard" ^
    --hidden-import "telethon" ^
    --hidden-import "telethon.sessions" ^
    --hidden-import "cryptg" ^
    --hidden-import "urllib.request" ^
    --hidden-import "http.server" ^
    main.py

echo.
if exist "dist\KlavyeMacro\KlavyeMacro.exe" (
    echo [OK] EXE basariyla olusturuldu: dist\KlavyeMacro\KlavyeMacro.exe

    REM Profil klasorunu kopyala
    if exist "profiles" xcopy /E /I /Y "profiles" "dist\KlavyeMacro\profiles" 2>nul

    REM ZIP olustur (kullanici macros.json ve ai_config.json ZIP'e dahil edilmez)
    if exist "dist\KlavyeMacro.zip" del "dist\KlavyeMacro.zip"
    powershell -Command "Compress-Archive -Path 'dist\KlavyeMacro\*' -DestinationPath 'dist\KlavyeMacro.zip' -Force"

    if exist "dist\KlavyeMacro.zip" (
        echo [OK] ZIP olusturuldu: dist\KlavyeMacro.zip
    ) else (
        echo [HATA] ZIP olusturulamadi!
    )
) else (
    echo [HATA] EXE olusturulamadi!
)
pause
