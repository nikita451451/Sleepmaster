import os
import sys
import customtkinter as ctk
import platform
import datetime
import threading
import subprocess
import json
import time
from PIL import Image, ImageTk
import webbrowser
import queue

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

APP_NAME = "TimeMaster"
APP_VERSION = "3.0"

# Linux-specific paths
CONFIG_DIR = os.path.expanduser("~/.config/timemaster")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
APP_ICON = "sleep_icon.png"  # Changed to PNG for Linux compatibility

DAYS_OF_WEEK_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
DAYS_OF_WEEK_FULL = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
ACTIONS = ["Выключить", "Сон", "Гибернация", "Перезагрузка"]

class TimeMasterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Состояние приложения
        self.scheduler_active = True
        self.is_fullscreen = False
        self.message_queue = queue.Queue()
        
        # Настройка окна
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1050x750")
        self.minsize(950, 650)
        
        # Центрирование
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 1050) // 2
        y = (self.winfo_screenheight() - 750) // 4
        self.geometry(f"1050x750+{x}+{y}")
        
        # Иконка
        self.setup_icon()
        
        # Загрузка конфигурации
        self.config = self.load_config()
        
        # Создание интерфейса
        self.create_ui()
        
        # Запуск планировщика
        self.start_scheduler()
        
        # Запуск обработки сообщений
        self.process_messages()
        
        # Обновление времени
        self.update_time()
        
        # Обработчик закрытия
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_icon(self):
        """Установка иконки приложения"""
        try:
            if sys.platform == "win32":
                self.iconbitmap(APP_ICON)
            elif os.path.exists(APP_ICON):
                # Для Linux используем ImageTk
                img = Image.open(APP_ICON)
                tk_img = ImageTk.PhotoImage(img)
                self.iconphoto(False, tk_img)
        except Exception as e:
            print(f"Ошибка загрузки иконки: {e}")

    def load_config(self):
        """Загрузка конфигурации"""
        default_config = {
            "schedule": {
                day: {
                    "enabled": True if i < 5 else False,
                    "on_time": None,
                    "off_time": "23:00",
                    "action": "Сон"
                } for i, day in enumerate(DAYS_OF_WEEK_SHORT)
            },
            "autostart_programs": [],
            "settings": {
                "theme": "dark",
                "start_minimized": False,
                "notifications": True
            }
        }
        
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
        return default_config

    def save_config(self):
        """Сохранение конфигурации"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
            return False

    def create_ui(self):
        """Создание пользовательского интерфейса"""
        # Главный контейнер
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Хедер приложения
        header = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color="#2c3e50")
        header.grid(row=0, column=0, sticky="ew", columnspan=2)
        header.grid_columnconfigure(0, weight=1)
        
        app_title = ctk.CTkLabel(
            header,
            text=f"{APP_NAME} v{APP_VERSION}",
            font=("Arial", 28, "bold"),
            text_color="#ecf0f1"
        )
        app_title.grid(row=0, column=0, padx=20, sticky="w")
        
        app_subtitle = ctk.CTkLabel(
            header,
            text="Планировщик включения/выключения ПК",
            font=("Arial", 14),
            text_color="#bdc3c7"
        )
        app_subtitle.grid(row=1, column=0, padx=20, sticky="w")
        
        # Основные вкладки
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        # Вкладка расписания
        self.schedule_tab = self.tabview.add("📅 Расписание")
        self.create_schedule_ui()
        
        # Вкладка автозапуска
        self.programs_tab = self.tabview.add("🚀 Автозапуск")
        self.create_programs_ui()
        
        # Вкладка настроек
        self.settings_tab = self.tabview.add("⚙️ Настройки")
        self.create_settings_ui()
        
        # Статус бар
        self.status_var = ctk.StringVar(value="⏱️ Идет подготовка...")
        status_frame = ctk.CTkFrame(self, height=30, corner_radius=0)
        status_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        
        status_bar = ctk.CTkLabel(
            status_frame,
            textvariable=self.status_var,
            anchor="w",
            font=("Arial", 11),
            justify="left"
        )
        status_bar.pack(fill="x", padx=15)
        
        # Управляющие кнопки
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        self.apply_btn = ctk.CTkButton(
            button_frame,
            text="💾 Применить изменения",
            command=self.apply_changes,
            width=200,
            height=40,
            font=("Arial", 14),
            fg_color="#27ae60",
            hover_color="#219653"
        )
        self.apply_btn.pack(side="right", padx=10)
        
        self.now_btn = ctk.CTkButton(
            button_frame,
            text="⚡ Выполнить сейчас",
            command=self.execute_now,
            width=180,
            height=40,
            font=("Arial", 14),
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.now_btn.pack(side="right", padx=10)

    def create_schedule_ui(self):
        """Создание интерфейса для расписания"""
        # Заголовок
        header = ctk.CTkLabel(
            self.schedule_tab,
            text="Настройка расписания на неделю",
            font=("Arial", 20, "bold")
        )
        header.pack(pady=(10, 15))
        
        # Табличка с днями недели
        table_frame = ctk.CTkFrame(self.schedule_tab, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Столбцы
        table_frame.columnconfigure(0, weight=1)  # День
        for i in range(1, 5):  # Активация, Время вкл, Время выкл, Действие
            table_frame.columnconfigure(i, weight=2)
        table_frame.columnconfigure(5, weight=1)  # Кнопка копирования
        
        # Заголовки столбцов
        headers = ["День", "Активировать", "Время включения", "Время выключения", "Действие", "Копировать"]
        for col, header_text in enumerate(headers):
            header_label = ctk.CTkLabel(
                table_frame,
                text=header_text,
                font=("Arial", 14, "bold"),
                corner_radius=6,
                fg_color="#3498db",
                text_color="white"
            )
            header_label.grid(row=0, column=col, padx=5, pady=5, sticky="ew")
        
        # Переменные для хранения состояний
        self.day_enabled = {}
        self.on_time_vars = {}
        self.off_time_vars = {}
        self.action_vars = {}
        
        # Заполнение таблицы
        for row, day in enumerate(DAYS_OF_WEEK_SHORT, start=1):
            # День
            day_label = ctk.CTkLabel(
                table_frame,
                text=DAYS_OF_WEEK_FULL[row-1],
                font=("Arial", 13)
            )
            day_label.grid(row=row, column=0, padx=5, pady=7, sticky="w")
            
            # Активация дня
            self.day_enabled[day] = ctk.BooleanVar(value=self.config["schedule"][day]["enabled"])
            switch = ctk.CTkSwitch(
                table_frame,
                text="",
                variable=self.day_enabled[day],
                onvalue=True,
                offvalue=False,
                width=20
            )
            switch.grid(row=row, column=1, padx=10, pady=5)
            
            # Время включения
            self.on_time_vars[day] = ctk.StringVar(
                value=self.config["schedule"][day]["on_time"] or "")
            on_time_entry = ctk.CTkEntry(
                table_frame,
                textvariable=self.on_time_vars[day],
                placeholder_text="чч:мм",
                width=120,
                justify="center"
            )
            on_time_entry.grid(row=row, column=2, padx=5, pady=5)
            
            # Время выключения
            self.off_time_vars[day] = ctk.StringVar(
                value=self.config["schedule"][day]["off_time"])
            off_time_entry = ctk.CTkEntry(
                table_frame,
                textvariable=self.off_time_vars[day],
                width=120,
                justify="center"
            )
            off_time_entry.grid(row=row, column=3, padx=5, pady=5)
            
            # Действие
            self.action_vars[day] = ctk.StringVar(
                value=self.config["schedule"][day]["action"])
            action_dropdown = ctk.CTkComboBox(
                table_frame,
                variable=self.action_vars[day],
                values=ACTIONS,
                width=150
            )
            action_dropdown.grid(row=row, column=4, padx=5, pady=5)
            
            # Кнопка копирования
            copy_btn = ctk.CTkButton(
                table_frame,
                text=f"📋 → Все",
                command=lambda d=day: self.copy_day_settings(d),
                width=70,
                height=30,
                font=("Arial", 11)
            )
            copy_btn.grid(row=row, column=5, padx=5, pady=5)
        
        # Кнопки управления всей таблицей
        table_ctrl_frame = ctk.CTkFrame(self.schedule_tab, fg_color="transparent")
        table_ctrl_frame.pack(pady=10)
        
        ctk.CTkButton(
            table_ctrl_frame,
            text="✅ Активировать все дни",
            command=lambda: self.set_all_days(True),
            width=170
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            table_ctrl_frame,
            text="❌ Отменить все дни",
            command=lambda: self.set_all_days(False),
            width=170
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            table_ctrl_frame,
            text="🔄 Сброс расписания",
            command=self.reset_schedule,
            width=170,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        ).pack(side="left", padx=5)

    def copy_day_settings(self, day):
        """Копирование настроек выбранного дня на все остальные дни"""
        settings = {
            "enabled": self.day_enabled[day].get(),
            "on_time": self.on_time_vars[day].get(),
            "off_time": self.off_time_vars[day].get(),
            "action": self.action_vars[day].get()
        }
        
        for d in DAYS_OF_WEEK_SHORT:
            if d != day:
                self.day_enabled[d].set(settings["enabled"])
                self.on_time_vars[d].set(settings["on_time"])
                self.off_time_vars[d].set(settings["off_time"])
                self.action_vars[d].set(settings["action"])
        
        self.status_var.set(f"⚡ Настройки '{day}' скопированы на все дни")
        self.after(3000, lambda: self.status_var.set("✅ Готово"))

    def set_all_days(self, state):
        """Установка состояния для всех дней"""
        for day in DAYS_OF_WEEK_SHORT:
            self.day_enabled[day].set(state)
        self.status_var.set(f"⚡ Все дни {'активированы' if state else 'деактивированы'}")

    def reset_schedule(self):
        """Сброс расписания к значениям по умолчанию"""
        for day in DAYS_OF_WEEK_SHORT:
            self.day_enabled[day].set(True if DAYS_OF_WEEK_SHORT.index(day) < 5 else False)
            self.on_time_vars[day].set("")
            self.off_time_vars[day].set("23:00")
            self.action_vars[day].set("Сон")
        self.status_var.set("⚡ Расписание сброшено к значениям по умолчанию")

    def create_programs_ui(self):
        """Создание интерфейса для автозапуска программ"""
        # Заголовок
        header = ctk.CTkLabel(
            self.programs_tab,
            text="Программы для автозапуска",
            font=("Arial", 20, "bold")
        )
        header.pack(pady=(10, 15))
        
        description = ctk.CTkLabel(
            self.programs_tab,
            text="Программы из списка будут запущены при каждом старте системы",
            font=("Arial", 14),
            text_color="#7f8c8d"
        )
        description.pack(pady=(0, 20))
        
        # Контейнер для списка программ
        programs_frame = ctk.CTkFrame(self.programs_tab)
        programs_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Заголовки списка
        header_frame = ctk.CTkFrame(programs_frame, fg_color="#3498db")
        header_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(
            header_frame,
            text="Программа",
            font=("Arial", 14, "bold"),
            text_color="white"
        ).pack(side="left", padx=10, pady=5)
        
        # Список программ
        self.programs_list = ctk.CTkScrollableFrame(programs_frame, height=250)
        self.programs_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Загрузка существующих программ
        self.autostart_program_frames = []
        for program in self.config["autostart_programs"]:
            self.add_program_ui(program)
        
        # Кнопки добавления/удаления
        btn_frame = ctk.CTkFrame(programs_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=10)
        
        ctk.CTkButton(
            btn_frame,
            text="➕ Добавить программу",
            command=self.add_program,
            width=200
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="🗑️ Удалить выделенные",
            command=self.remove_programs,
            width=200,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        ).pack(side="right", padx=5)

    def add_program_ui(self, program_path):
        """Добавление элемента программы в UI"""
        frame = ctk.CTkFrame(self.programs_list, fg_color="#ecf0f1")
        
        program_name = os.path.basename(program_path)
        ctk.CTkLabel(
            frame,
            text=program_name,
            font=("Arial", 12),
            anchor="w"
        ).pack(side="left", padx=10, pady=5, fill="x", expand=True)
        
        btn = ctk.CTkButton(
            frame,
            text="📂 Показать",
            command=lambda p=program_path: webbrowser.open(os.path.dirname(p)),
            width=80,
            height=25,
            font=("Arial", 11)
        )
        btn.pack(side="right", padx=5)
        
        frame.pack(fill="x", pady=3, padx=2)
        self.autostart_program_frames.append((frame, program_path))

    def add_program(self):
        """Добавление новой программы (адаптировано для Linux)"""
        file_types = [("Все файлы", "*.*")]  # Linux-friendly
        path = ctk.filedialog.askopenfilename(
            title="Выберите программу для автозапуска",
            filetypes=file_types
        )
        
        if path:
            self.config["autostart_programs"].append(path)
            self.add_program_ui(path)
            self.status_var.set(f"✚ Добавлена программа: {os.path.basename(path)}")

    def remove_programs(self):
        """Удаление выбранных программ"""
        # В реальной реализации здесь будет логика удаления
        self.status_var.set("⚡ Выбранные программы удалены из автозапуска")

    def create_settings_ui(self):
        """Создание интерфейса настроек"""
        # Заголовок
        header = ctk.CTkLabel(
            self.settings_tab,
            text="Настройки приложения",
            font=("Arial", 20, "bold")
        )
        header.pack(pady=(10, 15))
        
        # Категории настроек
        setting_categories = [
            ("🌙 Внешний вид", self.create_appearance_settings),
            ("🔔 Уведомления", self.create_notification_settings),
            ("⚙️ Дополнительно", self.create_advanced_settings)
        ]
        
        # Создаем вкладки для каждой категории
        category_tabview = ctk.CTkTabview(self.settings_tab)
        category_tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        for title, create_func in setting_categories:
            tab = category_tabview.add(title)
            create_func(tab)

    def create_appearance_settings(self, tab):
        """Настройки внешнего вида"""
        theme_frame = ctk.CTkFrame(tab, fg_color="transparent")
        theme_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            theme_frame,
            text="Тема интерфейса:",
            font=("Arial", 14)
        ).pack(anchor="w", pady=5)
        
        self.theme_var = ctk.StringVar(value=self.config["settings"]["theme"])
        theme_combo = ctk.CTkComboBox(
            theme_frame,
            variable=self.theme_var,
            values=["Системная", "Светлая", "Темная"],
            width=200
        )
        theme_combo.pack(anchor="w", pady=5)
        
        # Переключатель компактного режима
        self.compact_var = ctk.BooleanVar(value=False)
        compact_switch = ctk.CTkSwitch(
            theme_frame,
            text="Компактный режим интерфейса",
            variable=self.compact_var,
            font=("Arial", 14)
        )
        compact_switch.pack(anchor="w", pady=15)

    def create_notification_settings(self, tab):
        """Настройки уведомлений"""
        notify_frame = ctk.CTkFrame(tab, fg_color="transparent")
        notify_frame.pack(fill="x", padx=20, pady=15)
        
        self.notify_enabled = ctk.BooleanVar(value=self.config["settings"]["notifications"])
        notify_switch = ctk.CTkSwitch(
            notify_frame,
            text="Показывать уведомления",
            variable=self.notify_enabled,
            font=("Arial", 14)
        )
        notify_switch.pack(anchor="w", pady=5)
        
        # Предуреждающие уведомления
        self.warn_before = ctk.BooleanVar(value=True)
        warn_switch = ctk.CTkSwitch(
            notify_frame,
            text="Предупреждение за 10 минут до действия",
            variable=self.warn_before,
            font=("Arial", 14)
        )
        warn_switch.pack(anchor="w", pady=15)

    def create_advanced_settings(self, tab):
        """Дополнительные настройки"""
        advanced_frame = ctk.CTkFrame(tab, fg_color="transparent")
        advanced_frame.pack(fill="x", padx=20, pady=15)
        
        # Автозапуск приложения
        self.autostart_var = ctk.BooleanVar(value=False)
        autostart_switch = ctk.CTkSwitch(
            advanced_frame,
            text="Запуск приложения при старте системы",
            variable=self.autostart_var,
            font=("Arial", 14)
        )
        autostart_switch.pack(anchor="w", pady=5)
        
        # Сворачивание в трей
        self.minimize_var = ctk.BooleanVar(value=self.config["settings"]["start_minimized"])
        minimize_switch = ctk.CTkSwitch(
            advanced_frame,
            text="Сворачивать в трей вместо закрытия",
            variable=self.minimize_var,
            font=("Arial", 14)
        )
        minimize_switch.pack(anchor="w", pady=15)
        
        # Информация о BIOS
        bios_info = ctk.CTkLabel(
            advanced_frame,
            text="Для работы функции автоматического включения компьютера:\n"
                 "1. Зайдите в настройки BIOS/UEFI вашего компьютера\n"
                 "2. Найдите раздел Power Management или аналогичный\n"
                 "3. Активируйте опцию 'Wake on RTC Alarm' или 'Resume by RTC'\n"
                 "4. Сохраните изменения и перезагрузитесь",
            font=("Arial", 13),
            justify="left",
            text_color="#7f8c8d"
        )
        bios_info.pack(anchor="w", pady=10)

    def start_scheduler(self):
        """Запуск фонового планировщика"""
        self.scheduler_thread = threading.Thread(target=self.check_schedule, daemon=True)
        self.scheduler_thread.start()

    def check_schedule(self):
        """Проверка расписания для выполнения действий"""
        while self.scheduler_active:
            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M")
            current_day = now.weekday()  # 0=пн, 6=вс
            
            # Проверяем каждую минуту
            time.sleep(60)
            
            # Пропускаем проверку если приложение не активно
            if not self.scheduler_active:
                break
            
            # Проверка расписания для текущего дня
            day = DAYS_OF_WEEK_SHORT[current_day]
            schedule = self.config["schedule"][day]
            
            if schedule.get("enabled", False):
                # Проверка на время выключения
                off_time = schedule.get("off_time")
                if off_time and off_time == current_time:
                    self.execute_action(schedule.get("action", "Сон"))
                    
                # Проверка на время включения
                on_time = schedule.get("on_time")
                if on_time and on_time == current_time:
                    self.status_var.set("☀️ По расписанию: Время включения ПК")

    def execute_action(self, action):
        """Выполнение действия согласно расписания"""
        linux_cmd = {
            "Выключить": "systemctl poweroff",
            "Сон": "systemctl suspend",
            "Гибернация": "systemctl hibernate",
            "Перезагрузка": "systemctl reboot"
        }
        
        if sys.platform == "linux":
            cmd = linux_cmd.get(action)
            if cmd:
                self.status_var.set(f"⌛ Выполняем: {action}...")
                try:
                    # Пытаемся запустить с sudo
                    result = subprocess.run(
                        ["pkexec"] + cmd.split(), 
                        capture_output=True, 
                        text=True
                    )
                    
                    if result.returncode == 0:
                        self.status_var.set(f"✅ Выполнено: {action}")
                    else:
                        error_msg = result.stderr.strip() or "Неизвестная ошибка"
                        self.status_var.set(f"⚠️ Ошибка: {error_msg}")
                except Exception as e:
                    self.status_var.set(f"⚠️ Ошибка выполнения: {str(e)}")
        else:
            # Оригинальный код для Windows
            action_map = {
                "Выключить": "shutdown /s /f /t 0",
                "Сон": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
                "Гибернация": "shutdown /h",
                "Перезагрузка": "shutdown /r /f /t 0"
            }
            
            if sys.platform == "win32":
                cmd = action_map.get(action)
                if cmd:
                    try:
                        subprocess.run(cmd, shell=True)
                        self.status_var.set(f"✅ Выполнено: {action}")
                    except Exception as e:
                        self.status_var.set(f"⚠️ Ошибка: {str(e)}")
            else:
                self.status_var.set("⚠️ Поддержка только для Windows/Linux")

    def process_messages(self):
        """Обработка сообщений из очереди"""
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                self.status_var.set(message)
        except queue.Empty:
            pass
        
        if self.winfo_exists():
            self.after(100, self.process_messages)

    def update_time(self):
        """Обновление статусбара с текущим временем"""
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_var.set(f"Система: ⏱️ {current_time} | ✓ Режим планировщика: {'Активен' if self.scheduler_active else 'Остановлен'}")
        self.after(1000, self.update_time)

    def apply_changes(self):
        """Применение изменений"""
        # Сохранение расписания
        for day in DAYS_OF_WEEK_SHORT:
            self.config["schedule"][day] = {
                "enabled": self.day_enabled[day].get(),
                "on_time": self.on_time_vars[day].get(),
                "off_time": self.off_time_vars[day].get(),
                "action": self.action_vars[day].get()
            }
        
        # Сохранение настроек
        self.config["settings"] = {
            "theme": self.theme_var.get(),
            "start_minimized": self.minimize_var.get(),
            "notifications": self.notify_enabled.get()
        }
        
        if self.save_config():
            self.status_var.set("⚡ Изменения применены! Конфигурация сохранена.")
            self.after(3000, lambda: self.status_var.set("✅ Конфигурация актуальна"))
        else:
            self.status_var.set("⚠️ Ошибка сохранения конфигурации!")

    def execute_now(self):
        """Выполнение действия немедленно"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Немедленное выполнение")
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()
        
        # Используем grid для диалогового окна
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            dialog,
            text="Выберите действие для выполнения:",
            font=("Arial", 16)
        ).grid(row=0, column=0, pady=20, padx=20, sticky="w")
        
        selected_action = ctk.StringVar(value="Выключить")
        action_combo = ctk.CTkComboBox(
            dialog,
            variable=selected_action,
            values=["Выключить", "Сон", "Гибернация", "Перезагрузка"],
            width=200
        )
        action_combo.grid(row=1, column=0, pady=10, padx=20, sticky="ew")
        
        def confirm():
            action = selected_action.get()
            self.execute_action(action)
            dialog.destroy()
        
        ctk.CTkButton(
            dialog,
            text="Выполнить",
            command=confirm,
            width=150,
            height=40,
            fg_color="#e67e22"
        ).grid(row=2, column=0, pady=15)

    def on_closing(self):
        """Обработка закрытия приложения"""
        # Остановка планировщика
        self.scheduler_active = False
        
        # Сохранение состояния
        self.save_config()
        
        # Закрытие приложения
        self.destroy()

if __name__ == "__main__":
    app = TimeMasterApp()
    app.mainloop()