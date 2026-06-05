@echo off
chcp 65001 >nul
echo =============================================
echo   KlavyeMacro v1.2.0 Kurulum Scripti
echo =============================================
echo.

set INSTALL_DIR=%LOCALAPPDATA%\KlavyeMacro
set DESKTOP=%USERPROFILE%\Desktop
set STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs
set ZIP_PATH=%~dp0KlavyeMacro.zip

REM ZIP dosyasi mevcut mu?
if not exist "%ZIP_PATH%" (
    echo [HATA] KlavyeMacro.zip bu scriptle ayni klasorde olmali!
    echo Lutfen GitHub'dan KlavyeMacro.zip ve install.bat'i
    echo ayni klasore indirin.
    pause
    exit /b 1
)

echo [1] Kurulum klasoru olusturuluyor: %INSTALL_DIR%
mkdir "%INSTALL_DIR%" 2>nul

echo [2] Dosyalar kopyalaniyor...
REM Eski KlavyeMacro klasorunu temizle (macros.json hariç)
if exist "%INSTALL_DIR%\KlavyeMacro.exe" (
    echo     Mevcut kurulum guncelleniyor...
    REM Kullanici verilerini yedekle
    if exist "%INSTALL_DIR%\macros.json" copy "%INSTALL_DIR%\macros.json" "%TEMP%\km_macros_backup.json" >nul
    if exist "%INSTALL_DIR%\ai_config.json" copy "%INSTALL_DIR%\ai_config.json" "%TEMP%\km_config_backup.json" >nul
)

REM ZIP'i cikart
powershell -Command "Expand-Archive -Path '%ZIP_PATH%' -DestinationPath '%INSTALL_DIR%' -Force"
if errorlevel 1 (
    echo [HATA] ZIP acilamadi!
    pause
    exit /b 1
)
echo     OK

REM Kullanici verilerini geri yukle
if exist "%TEMP%\km_macros_backup.json" (
    copy "%TEMP%\km_macros_backup.json" "%INSTALL_DIR%\macros.json" >nul
    del "%TEMP%\km_macros_backup.json" >nul
    echo     Makrolar korundu.
)
if exist "%TEMP%\km_config_backup.json" (
    copy "%TEMP%\km_config_backup.json" "%INSTALL_DIR%\ai_config.json" >nul
    del "%TEMP%\km_config_backup.json" >nul
    echo     Ayarlar korundu.
)

if not exist "%INSTALL_DIR%\KlavyeMacro.exe" (
    echo [HATA] Kurulum basarisiz - EXE bulunamadi!
    pause
    exit /b 1
)

echo [3] Masaustu kisayolu olusturuluyor...
powershell -Command "$s=New-Object -ComObject WScript.Shell; $sc=$s.CreateShortcut('%DESKTOP%\KlavyeMacro.lnk'); $sc.TargetPath='%INSTALL_DIR%\KlavyeMacro.exe'; $sc.WorkingDirectory='%INSTALL_DIR%'; $sc.Description='KlavyeMacro - Klavye Makro Uygulamasi'; $sc.Save()" 2>nul
echo     OK

echo [4] Baslat Menusu kisayolu olusturuluyor...
mkdir "%STARTMENU%\KlavyeMacro" 2>nul
powershell -Command "$s=New-Object -ComObject WScript.Shell; $sc=$s.CreateShortcut('%STARTMENU%\KlavyeMacro\KlavyeMacro.lnk'); $sc.TargetPath='%INSTALL_DIR%\KlavyeMacro.exe'; $sc.WorkingDirectory='%INSTALL_DIR%'; $sc.Description='KlavyeMacro - Klavye Makro Uygulamasi'; $sc.Save()" 2>nul
echo     OK

echo.
echo =============================================
echo   KURULUM TAMAMLANDI!
echo =============================================
echo.
echo   Konum : %INSTALL_DIR%
echo   Kisayol: Masaustu ^> KlavyeMacro
echo.
echo   NOT: DLL hatasi aldiysan bu installer sayesinde
echo        uygulama AppData'ya kurulur - Defender
echo        o klasoru Downloads gibi taramaz.
echo.

set /p LAUNCH="Uygulama simdi acilsin mi? (E/H): "
if /i "%LAUNCH%"=="E" (
    start "" /D "%INSTALL_DIR%" "%INSTALL_DIR%\KlavyeMacro.exe"
)
