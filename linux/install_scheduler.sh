#!/bin/bash
echo "Установка приложения Sleep Scheduler..."

# Установка системных зависимостей
echo "Установка системных компонентов..."
sudo apt update
sudo apt install -y \
    python3.8 \
    python3.8-venv \
    python3.8-dev \
    python3.8-tk \
    build-essential \
    libjpeg-dev \
    libtiff5-dev \
    libpng-dev \
    zlib1g-dev \
    imagemagick

# Создаем директорию приложения
sudo mkdir -p /opt/SchedulerApp
echo "Директория приложения создана: /opt/SchedulerApp"

# Копируем основной файл
sudo cp hibernation_scheduler_linux.py /opt/SchedulerApp/
echo "Скопирован основной файл приложения"

# Создаем простую синюю иконку
echo "Создание иконки..."
sudo convert -size 256x256 xc:#1e88e5 /opt/SchedulerApp/app_icon.png

# Настраиваем виртуальное окружение
echo "Создание виртуального окружения..."
sudo python3.8 -m venv /opt/SchedulerApp/venv

# Установка Python зависимостей
echo "Установка зависимостей Python..."
/opt/SchedulerApp/venv/bin/pip install --upgrade pip
/opt/SchedulerApp/venv/bin/pip install wheel
/opt/SchedulerApp/venv/bin/pip install customtkinter==5.2.2 pillow==10.4.0

# Создаем скрипт запуска
echo "Создание скрипта запуска..."
sudo tee /usr/local/bin/run_scheduler > /dev/null << 'EOF'
#!/bin/bash
cd /opt/SchedulerApp
source /opt/SchedulerApp/venv/bin/activate
exec pkexec /opt/SchedulerApp/venv/bin/python hibernation_scheduler_linux.py
EOF
sudo chmod +x /usr/local/bin/run_scheduler

# Создаем ярлык в меню приложений
echo "Создание ярлыка в меню приложений..."
sudo tee /usr/share/applications/SchedulerApp.desktop > /dev/null << 'EOF'
[Desktop Entry]
Name=Менеджер сна
Comment=Планировщик гибернации и сна
Exec=run_scheduler
Icon=/opt/SchedulerApp/app_icon.png
Terminal=false
Type=Application
Categories=Utility;System;
EOF

echo "------------------------------------------"
echo "Установка завершена!"
echo "Теперь вы можете запустить приложение одним из способов:"
echo "1. Через меню приложений - ищите 'Менеджер сна'"
echo "2. Через терминал командой: run_scheduler"
echo "3. По ярлыку на рабочем столе (если вы его создали)"