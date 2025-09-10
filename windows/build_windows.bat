@echo off
echo Сборка TimeMaster для Windows...
cd /d %~dp0

pip install -r requirements.txt

pyinstaller ^
    --name=TimeMaster ^
    --windowed ^
    --hidden-import=tkinter ^
    --hidden-import=PIL ^
    --hidden-import=PIL._tkinter_finder ^
    --collect-all=customtkinter ^
    --collect-all=PIL ^
    --icon=assets/sleep_icon.ico ^
    --add-data="assets;assets" ^
    --onefile ^
    --clean ^
    --noconsole ^
    src/hibernation_scheduler_windows.py

echo Сборка завершена! Файл: dist\TimeMaster.exe
pause