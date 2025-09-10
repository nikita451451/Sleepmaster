#!/bin/bash
cd "$(dirname "$0")"

# Проверка прав root
if [ "$(id -u)" -ne 0 ]; then
    echo "Запуск с правами root..."
    exec sudo "$0" "$@"
fi

# Установка зависимостей
apt update
apt install -y python3 python3-tk python3-pip python3-venv

# Создание венвирутального окружения
python3 -m venv venv
source venv/bin/activate
pip install customtkinter pyinstaller pillow

# Сборка приложения
pyinstaller sleep_scheduler.spec

# Установка в систему
INSTALL_DIR="/opt/SleepScheduler"
mkdir -p "$INSTALL_DIR"
cp dist/SleepScheduler/* "$INSTALL_DIR/"

# Создание команды запуска
echo '#!/bin/sh
cd /opt/SleepScheduler
./SleepScheduler' > /usr/local/bin/sleep-scheduler
chmod +x /usr/local/bin/sleep-scheduler

echo "Установка завершена! Запуск: sleep-scheduler"