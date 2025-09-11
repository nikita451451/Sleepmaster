#!/bin/bash
# Установщик для Linux

APP_NAME="SleepScheduler"
INSTALL_DIR="/opt/$APP_NAME"
BIN_PATH="/usr/local/bin/sleep-scheduler"
DESKTOP_FILE="/usr/share/applications/sleep-scheduler.desktop"

# Проверка прав
if [ "$EUID" -ne 0 ]; then
    echo "Запуск с правами sudo!"
    exec sudo "$0"
    exit
fi

# Создать папки
mkdir -p $INSTALL_DIR

# Копировать файлы
cp hibernation_scheduler_linux.py "$INSTALL_DIR/"
cp sleep_scheduler.png "$INSTALL_DIR/" 2>/dev/null || true

# Установщик зависимостей
apt install -y python3-pip python3-tk
pip3 install customtkinter pillow

# Создать скрипт запуска
echo '#!/bin/sh
cd /opt/SleepScheduler
exec sudo python3 hibernation_scheduler_linux.py' > $BIN_PATH
chmod +x $BIN_PATH

# Создать ярлык .desktop
echo "[Desktop Entry]
Name=Sleep Scheduler
Comment=Планировщик управления питанием
Exec=$BIN_PATH
Icon=$INSTALL_DIR/sleep_scheduler.png
Terminal=false
Type=Application
Categories=Utility;" > $DESKTOP_FILE

echo "Установлена! Используйте команду: sleep-scheduler"