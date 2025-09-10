#!/bin/bash
# Полный скрипт установки Sleep Scheduler для Linux

# Проверка запуска с правами sudo
if [ "$EUID" -ne 0 ]; then
    echo "Этот скрипт требует прав администратора. Пожалуйста, запустите с sudo:"
    echo "  sudo $0"
    exit 1
fi

# Параметры установки
APP_NAME="SleepScheduler"
INSTALL_DIR="/opt/$APP_NAME"
BIN_PATH="/usr/local/bin/sleep-scheduler"
DESKTOP_FILE="/usr/share/applications/sleep-scheduler.desktop"
REPO_URL="https://github.com/username/sleep-scheduler.git"
ICON_URL="https://raw.githubusercontent.com/username/sleep-scheduler/main/sleep_scheduler.png"

echo "┌─────────────────────────────────────────┐"
echo "│ Установка Sleep Scheduler для Linux     │"
echo "└─────────────────────────────────────────┘"

# Установка системных зависимостей
echo "[1/6] Установка системных зависимостей..."
apt update > /dev/null
DEBIAN_FRONTEND=noninteractive apt install -y -q \
    python3 \
    python3-venv \
    python3-pip \
    python3-pil \
    python3-tk > /dev/null

# Создание временной директории
echo "[2/6] Подготовка файлов..."
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

# Загрузка иконки
echo "[3/6] Загрузка иконки приложения..."
if ! wget -q "$ICON_URL" -O sleep_scheduler.png; then
    echo "Используем встроенную иконку..."
    cat > generate_icon.py << 'EOF'
from PIL import Image, ImageDraw
img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.ellipse((25, 25, 230, 230), fill='#4d94ff', outline='white')
draw.ellipse((75, 75, 180, 180), fill='#f0f8ff', outline='white')
draw.polygon([(128, 100), (155, 160), (145, 160), (128, 130), (111, 160), (101, 160)], fill='#4d94ff')
img.save('sleep_scheduler.png')
EOF
    python3 generate_icon.py
fi

# Клонирование и сборка приложения
echo "[4/6] Сборка приложения..."
git clone -q "$REPO_URL" source || { echo "Ошибка клонирования репозитория!"; exit 1; }
cd source

python3 -m venv venv
source venv/bin/activate

pip install -U pip > /dev/null
pip install customtkinter pyinstaller > /dev/null

pyinstaller --onefile --windowed \
    --name "$APP_NAME" \
    --add-data "../sleep_scheduler.png:." \
    --hidden-import=tcl \
    --hidden-import=tk \
    hibernation_scheduler_linux.py

# Установка приложения
echo "[5/6] Системная установка..."
mkdir -p "$INSTALL_DIR"
cp "dist/$APP_NAME" "$INSTALL_DIR/"
cp "../sleep_scheduler.png" "$INSTALL_DIR/"

# Создание исполняемого файла
cat > "$INSTALL_DIR/run.sh" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
exec "$INSTALL_DIR/$APP_NAME"
EOF
chmod +x "$INSTALL_DIR/run.sh"

# Создание команды терминала
echo "sudo -u \$(logname) \"$INSTALL_DIR/run.sh\"" > "$BIN_PATH"
chmod +x "$BIN_PATH"

# Создание .desktop файла
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=Sleep Scheduler
Comment=Планировщик спящего режима
Exec=$BIN_PATH
Icon=$INSTALL_DIR/sleep_scheduler.png
Terminal=false
Type=Application
Categories=Utility;
Keywords=power;sleep;scheduler;
EOF

# Автозагрузка для пользователей
echo "[6/6] Настройка автозапуска..."
for USER_DIR in /home/*; do
    USER="$(basename "$USER_DIR")"
    USER_AUTOSTART="/home/$USER/.config/autostart"
    
    if [ -d "/home/$USER" ]; then
        mkdir -p "$USER_AUTOSTART"
        cp "$DESKTOP_FILE" "$USER_AUTOSTART/"
        chown "$USER":"$USER" "$USER_AUTOSTART/sleep-scheduler.desktop"
    fi
done

# Добавление пользователя в группу администраторов
echo "Добавление пользователей в группу sudoers..."
for USER_DIR in /home/*; do
    USER="$(basename "$USER_DIR")"
    if [ -d "/home/$USER" ]; then
        if ! groups "$USER" | grep -q '\bsudo\b'; then
            usermod -aG sudo "$USER"
        fi
    fi
done

# Очистка
cd ..
rm -rf "$TMP_DIR"

echo "──────────────────────────────────────────────────"
echo " Установка успешно завершена!"
echo "──────────────────────────────────────────────────"
echo " Для запуска используйте команду:"
echo "   sleep-scheduler"
echo " или найдите 'Sleep Scheduler' в меню приложений"
echo "──────────────────────────────────────────────────"
echo " Файлы установлены в: $INSTALL_DIR"
echo " Автозапуск настроен для всех пользователей"
echo "──────────────────────────────────────────────────"