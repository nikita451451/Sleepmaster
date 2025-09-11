#!/usr/bin/env python3
import sys
import os
import time
import subprocess
import json
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import threading
import getpass
from pathlib import Path

# Фикс для отображения GUI на некоторых Linux-системах
if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':0'

# Помощник для пути к ресурсам
def resource_path(relative_path):
    """Определяет правильный путь к ресурсам в разных окружениях"""
    try:
        # PyInstaller создает временную папку в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    full_path = os.path.join(base_path, relative_path)
    
    # Если файл не найден в основной папке, пробуем системную директорию
    if not os.path.exists(full_path):
        system_path = os.path.join("/opt/SleepScheduler", relative_path)
        if os.path.exists(system_path):
            return system_path
    
    return full_path

# Проверка прав доступа (корректный запуск с root-правами)
if os.geteuid() != 0:
    print("Перезапуск приложения с правами root...")
    try:
        # Используем pkexec для графического запроса пароля
        result = subprocess.run(
            ['pkexec', sys.executable] + sys.argv,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        sys.exit(result.returncode)
    except Exception as e:
        print(f"Ошибка при перезапуске: {e}")
        messagebox.showerror(
            "Ошибка запуска", 
            f"Не удалось запустить с правами root: {str(e)}\n"
            "Попробуйте запустить в терминале: \nsudo sleep-scheduler"
        )
    sys.exit(1)

# Инициализация графической среды
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class SchedulerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.system = "linux"
        self.title("Linux Sleep Scheduler")
        self.geometry("800x600")
        self.minsize(600, 500)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Загружаем иконку приложения
        try:
            icon_path = resource_path("sleep_scheduler.png")
            self.print_log(f"Загрузка иконки из: {icon_path}")
            img = Image.open(icon_path)
            icon = ImageTk.PhotoImage(img)
            self.after(100, lambda: self.iconphoto(False, icon))
            self.print_log("Иконка успешно загружена")
        except Exception as e:
            self.print_log(f"Ошибка загрузки иконки: {e}")
            # Создаем простую иконку как fallback
            try:
                from PIL import ImageDraw
                img = Image.new('RGB', (32, 32), color='#1e88e5')
                d = ImageDraw.Draw(img)
                d.ellipse((5, 5, 27, 27), fill='#0d47a1')
                icon = ImageTk.PhotoImage(img)
                self.after(100, lambda: self.iconphoto(False, icon))
            except:
                pass

        # Настройка сетки главного окна
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Создание вкладок
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tabview.add("Управление")
        self.tabview.add("Планировщик")
        self.tabview.add("Настройки")
        
        self.control_tab = self.tabview.tab("Управление")
        self.schedule_tab = self.tabview.tab("Планировщик")
        self.settings_tab = self.tabview.tab("Настройки")
        
        # Инициализация интерфейса
        self.setup_control_tab()
        self.setup_schedule_tab()
        self.setup_settings_tab()
        
        # Загрузка настроек
        self.settings_file = "/etc/sleep-scheduler.json"
        self.settings = {
            "time_format": "24ч",
            "autostart": 1,
            "schedules": []
        }
        self.load_settings()

        # Флаг работы фонового потока
        self.running = True
        
        # Запуск фонового потока для проверки событий
        self.check_thread = threading.Thread(target=self.check_scheduled_events, daemon=True)
        self.check_thread.start()
        
        self.print_log(f"Приложение запущено под {self.get_system_info()}")

    def print_log(self, message):
        """Логирование в консоль и в файл для отладки"""
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        print(f"{timestamp} {message}")

    def setup_control_tab(self):
        """Настройка вкладки управления"""
        self.control_tab.grid_columnconfigure(0, weight=1)
        for i in range(6):
            self.control_tab.grid_rowconfigure(i, weight=0 if i < 5 else 1)
            
        # Кнопки действий
        actions = ["Выключить", "Перезагрузка", "Сон", "Гибернация"]
        for i, action in enumerate(actions):
            btn = ctk.CTkButton(
                self.control_tab,
                text=action,
                command=lambda a=action: self.execute_action(a),
                height=40,
                font=("Arial", 14)
            )
            btn.grid(row=i, column=0, padx=20, pady=10, sticky="ew")
        
        # Кнопка быстрого выполнения
        self.execute_btn = ctk.CTkButton(
            self.control_tab,
            text="Выполнить сейчас (с задержкой)",
            command=self.show_quick_action_dialog,
            fg_color="#D9534F",
            height=40,
            font=("Arial", 14, "bold")
        )
        self.execute_btn.grid(row=5, column=0, padx=20, pady=5, sticky="ew")
        
        # Лог-поле
        self.log_text = ctk.CTkTextbox(self.control_tab, font=("Monospace", 10))
        self.log_text.grid(row=6, column=0, padx=20, pady=5, sticky="nsew")
        self.log("Система управления питанием инициализирована")
        self.log(f"Пользователь: {getpass.getuser()}")

    def setup_schedule_tab(self):
        """Настройка вкладки планировщика"""
        self.schedule_tab.grid_columnconfigure(0, weight=1)
        self.schedule_tab.grid_rowconfigure(0, weight=0)
        self.schedule_tab.grid_rowconfigure(1, weight=1)
        
        # Форма добавления задачи
        form_frame = ctk.CTkFrame(self.schedule_tab)
        form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        form_frame.grid_columnconfigure(0, weight=0)
        form_frame.grid_columnconfigure(1, weight=1)
        form_frame.grid_columnconfigure(2, weight=0)
        form_frame.grid_columnconfigure(3, weight=1)
        form_frame.grid_columnconfigure(4, weight=0)
        form_frame.grid_columnconfigure(5, weight=1)
        
        row = 0
        
        # Выбор действия
        ctk.CTkLabel(form_frame, text="Действие:", anchor="w").grid(
            row=row, column=0, padx=5, pady=5, sticky="w")
        self.action_var = tk.StringVar(value="Выключить")
        action_menu = ctk.CTkComboBox(
            form_frame,
            values=["Выключить", "Перезагрузка", "Сон", "Гибернация"],
            variable=self.action_var,
            width=150
        )
        action_menu.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        
        # Поле времени
        ctk.CTkLabel(form_frame, text="Время (ЧЧ:ММ):", anchor="w").grid(
            row=row, column=2, padx=5, pady=5, sticky="w")
        self.time_var = tk.StringVar(value=datetime.now().strftime("%H:%M"))
        time_entry = ctk.CTkEntry(
            form_frame, 
            textvariable=self.time_var, 
            width=100,
            placeholder_text="HH:MM"
        )
        time_entry.grid(row=row, column=3, padx=5, pady=5, sticky="ew")
        
        # Выбор повторения
        ctk.CTkLabel(form_frame, text="Повтор:", anchor="w").grid(
            row=row, column=4, padx=5, pady=5, sticky="w")
        self.repeat_var = tk.StringVar(value="Один раз")
        repeat_menu = ctk.CTkComboBox(
            form_frame,
            values=["Один раз", "Ежедневно", "По будням", "По выходным"],
            variable=self.repeat_var,
            width=150
        )
        repeat_menu.grid(row=row, column=5, padx=5, pady=5, sticky="ew")
        row += 1
        
        # Кнопка добавления
        add_btn = ctk.CTkButton(
            form_frame,
            text="Добавить задание",
            command=self.add_schedule,
            height=35,
            font=("Arial", 12)
        )
        add_btn.grid(row=row, column=0, columnspan=6, padx=10, pady=(0, 5), sticky="ew")
        
        # Список задач
        self.task_scroll = ctk.CTkScrollableFrame(self.schedule_tab)
        self.task_scroll.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.task_scroll.grid_columnconfigure(0, weight=1)
        self.task_container = self.task_scroll

    def setup_settings_tab(self):
        """Настройка вкладки с параметрами"""
        self.settings_tab.grid_columnconfigure(0, weight=1)
        self.settings_tab.grid_rowconfigure(0, weight=0)
        self.settings_tab.grid_rowconfigure(1, weight=1)
        self.settings_tab.grid_rowconfigure(2, weight=0)
        
        # Настройки приложения
        settings_frame = ctk.CTkFrame(self.settings_tab)
        settings_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        settings_frame.grid_columnconfigure(0, weight=1)
        
        row = 0
        ctk.CTkLabel(
            settings_frame, 
            text="Формат времени:",
            font=("Arial", 12),
            anchor="w"
        ).grid(row=row, column=0, padx=5, pady=5, sticky="w")
        
        time_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        time_frame.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        time_frame.grid_columnconfigure(0, weight=0)
        time_frame.grid_columnconfigure(1, weight=0)
        
        self.time_format = tk.StringVar(value="24ч")
        ctk.CTkRadioButton(
            time_frame, text="24-часовой", 
            variable=self.time_format, value="24ч"
        ).grid(row=0, column=0, padx=5, sticky="w")
        ctk.CTkRadioButton(
            time_frame, text="12-часовой", 
            variable=self.time_format, value="12ч"
        ).grid(row=0, column=1, padx=5, sticky="w")
        row += 1
        
        ctk.CTkLabel(
            settings_frame, 
            text="Автозапуск:",
            font=("Arial", 12),
            anchor="w"
        ).grid(row=row, column=0, padx=5, pady=5, sticky="w")
        
        self.autostart = tk.IntVar(value=1)
        switch = ctk.CTkSwitch(
            settings_frame, 
            text="Запускать автоматически при входе",
            variable=self.autostart,
            onvalue=1, offvalue=0
        )
        switch.grid(row=row, column=1, padx=5, pady=5, sticky="w")
        row += 1
        
        # Информация о системе
        info_frame = ctk.CTkFrame(self.settings_tab)
        info_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        info_frame.grid_rowconfigure(0, weight=1)
        info_frame.grid_columnconfigure(0, weight=1)
        
        sys_info = self.get_system_info()
        info_text = (
            f"• Операционная система: {sys_info}\n"
            f"• Версия приложения: 1.2\n"
            f"• Текущий пользователь: {getpass.getuser()}\n"
            f"• Путь программы: {os.path.abspath(__file__)}\n\n"
            "Для управления питанием используются команды systemctl:\n"
            "poweroff, reboot, suspend, hibernate"
        )
        
        info_label = ctk.CTkTextbox(
            info_frame,
            wrap="word",
            font=("Monospace", 11),
            height=150
        )
        info_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        info_label.insert("1.0", info_text)
        info_label.configure(state="disabled")
        
        # Кнопки сохранения
        btn_frame = ctk.CTkFrame(self.settings_tab, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=10, pady=10)
        
        self.save_btn = ctk.CTkButton(
            btn_frame,
            text="Сохранить настройки",
            command=self.save_settings,
            width=200,
            height=40
        )
        self.save_btn.pack(side="left", padx=20)
        
        self.reload_btn = ctk.CTkButton(
            btn_frame,
            text="Перезагрузить сервис",
            command=self.restart_service,
            width=200,
            height=40,
            fg_color="#5BC0DE"
        )
        self.reload_btn.pack(side="left", padx=20)

    def get_system_info(self):
        """Получение информации об ОС"""
        try:
            # Для систем на основе Debian/Ubuntu
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            return line.split('=')[1].strip().strip('"')
            
            # Для RedHat/CentOS
            elif os.path.exists("/etc/redhat-release"):
                with open("/etc/redhat-release", "r") as f:
                    return f.read().strip()
            
            # Общая информация о ядре
            return f"Linux {os.uname().sysname} {os.uname().release}"
        
        except Exception as e:
            self.log(f"Ошибка получения системной информации: {str(e)}")
            return "Неизвестная Linux-система"

    def execute_action(self, action):
        """Выполнение действия с системой"""
        # Команды для Linux систем
        commands = {
            "Выключить": "systemctl poweroff",
            "Перезагрузка": "systemctl reboot",
            "Сон": "systemctl suspend",
            "Гибернация": "systemctl hibernate"
        }
        
        custom_msg = ""
        if action == "Гибернация":
            # Проверка поддержки гибернации
            if subprocess.run("systemctl hibernate".split(), stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL).returncode != 0:
                custom_msg = "\n\n⚠️ Гибернация не настроена!\nТребуется:\n1. Достаточный размер swap-раздела\n2. Настройка ядра\nПопробуйте: sudo systemctl hibernate"
        
        self.log(f"Инициировано: {action}{custom_msg}")
        
        # Запускаем команду с задержкой 1с для отправки лога
        def delayed_execute():
            time.sleep(1)
            try:
                subprocess.run(commands[action].split(), check=True)
            except Exception as e:
                self.log(f"Ошибка выполнения: {str(e)}{custom_msg}")
                messagebox.showerror("Ошибка действия", f"{str(e)}{custom_msg}")
        
        threading.Thread(target=delayed_execute, daemon=True).start()

    def log(self, message):
        """Логирование в текстовом поле"""
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{timestamp} {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.print_log(message)

    def show_quick_action_dialog(self):
        """Диалог быстрого выполнения с задержкой"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Выполнить действие с задержкой")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Выберите действие:", font=("Arial", 14)).pack(pady=10)
        
        action_var = tk.StringVar(value="Выключить")
        action_menu = ctk.CTkComboBox(
            dialog,
            values=["Выключить", "Перезагрузка", "Сон", "Гибернация"],
            variable=action_var,
            width=200
        )
        action_menu.pack(pady=5)
        
        ctk.CTkLabel(dialog, text="Задержка выполнения (минуты):", font=("Arial", 12)).pack(pady=10)
        
        delay_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        delay_frame.pack(fill="x", padx=50)
        
        delay_var = tk.StringVar(value="10")
        delay_slider = ctk.CTkSlider(
            delay_frame, 
            from_=0, to=120, 
            variable=delay_var,
            number_of_steps=60,
            width=200
        )
        delay_slider.pack(side="left")
        
        delay_label = ctk.CTkLabel(delay_frame, textvariable=delay_var, width=50)
        delay_label.pack(side="right", padx=10)
        
        def confirm_action():
            try:
                action = action_var.get()
                minutes = int(delay_var.get())
                
                if minutes < 0:
                    raise ValueError("Отрицательное время")
                
                if minutes > 0:
                    self.log(f"Запланировано '{action}' через {minutes} мин.")
                    # Планируем выполнение в отдельном потоке
                    threading.Timer(minutes * 60, self.execute_action, args=[action]).start()
                    messagebox.showinfo(
                        "Действие запланировано", 
                        f"{action} будет выполнен через {minutes} минут"
                    )
                else:
                    self.execute_action(action)
                
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Ошибка", "Некорректное значение времени")
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(
            btn_frame, text="Подтвердить", 
            command=confirm_action, width=120
        ).pack(side="left", padx=20)
        
        ctk.CTkButton(
            btn_frame, text="Отмена", 
            command=dialog.destroy, fg_color="gray", width=120
        ).pack(side="right", padx=20)

    def add_schedule(self):
        """Добавление задачи в планировщик"""
        action = self.action_var.get()
        time_str = self.time_var.get()
        repeat = self.repeat_var.get()
        
        try:
            # Проверка формата времени
            datetime.strptime(time_str, "%H:%M")
            
            # Генерируем уникальный ID задания
            task_id = f"{action}-{time_str}-{int(time.time())}"
            task_name = f"{action} в {time_str} ({repeat})"
            
            # Создаем UI элемент задачи
            task_frame = ctk.CTkFrame(
                self.task_container, 
                fg_color=("gray90", "gray10")
            )
            task_frame.pack(fill="x", padx=5, pady=2)
            
            ctk.CTkLabel(
                task_frame, text=task_name, 
                font=("Arial", 12),
                anchor="w"
            ).pack(side="left", padx=10, pady=5, fill="x", expand=True)
            
            delete_btn = ctk.CTkButton(
                task_frame, 
                text="Удалить", 
                width=80,
                height=24,
                font=("Arial", 10),
                fg_color="#D9534F",
                hover_color="#C9302C",
                command=lambda t=task_id, f=task_frame: self.delete_schedule(t, f)
            )
            delete_btn.pack(side="right", padx=5, pady=2)
            
            # Сохраняем задачу в настройках
            self.settings["schedules"].append({
                "id": task_id,
                "action": action,
                "time": time_str,
                "repeat": repeat
            })
            
            self.save_settings()
            self.log(f"Добавлена задача: {task_name}")
            
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат времени!\nИспользуйте ЧЧ:ММ (например 22:30)")

    def delete_schedule(self, task_id, frame):
        """Удаление задачи из планировщика"""
        self.settings["schedules"] = [t for t in self.settings["schedules"] if t["id"] != task_id]
        frame.destroy()
        self.save_settings()
        self.log(f"Задача удалена")

    def check_scheduled_events(self):
        """Фоновая проверка задач по расписанию"""
        while self.running:
            now = datetime.now().strftime("%H:%M")
            
            # Проверяем каждое задание
            for task in list(self.settings["schedules"]):
                if self.should_execute(task, now):
                    self.log(f"Выполнение по расписанию: {task['action']}")
                    self.execute_action(task["action"])
                    
                    # Удаляем разовые задания
                    if task["repeat"] == "Один раз":
                        self.settings["schedules"].remove(task)
                        self.save_settings()
                        self.remove_task_from_ui(task["id"])
            
            # Проверяем каждые 15 секунд
            for _ in range(15):
                if not self.running:
                    break
                time.sleep(1)

    def should_execute(self, task, current_time):
        """Определяет, нужно ли выполнять задачу сейчас"""
        if task["time"] != current_time:
            return False
            
        today = datetime.today()
        weekday = today.weekday()  # 0=пн, 6=вс
        
        if task["repeat"] == "Ежедневно":
            return True
        elif task["repeat"] == "По будням":
            return weekday < 5  # Пн-Пт
        elif task["repeat"] == "По выходным":
            return weekday >= 5  # Сб-Вс
        else:  # Один раз
            return True

    def remove_task_from_ui(self, task_id):
        """Удаляет задачу из интерфейса"""
        for widget in self.task_container.winfo_children():
            if hasattr(widget, 'task_id') and widget.task_id == task_id:
                widget.destroy()
                break

    def load_settings(self):
        """Загрузка настроек из файла"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r") as f:
                    self.settings = json.load(f)
        except json.JSONDecodeError:
            self.log("Ошибка чтения настроек: файл поврежден")
        except Exception as e:
            self.log(f"Ошибка загрузки настроек: {str(e)}")
        finally:
            self.update_ui_from_settings()

    def update_ui_from_settings(self):
        """Обновление UI на основе загруженных настроек"""
        # Восстановление задач
        for widget in self.task_container.winfo_children():
            widget.destroy()
            
        for task in self.settings.get("schedules", []):
            task_frame = ctk.CTkFrame(
                self.task_container, 
                fg_color=("gray90", "gray10")
            )
            task_frame.pack(fill="x", padx=5, pady=2)
            task_frame.task_id = task["id"]  # Сохраняем ID для последующего удаления
            
            task_name = f"{task['action']} в {task['time']} ({task['repeat']})"
            ctk.CTkLabel(
                task_frame, text=task_name, 
                font=("Arial", 12),
                anchor="w"
            ).pack(side="left", padx=10, pady=5, fill="x", expand=True)
            
            delete_btn = ctk.CTkButton(
                task_frame, 
                text="Удалить", 
                width=80,
                height=24,
                font=("Arial", 10),
                fg_color="#D9534F",
                hover_color="#C9302C",
                command=lambda t=task['id'], f=task_frame: self.delete_schedule(t, f)
            )
            delete_btn.pack(side="right", padx=5, pady=2)

    def save_settings(self):
        """Сохраняем настройки в файл"""
        try:
            # Создаем временный файл для безопасной записи
            temp_file = self.settings_file + ".tmp"
            with open(temp_file, "w") as f:
                json.dump(self.settings, f, indent=2)
            
            # Заменяем оригинальный файл
            os.replace(temp_file, self.settings_file)
            self.log("Настройки успешно сохранены")
            return True
        except Exception as e:
            self.log(f"Ошибка сохранения настроек: {str(e)}")
            messagebox.showerror(
                "Ошибка сохранения", 
                f"Не удалось сохранить настройки: {str(e)}\n"
                "Убедитесь, что программа запущена с правами администратора"
            )
            return False

    def restart_service(self):
        """Перезапуск системного сервиса (для применения настроек)"""
        try:
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            self.log("Системные службы обновлены")
            messagebox.showinfo("Службы обновлены", "Настройки были успешно применены")
        except subprocess.CalledProcessError as e:
            self.log(f"Ошибка перезагрузки служб: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось обновить службы: {str(e)}")

    def on_closing(self):
        """Действия при закрытии приложения"""
        self.log("Завершение работы приложения...")
        self.running = False
        time.sleep(0.5)  # Даем время потокам остановиться
        
        # Сохраняем настройки только если это основной процесс
        if os.geteuid() == 0:
            self.save_settings()
        
        self.destroy()
        self.print_log("Приложение корректно завершено")

if __name__ == "__main__":
    # Перехват исключений для создания логов
    try:
        app = SchedulerApp()
        app.mainloop()
    except Exception as e:
        error_msg = f"CRITICAL ERROR: {str(e)}\n"
        with open("/tmp/sleep_scheduler_crash.log", "a") as f:
            f.write(error_msg)
            f.write("--- TRACEBACK ---\n")
            import traceback
            traceback.print_exc(file=f)
        messagebox.showerror(
            "Critical Error", 
            f"Программа аварийно завершилась:\n{error_msg}\n"
            "Детали смотрите в /tmp/sleep_scheduler_crash.log"
        )