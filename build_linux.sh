#!/bin/bash

echo "Установка зависимостей..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-pil.imagetk python3-tk
pip3 install pyinstaller pillow

echo "Очистка предыдущих сборок..."
rm -rf dist build __pycache__

echo "Сборка приложения для Linux..."
pyinstaller --onefile --windowed --add-data "sleep_scheduler.png:." --icon=sleep_scheduler.png hibernation_scheduler.py

echo "Установка прав..."
chmod +x dist/hibernation_scheduler

echo "Сборка завершена! Исполняемый файл: dist/hibernation_scheduler"