@echo off
setlocal

echo Установка Sleep Scheduler для Windows
echo.

set "INSTALL_DIR=%ProgramFiles%\SleepScheduler"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\Sleep Scheduler.lnk"

echo Создание папки установки...
mkdir "%INSTALL_DIR%" 2>nul

echo Копирование файлов...
xcopy /Y /E "dist\hibernation_scheduler.exe" "%INSTALL_DIR%"
xcopy /Y "sleep_scheduler.ico" "%INSTALL_DIR%"

echo Создание ярлыка на рабочем столе...
set "PS_CMD="$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%INSTALL_DIR%\hibernation_scheduler.exe'; $s.IconLocation = '%INSTALL_DIR%\sleep_scheduler.ico'; $s.Save()""
powershell -Command %PS_CMD%

echo Добавление в автозапуск...
set "REG_ADD=reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v SleepScheduler /t REG_SZ /d \"%INSTALL_DIR%\hibernation_scheduler.exe\" /f"
%REG_ADD%

echo Установка завершена!
echo Запустите приложение с рабочего стола
pause