# Sleep Scheduler - Планировщик спящего режима

Приложение для автоматического перевода компьютера в спящий режим по расписанию. Поддерживает Windows и Linux.

## Установка

Для Windows:

Запустите build_windows.bat

Для Linux:

Дайте права: chmod +x build_linux.sh
Запустите: ./build_linux.sh

Шаг 3: Установка

Для Windows:

Запустите install_windows.bat от имени администратора

Для Linux:

Дайте права: chmod +x install_linux.sh
Запустите: sudo ./install_linux.sh

## Использование
- Установите расписание во вкладке "Расписание"
- Нажмите "Сохранить" для сохранения настроек
- Для немедленного перехода в спящий режим используйте кнопку на главной вкладке

# Запуск в терминале для отладки
cd dist/
./hibernation_scheduler

# Смотрите вывод на наличие ошибок:
# - отсутствие библиотек
# - проблемы с темами
# - ошибки импорта

# Проверьте команды через терминал
systemctl suspend
loginctl suspend

# Если требуются права sudo:
sudo visudo
# Добавьте строку:
your_username ALL=(ALL) NOPASSWD: /bin/systemctl suspend, /bin/loginctl suspend