#!/bin/bash
# Скрипт установки Sleep Scheduler с USB-флешки (полная версия)

# Определяем путь к скрипту (даже при запуске с флешки)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Проверка запуска с правами sudo
if [ "$(id -u)" != "0" ]; then
    # Перезапуск с sudo
    exec sudo "$0" "$SCRIPT_DIR" "$@"
fi

# Если запустили с правами root, получаем путь к скрипту из первого аргумента
if [ -n "$1" ]; then
    SCRIPT_DIR="$1"
fi

echo -e "\033[1;34m"
echo "┌─────────────────────────────────────────────┐"
echo "│ Установка Sleep Scheduler с USB-флешки      │"
echo "└─────────────────────────────────────────────┘"
echo -e "\033[0m"

# Проверка наличия файла проекта
APP_EXISTS=$(ls "$SCRIPT_DIR"/*scheduler*.py 2> /dev/null | wc -l)
if [ "$APP_EXISTS" -eq 0 ]; then
    echo -e "\033[1;31mОШИБКА: Файлы приложения не найдены!\033[0m"
    echo "Убедитесь что на флешке есть файлы:"
    echo "  - hibernation_scheduler_linux.py"
    echo "  - sleep_scheduler.png (опционально)"
    echo "Скрипт запущен из: $SCRIPT_DIR"
    exit 1
fi

# Параметры установки
APP_NAME="SleepScheduler"
INSTALL_DIR="/opt/$APP_NAME"
BIN_PATH="/usr/local/bin/sleep-scheduler"
DESKTOP_FILE="/usr/share/applications/sleep-scheduler.desktop"

# Установка системных зависимостей
echo "[1/6] Проверка зависимостей..."
if ! command -v python3 > /dev/null; then
    apt update > /dev/null
    DEBIAN_FRONTEND=noninteractive apt install -y -q \
        python3 \
        python3-venv \
        python3-pip \
        python3-pil \
        python3-tk > /dev/null
fi

# Создание временной директории
echo "[2/6] Подготовка файлов..."
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

# Копирование файлов с флешки
echo "[3/6] Копирование файлов программы..."
cp "$SCRIPT_DIR"/*scheduler*.py ./
[ -f "$SCRIPT_DIR/sleep_scheduler.png" ] && \
    cp "$SCRIPT_DIR/sleep_scheduler.png" ./ || \
    echo "Используем стандартную иконку"

# Создание иконки если не найдена
if [ ! -f sleep_scheduler.png ]; then
    echo "[#] Создание временной иконки..."
    cat > generate_icon.py << 'EOF'
from PIL import Image, ImageDraw
img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.ellipse((20, 20, 235, 235), fill='#1e88e5', outline='white', width=5)
draw.ellipse((60, 60, 195, 195), fill='#bbdefb')
draw.polygon([(128,90), (155,150), (140,150), (128,120), (116,150), (101,150)], 
             fill='#0d47a1')
img.save('sleep_scheduler.png')
EOF
    python3 generate_icon.py
fi

# Определение основного py-файла
MAIN_PY_FILE=$(ls *scheduler*.py | head -1)

# Создание виртуального окружения
echo "[4/6] Сборка приложения..."
python3 -m venv venv
source venv/bin/activate
pip install -U pip > /dev/null
pip install customtkinter pyinstaller > /dev/null

# Сборка
pyinstaller --onefile --windowed \
    --name "$APP_NAME" \
    --add-data "sleep_scheduler.png:." \
    --hidden-import=tcl \
    --hidden-import=tk \
    "$MAIN_PY_FILE"

# Установка приложения
echo "[5/6] Системная установка..."
mkdir -p "$INSTALL_DIR"
cp "dist/$APP_NAME" "$INSTALL_DIR/"
cp "sleep_scheduler.png" "$INSTALL_DIR/"

# Создание команд
echo "sudo \"$INSTALL_DIR/$APP_NAME\"" > "$INSTALL_DIR/autorun.sh"
chmod +x "$INSTALL_DIR/autorun.sh"

echo "#!/bin/bash
cd -- \"\$(dirname \"\$0\")\"
exec \"$INSTALL_DIR/$APP_NAME\"" > "$BIN_PATH"
chmod +x "$BIN_PATH"

# Создание .desktop файла
echo "[6/6] Создание ярлыка приложения..."
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=Sleep Scheduler
Comment=Планировщик управления питанием
Exec=$BIN_PATH
Icon=$INSTALL_DIR/sleep_scheduler.png
Terminal=false
Type=Application
Categories=Utility;
Keywords=power;management;
EOF

# Дополнительные настройки
echo "Разрешаем доступ для всех пользователей..."
chmod 755 "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR/"*

# Проверка установки
echo -e "\033[1;32m"
echo "УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!"
echo "============================="
echo -e "\033[0m"
echo "Приложение установлено в: $INSTALL_DIR"
echo "Запуск:"
echo "  $ sleep-scheduler"
echo
echo "Ярлык создан в меню приложений"
echo
echo "Для управления питанием компьютера запускайте приложение с правами администратора"

# Очистка
rm -rf "$TMP_DIR"