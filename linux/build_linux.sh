#!/bin/bash
echo "Сборка Sleep Scheduler для Linux..."
echo

cd "$(dirname "$0")"

# Создаем виртуальное окружение
python3 -m venv venv
source venv/bin/activate

echo "Установка зависимостей..."
pip install customtkinter pillow pyinstaller

echo "Сборка приложения..."
pyinstaller \
    --name=SleepScheduler \
    --onefile \
    --windowed \
    --clean \
    --add-data="sleep_scheduler.png:." \
    --hidden-import=tcl \
    --hidden-import=tk \
    hibernation_scheduler_linux.py

cp sleep_scheduler.png dist/ 
echo
echo "✅ Сборка завершена!"
echo "📁 Файл: dist/SleepScheduler"
echo "🔧 Дайте права на выполнение: chmod +x dist/SleepScheduler"
echo