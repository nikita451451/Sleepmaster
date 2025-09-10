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

# Помощник для путей ресурсов
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Проверка прав доступа
if os.geteuid() != 0:
    print("Перезапуск с правами sudo...")
    subprocess.call(['sudo', sys.executable] + sys.argv)
    sys.exit(0)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class SchedulerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.system = "linux"
        self.title("Linux Sleep Scheduler")
        self.geometry("500x500")
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Установка иконки
        try:
            img = Image.open(resource_path("sleep_scheduler.png"))
            icon = ImageTk.PhotoImage(img)
            self.after(100, lambda: self.iconphoto(False, icon))
        except Exception as e:
            print(f"Ошибка загрузки иконки: {e}")

        # Настройка сетки
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Вкладки
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Создание вкладок
        self.control_tab = self.tabview.add("Управление")
        self.schedule_tab = self.tabview.add("Планировщик")
        self.settings_tab = self.tabview.add("Настройки")
        
        # Инициализация интерфейса
        self.setup_control_tab()
        self.setup_schedule_tab()
        self.setup_settings_tab()
        
        # Загрузка настроек
        self.settings_file = "/etc/sleep-scheduler.json"
        self.load_settings()

        # Флаг работы потока
        self.running = True
        
        # Запуск потока проверки
        self.check_thread = threading.Thread(target=self.check_scheduled_events, daemon=True)
        self.check_thread.start()

    def setup_control_tab(self):
        # Сетка вкладки управления
        self.control_tab.grid_columnconfigure(0, weight=1)
        for i in range(5):
            self.control_tab.grid_rowconfigure(i, weight=1)
            
        # Кнопки действий
        actions = ["Выключить", "Перезагрузка", "Сон", "Гибернация"]
        for i, action in enumerate(actions):
            btn = ctk.CTkButton(
                self.control_tab,
                text=action,
                command=lambda a=action: self.execute_action(a)
            )
            btn.grid(row=i, column=0, padx=20, pady=10, sticky="ew")
        
        # Кнопка быстрого выполнения
        self.execute_btn = ctk.CTkButton(
            self.control_tab,
            text="Выполнить сейчас",
            command=self.show_quick_action_dialog,
            fg_color="#D9534F"
        )
        self.execute_btn.grid(row=4, column=0, padx=20, pady=20, sticky="ew")
        
        # Логгер
        self.log_text = ctk.CTkTextbox(self.control_tab, height=100)
        self.log_text.grid(row=5, column=0, padx=20, pady=20, sticky="nsew")
        self.log("Приложение успешно запущено")

    def setup_schedule_tab(self):
        # Сетка вкладки планировщика
        self.schedule_tab.grid_columnconfigure(0, weight=1)
        
        # Форма добавления
        form_frame = ctk.CTkFrame(self.schedule_tab)
        form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(form_frame, text="Действие:").grid(row=0, column=0, padx=5, pady=5)
        self.action_var = tk.StringVar(value="Выключить")
        action_menu = ctk.CTkOptionMenu(
            form_frame,
            values=["Выключить", "Перезагрузка", "Сон", "Гибернация"],
            variable=self.action_var
        )
        action_menu.grid(row=0, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(form_frame, text="Время:").grid(row=0, column=2, padx=5, pady=5)
        self.time_var = tk.StringVar(value="23:00")
        time_entry = ctk.CTkEntry(form_frame, textvariable=self.time_var, width=85)
        time_entry.grid(row=0, column=3, padx=5, pady=5)
        
        ctk.CTkLabel(form_frame, text="Повторять:").grid(row=0, column=4, padx=5, pady=5)
        self.repeat_var = tk.StringVar(value="Один раз")
        repeat_menu = ctk.CTkOptionMenu(
            form_frame,
            values=["Один раз", "Ежедневно", "По будням", "По выходным"],
            variable=self.repeat_var
        )
        repeat_menu.grid(row=0, column=5, padx=5, pady=5)
        
        add_btn = ctk.CTkButton(
            form_frame,
            text="Добавить",
            command=self.add_schedule,
            width=80
        )
        add_btn.grid(row=0, column=6, padx=5, pady=5)
        
        # Список задач
        scroll_frame = ctk.CTkScrollableFrame(
            self.schedule_tab,
            height=300
        )
        scroll_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        scroll_frame.grid_columnconfigure(0, weight=1)
        self.task_frame = scroll_frame

    def setup_settings_tab(self):
        self.settings_tab.grid_columnconfigure(0, weight=1)
        
        settings_frame = ctk.CTkFrame(self.settings_tab)
        settings_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # Настройки
        ctk.CTkLabel(settings_frame, text="Формат времени:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.time_format = tk.StringVar(value="24ч")
        ctk.CTkRadioButton(settings_frame, text="24 часа", variable=self.time_format, value="24ч"
                          ).grid(row=0, column=1, padx=5, sticky="w")
        ctk.CTkRadioButton(settings_frame, text="12 часов", variable=self.time_format, value="12ч"
                          ).grid(row=0, column=2, padx=5, sticky="w")
        
        ctk.CTkLabel(settings_frame, text="Автостарт:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.autostart = tk.IntVar(value=1)
        ctk.CTkCheckBox(settings_frame, text="Запускать автоматически", variable=self.autostart
                       ).grid(row=1, column=1, columnspan=2, padx=5, sticky="w")
        
        # Информация
        info_frame = ctk.CTkFrame(self.settings_tab)
        info_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        info = (
            f"OS: {self.get_system_info()}\n"
            f"Версия: 1.1\n"
            f"Пользователь: {getpass.getuser()}\n"
            f"Путь: {os.path.abspath(__file__)}\n\n"
            "Приложение работает через systemctl для управления питанием системы"
        )
        
        ctk.CTkLabel(info_frame, text=info, justify="left"
                    ).pack(padx=10, pady=10, fill="both", expand=True)
        
        # Сохранение
        save_btn = ctk.CTkButton(
            self.settings_tab,
            text="Сохранить настройки",
            command=self.save_settings,
            width=150
        )
        save_btn.grid(row=2, column=0, pady=(0, 10))

    # Системная информация
    def get_system_info(self):
        try:
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split('=')[1].strip().strip('"')
        except:
            pass
        return "Linux " + os.uname().release

    # Действия
    def execute_action(self, action):
        commands = {
            "Выключить": "poweroff",
            "Перезагрузка": "reboot",
            "Сон": "suspend",
            "Гибернация": "hibernate"
        }
        
        self.log(f"Выполняется: {action}")
        try:
            subprocess.run(["systemctl", commands[action]], check=True)
        except Exception as e:
            self.log(f"Ошибка: {str(e)}")

    # Логирование
    def log(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{timestamp} {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
    
    # Быстрое выполнение
    def show_quick_action_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Немедленное выполнение")
        dialog.geometry("300x200")
        dialog.attributes('-topmost', True)
        dialog.transient(self)
        dialog.grab_set()
        
        action_var = tk.StringVar(value="Выключить")
        ctk.CTkLabel(dialog, text="Действие:").pack(pady=5)
        
        action_menu = ctk.CTkOptionMenu(
            dialog,
            values=["Выключить", "Перезагрузка", "Сон", "Гибернация"],
            variable=action_var
        )
        action_menu.pack(pady=5)
        
        ctk.CTkLabel(dialog, text="Задержка (минуты):").pack(pady=5)
        delay_var = tk.StringVar(value="0")
        delay_entry = ctk.CTkEntry(dialog, textvariable=delay_var, width=50)
        delay_entry.pack(pady=5)
        
        def execute():
            try:
                action = action_var.get()
                minutes = max(0, int(delay_var.get()))
                
                if minutes > 0:
                    self.log(f"Запланировано {action} через {minutes} мин.")
                    threading.Timer(minutes*60, lambda: self.execute_action(action)).start()
                else:
                    self.execute_action(action)
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Ошибка", "Некорректное число минут")
        
        ctk.CTkButton(dialog, text="Выполнить", command=execute
                      ).pack(pady=15, padx=20, fill="x")
    
    # Управление расписанием
    def add_schedule(self):
        action = self.action_var.get()
        time_str = self.time_var.get()
        repeat = self.repeat_var.get()
        
        try:
            # Проверка времени
            datetime.strptime(time_str, "%H:%M")
            
            # Создаем элемент
            task_id = f"{action}-{time_str}-{datetime.now().timestamp()}"
            task_name = f"{action} в {time_str} ({repeat})"
            
            task_frame = ctk.CTkFrame(self.task_frame)
            task_frame.pack(fill="x", padx=5, pady=2)
            
            ctk.CTkLabel(task_frame, text=task_name, width=300).pack(side="left", padx=5)
            
            delete_btn = ctk.CTkButton(
                task_frame, 
                text="❌", 
                width=30, 
                height=20,
                command=lambda t=task_id, f=task_frame: self.delete_schedule(t, f)
            )
            delete_btn.pack(side="right", padx=2)
            
            # Сохраняем задание
            self.settings["schedules"].append({
                "id": task_id,
                "action": action,
                "time": time_str,
                "repeat": repeat
            })
            
            self.save_settings()
            self.log(f"Добавлено задание: {task_name}")
            
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат времени. Используйте ЧЧ:ММ")

    def delete_schedule(self, task_id, frame):
        self.settings["schedules"] = [t for t in self.settings["schedules"] if t["id"] != task_id]
        frame.destroy()
        self.save_settings()
        self.log(f"Задание удалено")

    # Проверка расписания
    def check_scheduled_events(self):
        while self.running:
            now = datetime.now().strftime("%H:%M")
            
            for task in self.settings["schedules"][:]:
                if self.should_execute(task, now):
                    self.execute_action(task["action"])
                    if task["repeat"] == "Один раз":
                        self.settings["schedules"].remove(task)
                        self.save_settings()
            
            time.sleep(30)  # Проверка каждые 30 сек

    def should_execute(self, task, current_time):
        if task["time"] != current_time:
            return False
            
        today = datetime.today()
        
        if task["repeat"] == "Ежедневно":
            return True
        if task["repeat"] == "По будням":
            return today.weekday() < 5  # Пн-Пт
        if task["repeat"] == "По выходным":
            return today.weekday() >= 5  # Сб-Вс
            
        return True  # Для "Один раз"

    # Настройки
    def load_settings(self):
        default_settings = {
            "time_format": "24ч",
            "autostart": 1,
            "schedules": []
        }
        
        try:
            with open(self.settings_file, "r") as f:
                self.settings = json.load(f)
                # Объединение с настройками по умолчанию
                for key, value in default_settings.items():
                    if key not in self.settings:
                        self.settings[key] = value
        except:
            self.settings = default_settings
        
        # Применение
        self.time_format.set(self.settings["time_format"])
        self.autostart.set(self.settings["autostart"])
        
        # Восстановление расписания
        for task in self.settings["schedules"]:
            task_frame = ctk.CTkFrame(self.task_frame)
            task_frame.pack(fill="x", padx=5, pady=2)
            
            task_name = f"{task['action']} в {task['time']} ({task['repeat']})"
            ctk.CTkLabel(task_frame, text=task_name, width=300).pack(side="left", padx=5)
            
            delete_btn = ctk.CTkButton(
                task_frame, 
                text="❌", 
                width=30, 
                height=20,
                command=lambda t=task['id'], f=task_frame: self.delete_schedule(t, f)
            )
            delete_btn.pack(side="right", padx=2)

    def save_settings(self):
        self.settings["time_format"] = self.time_format.get()
        self.settings["autostart"] = self.autostart.get()
        
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            self.log(f"Ошибка сохранения настроек: {e}")

    # Закрытие
    def on_closing(self):
        self.running = False
        self.save_settings()
        self.destroy()
        print("Приложение успешно закрыто")

if __name__ == "__main__":
    try:
        app = SchedulerApp()
        app.mainloop()
    except PermissionError:
        print("Недостаточно прав! Запустите с sudo.")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()