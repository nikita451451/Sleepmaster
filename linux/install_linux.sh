#!/bin/bash
# Universal Installer for Linux

echo "┌─────────────────────────────────────────┐"
echo "│ Установка Sleep Scheduler для Linux     │"
echo "└─────────────────────────────────────────┘"

# Проверка прав
if [ "$EUID" -ne 0 ]; then
    echo "> Этот скрипт требует прав администратора."
    echo "> Пожалуйста, запустите через sudo:"
    echo -e "\033[1;31m  sudo $0\033[0m"
    exit 1
fi

# Параметры установки
APP_NAME="SleepScheduler"
INSTALL_DIR="/opt/$APP_NAME"
BIN_PATH="/usr/local/bin/sleep-scheduler"
DESKTOP_FILE="/usr/share/applications/sleep-scheduler.desktop"

# Установка зависимостей
echo "> Установка системных зависимостей..."
apt update -y
apt install -y \
    python3 \
    python3-pip \
    python3-tk \
    python3-pil \
    policykit-1 \
    libxcb-xinerama0

# Создание директории приложения
echo "> Создание директорий..."
mkdir -p "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR"

# Копирование файлов
echo "> Копирование файлов..."
cp hibernation_scheduler_linux.py "$INSTALL_DIR/"
cp sleep_scheduler.png "$INSTALL_DIR/"

# Установка Python-зависимостей
echo "> Установка pip-пакетов..."
pip3 install customtkinter pillow

# Создание исполняемого файла
echo "> Создание скрипта запуска..."
tee "$BIN_PATH" > /dev/null << EOF
#!/bin/bash
cd "$INSTALL_DIR"
exec pkexec python3 hibernation_scheduler_linux.py "\$@"
EOF
chmod +x "$BIN_PATH"

# Создание .desktop файла
echo "> Создание ярлыка приложения..."
tee "$DESKTOP_FILE" > /dev/null << EOF
[Desktop Entry]
Name=Sleep Scheduler
Comment=Планировщик управления питанием
Exec=sleep-scheduler
Icon=$INSTALL_DIR/sleep_scheduler.png
Terminal=false
Type=Application
Categories=Utility;
Keywords=power;sleep;scheduler;
EOF

# Настройка разрешений
echo "> Настройка прав доступа..."
chown -R root:root "$INSTALL_DIR"
chmod 755 "$BIN_PATH"

echo -e "\033[1;32m
Установка успешно завершена!
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Команда для запуска: 
  $ sleep-scheduler

Или найдите \"Sleep Scheduler\" в меню приложений

При первом запуске потребуется ввести пароль
для предоставления прав администратора
\033[0m"