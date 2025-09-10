Упрощённый способ установки на Ubuntu Lite:

# 1. Обновление системы
sudo apt update && sudo apt upgrade -y

# 2. Установка зависимостей
sudo apt install -y python3 python3-tk python3-pip python3-venv git imagemagick

# 3. Клонирование репозитория
git clone https://github.com/nikita451451/Sleepmaster/tree/main/linux
cd sleep-scheduler

# 4. Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# 5. Установка Python-зависимостей
pip install customtkinter pyinstaller pillow

# 6. Сборка приложения
pyinstaller --onefile --windowed \
    --name SleepScheduler \
    --add-data "sleep_scheduler.png:." \
    hibernation_scheduler_linux.py

# 7. Копирование в системные директории
sudo mkdir -p /opt/SleepScheduler
sudo cp dist/SleepScheduler /opt/SleepScheduler/
sudo cp sleep_scheduler.png /opt/SleepScheduler/

# 8. Создание команды для запуска
echo '#!/bin/sh
cd /opt/SleepScheduler
./SleepScheduler' | sudo tee /usr/local/bin/sleep-scheduler > /dev/null
sudo chmod +x /usr/local/bin/sleep-scheduler

# 9. Создание ярлыка (.desktop файл)
echo "[Desktop Entry]
Name=Sleep Scheduler
Comment=Управление питанием компьютера
Exec=sleep-scheduler
Icon=/opt/SleepScheduler/sleep_scheduler.png
Terminal=false
Type=Application
Categories=Utility;" | sudo tee /usr/share/applications/sleep-scheduler.desktop > /dev/null

# 10. Завершение
deactivate
echo "Установка завершена! Запустите командой: sleep-scheduler"