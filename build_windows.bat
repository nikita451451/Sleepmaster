@echo off
echo Установка зависимостей...
pip install pyinstaller pillow tk

echo Очистка предыдущих сборок...
rd /s /q dist
rd /s /q build
del hibernation_scheduler.spec 2>nul

echo Сборка приложения...
pyinstaller --onefile --windowed --icon=sleep_scheduler.ico --clean --noconfirm hibernation_scheduler.py

echo Копирование иконки...
copy sleep_scheduler.ico dist\ 1>nul

echo Сборка завершена! Исполняемый файл в папке dist
pause