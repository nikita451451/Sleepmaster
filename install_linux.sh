#!/bin/bash

echo "Установка Sleep Scheduler для Linux"
echo

INSTALL_DIR="/opt/sleep-scheduler"
APPS_DIR="$HOME/.local/share/applications"
EXEC_PATH="$(pwd)/dist/hibernation_scheduler"

# Создание директории установки
sudo mkdir -p $INSTALL_DIR

# Копирование файлов
sudo cp dist/hibernation_scheduler $INSTALL_DIR/
sudo cp sleep_scheduler.png $INSTALL_DIR/

# Создание десктоп-файла
DESKTOP_FILE="$APPS_DIR/sleep-scheduler.desktop"
mkdir -p "$APPS_DIR"

cat > "$DESKTOP_FILE" <<EOL
[Desktop Entry]
Name=Sleep Scheduler
Comment=Планировщик спящего режима
Exec=$INSTALL_DIR/hibernation_scheduler
Icon=$INSTALL_DIR/sleep_scheduler.png
Terminal=false
Type=Application
Categories=Utility;
Keywords=sleep;hibernate;scheduler;
EOL

# Создание симлинка для запуска из терминала
sudo ln -sf "$INSTALL_DIR/hibernation_scheduler" /usr/local/bin/sleep-scheduler

# Настройка автозапуска
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
cp "$DESKTOP_FILE" "$AUTOSTART_DIR/"

echo "Установка завершена!"
echo "Приложение добавлено в меню программ и будет запускаться автоматически"