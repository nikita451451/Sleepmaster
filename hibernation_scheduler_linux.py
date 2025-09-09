import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import platform
import datetime
import threading
import subprocess
import json
import time
import webbrowser
import queue

APP_NAME = "TimeMaster Linux"
APP_VERSION = "3.0"
CONFIG_FILE = os.path.expanduser("~/.timemaster_linux_config.json")

DAYS_OF_WEEK_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
DAYS_OF_WEEK_FULL = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
ACTIONS = ["Выключить", "Перезагрузка", "Спящий режим"]

class TimeMasterApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1050x750")
        self.root.minsize(950, 650)
        
        # Центрирование
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 1050) // 2
        y = (self.root.winfo_screenheight() - 750) // 4
        self.root.geometry(f"1050x750+{x}+{y}")
        
        # Состояние приложения
        self.scheduler_active = True
        self.message_queue = queue.Queue()
        
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
        
        # Обработка закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
        """Загрузка конфигурации"""
        default_config = {
            "schedule": {
                day: {
                    "enabled": True if i < 5 else False,
                    "on_time": None,
                    "off_time": "23:00",
                    "action": "Выключить"
                } for i, day in enumerate(DAYS_OF_WEEK_SHORT)
            },
            "autostart_programs": [],
            "settings": {
                "theme": "light",
                "start_minimized": False,
                "notifications": True
            }
        }
        
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return default_config

    def save_config(self):
        """Сохранение конфигурации"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except:
            return False

    def create_ui(self):
        """Создание пользовательского интерфейса"""
        # Главный контейнер
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        # Хедер приложения
        header = tk.Frame(self.root, height=80, bg="#2c3e50")
        header.grid(row=0, column=0, sticky="ew", columnspan=2)
        header.grid_columnconfigure(0, weight=1)
        
        app_title = tk.Label(
            header,
            text=f"{APP_NAME} v{APP_VERSION}",
            font=("Arial", 28, "bold"),
            fg="#ecf0f1",
            bg="#2c3e50"
        )
        app_title.grid(row=0, column=0, padx=20, sticky="w")
        
        app_subtitle = tk.Label(
            header,
            text="Планировщик включения/выключения ПК",
            font=("Arial", 14),
            fg="#bdc3c7",
            bg="#2c3e50"
        )
        app_subtitle.grid(row=1, column=0, padx=20, sticky="w")
        
        # Основные вкладки
        notebook = ttk.Notebook(self.root)
        notebook.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        # Вкладка расписания
        self.schedule_tab = tk.Frame(notebook, bg="white")
        notebook.add(self.schedule_tab, text="📅 Расписание")
        self.create_schedule_ui()
        
        # Вкладка автозапуска
        self.programs_tab = tk.Frame(notebook, bg="white")
        notebook.add(self.programs_tab, text="🚀 Автозапуск")
        self.create_programs_ui()
        
        # Вкладка настроек
        self.settings_tab = tk.Frame(notebook, bg="white")
        notebook.add(self.settings_tab, text="⚙️ Настройки")
        self.create_settings_ui()
        
        # Статус бар
        self.status_var = tk.StringVar(value="⏱️ Идет подготовка...")
        status_frame = tk.Frame(self.root, height=30, bg="#ecf0f1")
        status_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        
        status_bar = tk.Label(
            status_frame,
            textvariable=self.status_var,
            anchor="w",
            font=("Arial", 11),
            bg="#ecf0f1",
            justify="left"
        )
        status_bar.pack(fill="x", padx=15)
        
        # Управляющие кнопки
        button_frame = tk.Frame(self.root, bg="white")
        button_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        self.apply_btn = tk.Button(
            button_frame,
            text="💾 Применить изменения",
            command=self.apply_changes,
            width=20,
            height=2,
            font=("Arial", 12),
            bg="#27ae60",
            fg="white",
            relief="flat"
        )
        self.apply_btn.pack(side="right", padx=10)
        
        self.now_btn = tk.Button(
            button_frame,
            text="⚡ Выполнить сейчас",
            command=self.execute_now,
            width=18,
            height=2,
            font=("Arial", 12),
            bg="#3498db",
            fg="white",
            relief="flat"
        )
        self.now_btn.pack(side="right", padx=10)

    def create_schedule_ui(self):
        """Создание интерфейса для расписания"""
        # Заголовок
        header = tk.Label(
            self.schedule_tab,
            text="Настройка расписания на неделю",
            font=("Arial", 20, "bold"),
            bg="white"
        )
        header.pack(pady=(10, 15))
        
        # Табличка с днями недели
        table_frame = tk.Frame(self.schedule_tab, bg="white")
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Столбцы
        table_frame.columnconfigure(0, weight=1)  # День
        for i in range(1, 5):  # Активация, Время вкл, Время выкл, Действие
            table_frame.columnconfigure(i, weight=2)
        table_frame.columnconfigure(5, weight=1)  # Кнопка копирования
        
        # Заголовки столбцов
        headers = ["День", "Активировать", "Время включения", "Время выключения", "Действие", "Копировать"]
        for col, header_text in enumerate(headers):
            header_label = tk.Label(
                table_frame,
                text=header_text,
                font=("Arial", 14, "bold"),
                bg="#3498db",
                fg="white",
                relief="raised",
                padx=10,
                pady=5
            )
            header_label.grid(row=0, column=col, padx=2, pady=5, sticky="ew")
        
        # Переменные для хранения состояний
        self.day_enabled = {}
        self.on_time_vars = {}
        self.off_time_vars = {}
        self.action_vars = {}
        
        # Заполнение таблицы
        for row, day in enumerate(DAYS_OF_WEEK_SHORT, start=1):
            # День
            day_label = tk.Label(
                table_frame,
                text=DAYS_OF_WEEK_FULL[row-1],
                font=("Arial", 13),
                bg="white"
            )
            day_label.grid(row=row, column=0, padx=5, pady=7, sticky="w")
            
            # Активация дня
            self.day_enabled[day] = tk.BooleanVar(value=self.config["schedule"][day]["enabled"])
            switch = tk.Checkbutton(
                table_frame,
                variable=self.day_enabled[day],
                bg="white"
            )
            switch.grid(row=row, column=1, padx=10, pady=5)
            
            # Время включения
            self.on_time_vars[day] = tk.StringVar(
                value=self.config["schedule"][day]["on_time"] or "")
            on_time_entry = tk.Entry(
                table_frame,
                textvariable=self.on_time_vars[day],
                width=12,
                justify="center",
                font=("Arial", 11)
            )
            on_time_entry.grid(row=row, column=2, padx=5, pady=5)
            
            # Время выключения
            self.off_time_vars[day] = tk.StringVar(
                value=self.config["schedule"][day]["off_time"])
            off_time_entry = tk.Entry(
                table_frame,
                textvariable=self.off_time_vars[day],
                width=12,
                justify="center",
                font=("Arial", 11)
            )
            off_time_entry.grid(row=row, column=3, padx=5, pady=5)
            
            # Действие
            self.action_vars[day] = tk.StringVar(
                value=self.config["schedule"][day]["action"])
            action_dropdown = ttk.Combobox(
                table_frame,
                textvariable=self.action_vars[day],
                values=ACTIONS,
                width=14,
                state="readonly"
            )
            action_dropdown.grid(row=row, column=4, padx=5, pady=5)
            
            # Кнопка копирования
            copy_btn = tk.Button(
                table_frame,
                text=f"📋 → Все",
                command=lambda d=day: self.copy_day_settings(d),
                width=8,
                height=1,
                font=("Arial", 10),
                bg="#95a5a6",
                fg="white"
            )
            copy_btn.grid(row=row, column=5, padx=5, pady=5)
        
        # Кнопки управления всей таблицей
        table_ctrl_frame = tk.Frame(self.schedule_tab, bg="white")
        table_ctrl_frame.pack(pady=10)
        
        tk.Button(
            table_ctrl_frame,
            text="✅ Активировать все дни",
            command=lambda: self.set_all_days(True),
            width=18,
            bg="#27ae60",
            fg="white"
        ).pack(side="left", padx=5)
        
        tk.Button(
            table_ctrl_frame,
            text="❌ Отменить все дни",
            command=lambda: self.set_all_days(False),
            width=18,
            bg="#e74c3c",
            fg="white"
        ).pack(side="left", padx=5)
        
        tk.Button(
            table_ctrl_frame,
            text="🔄 Сброс расписания",
            command=self.reset_schedule,
            width=18,
            bg="#f39c12",
            fg="white"
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
        self.root.after(3000, lambda: self.status_var.set("✅ Готово"))

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
            self.action_vars[day].set("Выключить")
        self.status_var.set("⚡ Расписание сброшено к значениям по умолчанию")

    def create_programs_ui(self):
        """Создание интерфейса для автозапуска программ"""
        # Заголовок
        header = tk.Label(
            self.programs_tab,
            text="Программы для автозапуска",
            font=("Arial", 20, "bold"),
            bg="white"
        )
        header.pack(pady=(10, 15))
        
        description = tk.Label(
            self.programs_tab,
            text="Программы из списка будут запущены при каждом старте системы",
            font=("Arial", 14),
            fg="#7f8c8d",
            bg="white"
        )
        description.pack(pady=(0, 20))
        
        # Контейнер для списка программ
        programs_frame = tk.Frame(self.programs_tab, bg="white")
        programs_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Заголовки списка
        header_frame = tk.Frame(programs_frame, bg="#3498db")
        header_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Label(
            header_frame,
            text="Программа",
            font=("Arial", 14, "bold"),
            fg="white",
            bg="#3498db"
        ).pack(side="left", padx=10, pady=5)
        
        # Список программ
        self.programs_list = tk.Frame(programs_frame, bg="white")
        self.programs_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Загрузка существующих программ
        self.autostart_program_frames = []
        for program in self.config["autostart_programs"]:
            self.add_program_ui(program)
        
        # Кнопки добавления/удаления
        btn_frame = tk.Frame(programs_frame, bg="white")
        btn_frame.pack(fill="x", padx=5, pady=10)
        
        tk.Button(
            btn_frame,
            text="➕ Добавить программу",
            command=self.add_program,
            width=20,
            bg="#27ae60",
            fg="white"
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_frame,
            text="🗑️ Удалить выделенные",
            command=self.remove_programs,
            width=20,
            bg="#e74c3c",
            fg="white"
        ).pack(side="right", padx=5)

    def add_program_ui(self, program_path):
        """Добавление элемента программы в UI"""
        frame = tk.Frame(self.programs_list, bg="#ecf0f1", relief="raised", bd=1)
        
        program_name = os.path.basename(program_path)
        tk.Label(
            frame,
            text=program_name,
            font=("Arial", 12),
            anchor="w",
            bg="#ecf0f1"
        ).pack(side="left", padx=10, pady=5, fill="x", expand=True)
        
        btn = tk.Button(
            frame,
            text="📂 Показать",
            command=lambda p=program_path: webbrowser.open(os.path.dirname(p)),
            width=10,
            height=1,
            font=("Arial", 10),
            bg="#3498db",
            fg="white"
        )
        btn.pack(side="right", padx=5)
        
        frame.pack(fill="x", pady=3, padx=2)
        self.autostart_program_frames.append((frame, program_path))

    def add_program(self):
        """Добавление новой программы"""
        file_types = [("Исполняемые файлы", "*.sh *.py *.bin"), ("Все файлы", "*.*")]
        path = filedialog.askopenfilename(
            title="Выберите программу для автозапуска",
            filetypes=file_types
        )
        
        if path:
            self.config["autostart_programs"].append(path)
            self.add_program_ui(path)
            self.status_var.set(f"✚ Добавлена программа: {os.path.basename(path)}")

    def remove_programs(self):
        """Удаление выбранных программ"""
        self.status_var.set("⚡ Выбранные программы удалены из автозапуска")

    def create_settings_ui(self):
        """Создание интерфейса настроек"""
        # Заголовок
        header = tk.Label(
            self.settings_tab,
            text="Настройки приложения",
            font=("Arial", 20, "bold"),
            bg="white"
        )
        header.pack(pady=(10, 15))
        
        # Настройки внешнего вида
        theme_frame = tk.Frame(self.settings_tab, bg="white")
        theme_frame.pack(fill="x", padx=20, pady=15)
        
        tk.Label(
            theme_frame,
            text="Тема интерфейса:",
            font=("Arial", 14),
            bg="white"
        ).pack(anchor="w", pady=5)
        
        self.theme_var = tk.StringVar(value=self.config["settings"]["theme"])
        theme_combo = ttk.Combobox(
            theme_frame,
            textvariable=self.theme_var,
            values=["light", "dark"],
            width=20,
            state="readonly"
        )
        theme_combo.pack(anchor="w", pady=5)
        
        # Настройки уведомлений
        notify_frame = tk.Frame(self.settings_tab, bg="white")
        notify_frame.pack(fill="x", padx=20, pady=15)
        
        self.notify_enabled = tk.BooleanVar(value=self.config["settings"]["notifications"])
        notify_switch = tk.Checkbutton(
            notify_frame,
            text="Показывать уведомления",
            variable=self.notify_enabled,
            font=("Arial", 14),
            bg="white"
        )
        notify_switch.pack(anchor="w", pady=5)
        
        # Дополнительные настройки
        advanced_frame = tk.Frame(self.settings_tab, bg="white")
        advanced_frame.pack(fill="x", padx=20, pady=15)
        
        self.minimize_var = tk.BooleanVar(value=self.config["settings"]["start_minimized"])
        minimize_switch = tk.Checkbutton(
            advanced_frame,
            text="Сворачивать в трей вместо закрытия",
            variable=self.minimize_var,
            font=("Arial", 14),
            bg="white"
        )
        minimize_switch.pack(anchor="w", pady=5)
        
        # Информация для Linux
        info_text = """
        Для Linux доступны следующие команды:
        - Выключение: systemctl poweroff / shutdown -h now
        - Перезагрузка: systemctl reboot / shutdown -r now
        - Спящий режим: systemctl suspend
        
        Для автоматического включения требуется настройка BIOS/UEFI
        """
        
        info_label = tk.Label(
            advanced_frame,
            text=info_text,
            font=("Arial", 12),
            justify="left",
            fg="#7f8c8d",
            bg="white"
        )
        info_label.pack(anchor="w", pady=10)

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
                    self.execute_action(schedule.get("action", "Выключить"))

    def execute_action(self, action):
        """Выполнение действия согласно расписания"""
        action_map = {
            "Выключить": "systemctl poweroff",
            "Перезагрузка": "systemctl reboot", 
            "Спящий режим": "systemctl suspend"
        }
        
        cmd = action_map.get(action, "systemctl poweroff")
        try:
            subprocess.run(cmd, shell=True)
            self.status_var.set(f"⏱️ Выполнено действие: {action}")
        except:
            self.status_var.set(f"⚠️ Ошибка выполнения: {action}")

    def process_messages(self):
        """Обработка сообщений из очереди"""
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                self.status_var.set(message)
        except queue.Empty:
            pass
        
        if self.root.winfo_exists():
            self.root.after(100, self.process_messages)

    def update_time(self):
        """Обновление статусбара с текущим временем"""
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_var.set(f"Система: ⏱️ {current_time} | ✓ Режим планировщика: {'Активен' if self.scheduler_active else 'Остановлен'}")
        self.root.after(1000, self.update_time)

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
        
        self.save_config()
        self.status_var.set("⚡ Изменения применены! Конфигурация сохранена.")
        self.root.after(3000, lambda: self.status_var.set("✅ Конфигурация актуальна"))

    def execute_now(self):
        """Выполнение действия немедленно"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Немедленное выполнение")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.grid_columnconfigure(0, weight=1)
        
        tk.Label(
            dialog,
            text="Выберите действие для выполнения:",
            font=("Arial", 16)
        ).grid(row=0, column=0, pady=20, padx=20, sticky="w")
        
        selected_action = tk.StringVar(value="Выключить")
        action_combo = ttk.Combobox(
            dialog,
            variable=selected_action,
            values=["Выключить", "Перезагрузка", "Спящий режим"],
            width=20,
            state="readonly"
        )
        action_combo.grid(row=1, column=0, pady=10, padx=20, sticky="ew")
        
        def confirm():
            action = selected_action.get()
            self.execute_action(action)
            dialog.destroy()
        
        tk.Button(
            dialog,
            text="Выполнить",
            command=confirm,
            width=15,
            height=2,
            bg="#e67e22",
            fg="white"
        ).grid(row=2, column=0, pady=15)

    def on_closing(self):
        """Обработка закрытия приложения"""
        # Остановка планировщика
        self.scheduler_active = False
        
        # Сохранение состояния
        self.apply_changes()
        self.save_config()
        
        # Закрытие приложения
        self.root.destroy()

if __name__ == "__main__":
    app = TimeMasterApp()
    app.root.mainloop()