#!/bin/bash
echo "┌─────────────────────────────────────────┐"
echo "│ Установка Sleep Scheduler для Linux     │"
echo "└─────────────────────────────────────────┘"

if [ "$EUID" -ne 0 ]; then
    exec sudo "$0"
    exit
fi

APP_NAME="SleepScheduler"
INSTALL_DIR="/opt/$APP_NAME"
BIN_PATH="/usr/local/bin/sleep-scheduler"
DESKTOP_FILE="/usr/share/applications/sleep-scheduler.desktop"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "> Установка системных зависимостей..."
sudo apt update -y
sudo apt install -y \
    python3 \
    python3-pip \
    python3-tk \
    python3-pil.imagetk \
    policykit-1 \
    libxcb-xinerama0 \
    imagemagick

echo "> Создание директорий..."
sudo mkdir -p "$INSTALL_DIR"
sudo chmod 755 "$INSTALL_DIR"

echo "> Копирование файлов..."
sudo cp "$SCRIPT_DIR/hibernation_scheduler_linux.py" "$INSTALL_DIR/"

# Создаём иконку, если её нет
if [ -f "$SCRIPT_DIR/sleep_scheduler.png" ]; then
    sudo cp "$SCRIPT_DIR/sleep_scheduler.png" "$INSTALL_DIR/"
else
    echo "Создание временной иконки..."
    sudo convert -size 256x256 xc:#1e88e5 \
        -fill '#0d47a1' -draw 'circle 128,128 90,200' \
        "$INSTALL_DIR/sleep_scheduler.png"
fi

echo "> Установка Python-зависимостей..."
sudo -H pip3 install customtkinter pillow

echo "> Создание скриптов..."
sudo tee "$BIN_PATH" > /dev/null << EOF
#!/bin/bash
cd /opt/SleepScheduler
exec pkexec python3 hibernation_scheduler_linux.py "\$@"
EOF
sudo chmod +x "$BIN_PATH"

sudo tee "$DESKTOP_FILE" > /dev/null << EOF
[Desktop Entry]
Name=Sleep Scheduler
Comment=Планировщик управления питанием
Exec=sleep-scheduler
Icon=$INSTALL_DIR/sleep_scheduler.png
Terminal=false
Type=Application
Categories=Utility;
EOF

echo -e "\033[1;32mУспешно установлено!\033[0m"
echo "Запуск: sleep-scheduler"
echo "Или через меню приложений"