#!/bin/bash
echo "Установка приложения..."
sudo mkdir -p /opt/SchedulerApp
sudo cp hibernation_scheduler_linux.py /opt/SchedulerApp/

sudo apt update
sudo apt install -y python3.8 python3.8-venv python3.8-dev python3.8-tk imagemagick

# Создание иконки
sudo convert -size 256x256 xc:#1e88e5 /opt/SchedulerApp/app_icon.png

# Создание виртуального окружения
sudo python3.8 -m venv /opt/SchedulerApp/venv

# Установка зависимостей
/opt/SchedulerApp/venv/bin/pip install customtkinter pillow

# Создание скрипта запуска
sudo bash -c 'cat > /usr/local/bin/run_scheduler << EOF
#!/bin/bash
cd /opt/SchedulerApp
source /opt/SchedulerApp/venv/bin/activate
exec pkexec python hibernation_scheduler_linux.py
EOF'
sudo chmod +x /usr/local/bin/run_scheduler

# Создание ярлыка на рабочем столе
sudo bash -c 'cat > /usr/share/applications/SchedulerApp.desktop << EOF
[Desktop Entry]
Name=Менеджер сна
Exec=run_scheduler
Icon=/opt/SchedulerApp/app_icon.png
Terminal=false
Type=Application
Categories=Utility;
EOF'

echo "Установка завершена! Для запуска используйте команду 'run_scheduler'"