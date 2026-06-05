@echo off
echo KlavyeMacro - EXE Olusturuluyor...
echo.

pyinstaller ^
    --onefile ^
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
if exist "dist\KlavyeMacro.exe" (
    echo [OK] EXE basariyla olusturuldu: dist\KlavyeMacro.exe
    copy "macros.json" "dist\macros.json" 2>nul
    if exist "profiles" xcopy /E /I "profiles" "dist\profiles" 2>nul
    if exist "ai_config.json" copy "ai_config.json" "dist\ai_config.json" 2>nul
    echo [OK] Dosyalar dist klasorune kopyalandi.
) else (
    echo [HATA] EXE olusturulamadi!
)
pause
