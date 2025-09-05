import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import platform
import datetime
import json
import time
import threading
import queue
import re
from PIL import Image, ImageTk

CONFIG_FILE = os.path.expanduser("~/.sleep_scheduler.json")
APP_NAME = "Sleep Scheduler"
APP_VERSION = "1.6"

def resource_path(relative_path):
    """Получение абсолютного пути к ресурсам для PyInstaller и обычного запуска"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    path = os.path.join(base_path, relative_path)
    
    # Исправление для Linux, где чувствительная к регистру ФС
    if not os.path.exists(path) and platform.system() == "Linux":
        dir_name = os.path.dirname(path)
        file_name = os.path.basename(path)
        if os.path.exists(dir_name):
            actual_files = os.listdir(dir_name)
            for actual_file in actual_files:
                if actual_file.lower() == file_name.lower():
                    return os.path.join(dir_name, actual_file)
        print(f"Resource not found: {path}")
    return path

class MediaApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        
        # Идентификаторы для обновления времени
        self.time_update_id = None
        self.status_time_id = None
        
        # Определение ОС
        self.is_linux = platform.system() == "Linux"
        self.is_windows = platform.system() == "Windows"
        self.linux_desktop = self.detect_linux_desktop() if self.is_linux else None
        
        # Установка иконки
        self.set_app_icon()
        
        # Настройка геометрии окна
        self.set_window_geometry()
        
        # Обработчики событий
        self.root.bind("<Configure>", self.on_window_resize)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Очередь сообщений для межпоточного взаимодействия
        self.message_queue = queue.Queue()
        
        # Создание интерфейса
        self.create_ui()
        
        # Загрузка расписания
        self.schedule = self.load_schedule()
        
        # Запуск фонового планировщика
        self.scheduler_running = True
        self.start_scheduler_thread()
        
        # Проверка очереди и запуск обновления времени
        self.root.after(100, self.check_queue)
        self.root.after(100, self.raise_to_top)
        self.start_time_updates()

    def detect_linux_desktop(self):
        """Определение типа окружения Linux"""
        if os.environ.get('XDG_CURRENT_DESKTOP'):
            return os.environ['XDG_CURRENT_DESKTOP'].split(':')[-1].lower()
        if os.environ.get('GNOME_DESKTOP_SESSION_ID'):
            return 'gnome'
        if os.environ.get('KDE_FULL_SESSION'):
            return 'kde'
        return 'unknown'

    def set_app_icon(self):
        """Установка иконки с учетом платформы"""
        try:
            if self.is_windows:
                icon_path = resource_path('sleep_scheduler.ico')
                if os.path.exists(icon_path):
                    self.root.iconbitmap(default=icon_path)
            elif self.is_linux:
                # Пробуем найти иконку в разных форматах
                for ext in ['.png', '.ico', '.xpm']:
                    icon_path = resource_path(f'sleep_scheduler{ext}')
                    if os.path.exists(icon_path):
                        try:
                            img = Image.open(icon_path)
                            # Уменьшаем большие изображения для Linux
                            if img.width > 128 or img.height > 128:
                                img = img.resize((128, 128), Image.LANCZOS)
                            pimg = ImageTk.PhotoImage(img)
                            self.root.tk.call('wm', 'iconphoto', self.root._w, pimg)
                            break
                        except Exception as e:
                            print(f"Error loading icon: {str(e)}")
        except Exception as e:
            print(f"Icon setting error: {str(e)}")

    def set_window_geometry(self):
        """Установка размеров окна"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        width = 400
        height = 500
        x = (screen_width - width) // 2
        y = (screen_height - height) // 3
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(380, 450)
        self.window_width = width
        self.window_height = height

    def start_time_updates(self):
        """Запуск обновления времени"""
        self.update_time_label()
        self.update_status_time()

    def raise_to_top(self):
        """Поднимаем окно наверх"""
        self.root.attributes('-topmost', True)
        self.root.after(50, lambda: self.root.attributes('-topmost', False))
        self.root.focus_force()

    def on_close(self):
        """Обработка закрытия окна"""
        if self.is_linux:
            if messagebox.askyesno("Подтверждение", 
                                   "Закрыть приложение?",
                                   detail="'Да' - закрыть приложение, 'Нет' - свернуть в трей"):
                self.root.destroy()
            else:
                self.minimize_to_tray()
        else:
            self.minimize_to_tray()

    def on_destroy(self, event):
        """Корректное завершение приложения"""
        if event.widget == self.root:
            # Отменяем обновление времени
            if self.time_update_id:
                self.root.after_cancel(self.time_update_id)
            if self.status_time_id:
                self.root.after_cancel(self.status_time_id)
                
            self.scheduler_running = False
            if hasattr(self, 'scheduler_thread') and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=1.0)

    def on_window_resize(self, event=None):
        """Адаптация к изменению размера окна"""
        if event and event.widget == self.root:
            if self.window_width != event.width or self.window_height != event.height:
                self.window_width = event.width
                self.window_height = event.height
                self.update_ui_size()
    
    def create_ui(self):
        # Стиль интерфейса
        self.style = ttk.Style()
        
        # Особенности настройки для Linux
        if self.is_linux:
            try:
                self.root.tk.call('lappend', 'auto_path', '/usr/share/tcltk/tk8.6/themes/')
                self.root.tk.call('package', 'require', 'ttk::theme::alt')
                self.root.tk.call('ttk::setTheme', 'alt')
                self.style.theme_use('alt')
            except:
                self.style.theme_use("clam")
        else:
            self.style.theme_use("clam")
        
        # Настройка цветов
        self.style.configure('.', background='#f0f0f0', foreground='black')
        self.style.configure('TNotebook', background='#e0e0e0')
        self.style.configure('TNotebook.Tab', background='#d0d0d0', padding=[10, 5])
        self.style.map('TNotebook.Tab', background=[('selected', '#f0f0f0')])
        
        # Создание вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Вкладки
        self.create_main_tab()
        self.create_schedule_tab()
        self.create_settings_tab()
        
        # Статусная строка
        self.status_var = tk.StringVar(value=f"Готов | {platform.system()}")
        self.status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var,
            anchor=tk.W,
            relief=tk.SUNKEN,
            font=('Arial', 9),
            padding=3,
            background='#e0e0e0'
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.update_ui_size()
        
    def create_main_tab(self):
        """Главная вкладка"""
        main_frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(main_frame, text="Главная")
        
        # Заголовок
        title_label = ttk.Label(
            main_frame, 
            text="Планировщик сна", 
            font=('Arial', 14, 'bold'),
            foreground='#2c3e50'
        )
        title_label.pack(pady=(0, 20))
        
        # Кнопка перехода в сон
        self.sleep_btn = ttk.Button(
            main_frame,
            text="Перевести в спящий режим",
            command=self.sleep_pc,
            width=25
        )
        self.sleep_btn.pack(pady=10, fill=tk.X)
        
        # Кнопка открытия медиа
        self.media_btn = ttk.Button(
            main_frame,
            text="Открыть медиафайл",
            command=self.open_media_player,
            width=25
        )
        self.media_btn.pack(pady=10, fill=tk.X)
        
        # Разделитель
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=20)
        
        # Информация о системе
        info_frame = ttk.LabelFrame(main_frame, text="Информация о системе")
        info_frame.pack(fill=tk.X, pady=5)
        
        # ОС
        os_label = ttk.Label(
            info_frame, 
            text=f"ОС: {platform.system()} {platform.release()}", 
            font=('Arial', 9)
        )
        os_label.pack(anchor=tk.W, pady=2)
        
        # Версия приложения
        version_label = ttk.Label(
            info_frame, 
            text=f"Версия: {APP_VERSION}", 
            font=('Arial', 9)
        )
        version_label.pack(anchor=tk.W, pady=2)
        
        # Метка для текущего времени
        self.time_label = ttk.Label(
            info_frame, 
            text="Время: 00:00:00", 
            font=('Arial', 9)
        )
        self.time_label.pack(anchor=tk.W, pady=2)
        
    def create_schedule_tab(self):
        """Вкладка расписания"""
        schedule_frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(schedule_frame, text="Расписание")
        
        # Заголовок
        title_label = ttk.Label(
            schedule_frame, 
            text="Настройка расписания", 
            font=('Arial', 12, 'bold')
        )
        title_label.pack(pady=(0, 15))
        
        # Фрейм списка расписания
        schedule_list_frame = ttk.LabelFrame(schedule_frame, text="Текущее расписание")
        schedule_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Список
        self.schedule_listbox = tk.Listbox(
            schedule_list_frame, 
            height=8,
            font=('Arial', 9),
            relief=tk.FLAT,
            bg='white'
        )
        scrollbar = ttk.Scrollbar(schedule_list_frame, orient=tk.VERTICAL, command=self.schedule_listbox.yview)
        self.schedule_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.schedule_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Фрейм добавления
        add_frame = ttk.Frame(schedule_frame)
        add_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(add_frame, text="День:").grid(row=0, column=0, padx=2, pady=2, sticky='e')
        self.day_var = tk.StringVar()
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        self.day_combo = ttk.Combobox(add_frame, textvariable=self.day_var, values=days, 
                                    state='readonly', width=8)
        self.day_combo.current(0)
        self.day_combo.grid(row=0, column=1, padx=2, pady=2)
        
        ttk.Label(add_frame, text="С:").grid(row=0, column=2, padx=2, pady=2, sticky='e')
        self.start_time_var = tk.StringVar(value="00:00")
        self.start_entry = ttk.Entry(add_frame, textvariable=self.start_time_var, width=6)
        self.start_entry.grid(row=0, column=3, padx=2, pady=2)
        
        ttk.Label(add_frame, text="По:").grid(row=0, column=4, padx=2, pady=2, sticky='e')
        self.end_time_var = tk.StringVar(value="00:00")
        self.end_entry = ttk.Entry(add_frame, textvariable=self.end_time_var, width=6)
        self.end_entry.grid(row=0, column=5, padx=2, pady=2)
        
        ttk.Button(
            add_frame, 
            text="Добавить",
            command=self.add_schedule_item,
            width=10
        ).grid(row=0, column=6, padx=5, pady=2)
        
        # Кнопки управления
        button_frame = ttk.Frame(schedule_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            button_frame,
            text="Удалить",
            command=self.delete_schedule_item,
            width=12
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            button_frame,
            text="Очистить все",
            command=self.clear_schedule,
            width=12
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            button_frame,
            text="Сохранить",
            command=self.save_schedule_config,
            width=12
        ).pack(side=tk.RIGHT, padx=2)
        
    def create_settings_tab(self):
        """Вкладка настроек"""
        settings_frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(settings_frame, text="Настройки")
        
        title_label = ttk.Label(
            settings_frame, 
            text="Настройки приложения", 
            font=('Arial', 12, 'bold')
        )
        title_label.pack(pady=(0, 15))
        
        # Настройки автозапуска
        autostart_frame = ttk.LabelFrame(settings_frame, text="Автозапуск")
        autostart_frame.pack(fill=tk.X, pady=5)
        
        self.autostart_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            autostart_frame, 
            text="Запускать при старте системы",
            variable=self.autostart_var,
            command=self.toggle_autostart
        ).pack(anchor=tk.W, pady=5, padx=10)
        
        # Настройки уведомлений
        notify_frame = ttk.LabelFrame(settings_frame, text="Уведомления")
        notify_frame.pack(fill=tk.X, pady=5)
        
        self.notify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            notify_frame, 
            text="Показывать уведомления",
            variable=self.notify_var
        ).pack(anchor=tk.W, pady=5, padx=10)
        
        # Кнопки управления настройками
        button_frame = ttk.Frame(settings_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            button_frame,
            text="Применить",
            command=self.apply_settings,
            width=15
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Сброс",
            command=self.reset_settings,
            width=15
        ).pack(side=tk.RIGHT, padx=5)
        
    def update_ui_size(self):
        """Динамическое изменение UI"""
        size_factor = min(self.window_width, self.window_height) / 500
        font_size = max(9, min(12, int(10 * size_factor)))
        
        # Обновляем стили
        self.style.configure('.', font=('Arial', font_size))
        self.style.configure('TNotebook.Tab', font=('Arial', font_size))
        
    def open_media_player(self):
        filetypes = (
            ("Медиафайлы", "*.jpg *.jpeg *.png *.bmp *.gif *.mp4 *.avi *.mkv *.mov *.wmv"),
            ("Все файлы", "*.*")
        )
        
        path = filedialog.askopenfilename(
            title="Выберите медиафайл",
            filetypes=filetypes
        )
        
        if not path:
            return
            
        ext = os.path.splitext(path)[1].lower()
        image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
        
        try:
            if ext in image_exts:
                self.show_fullscreen_image(path)
            else:
                if self.is_linux:
                    subprocess.Popen(["xdg-open", path])
                elif self.is_windows:
                    os.startfile(path)
                else:  # macOS
                    subprocess.Popen(["open", path])
                
            self.status_var.set(f"Открыт: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть медиа: {str(e)}")

    def show_fullscreen_image(self, image_path):
        """Показ изображения в полноэкранном режиме"""
        top = tk.Toplevel(self.root)
        top.attributes('-fullscreen', True)
        top.configure(background='black')
        
        # Центрировать изображение
        screen_width = top.winfo_screenwidth()
        screen_height = top.winfo_screenheight()
        top.geometry(f"{screen_width}x{screen_height}+0+0")
        
        close_btn = ttk.Button(
            top, 
            text="Закрыть (ESC)", 
            command=top.destroy
        )
        close_btn.pack(side=tk.BOTTOM, pady=10)
        
        top.bind("<Escape>", lambda e: top.destroy())
        
        try:
            original_img = Image.open(image_path)
            img_width, img_height = original_img.size
            ratio = min(screen_width / img_width, screen_height / img_height)
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)
            
            resized_img = original_img.resize((new_width, new_height), Image.LANCZOS)
            img_tk = ImageTk.PhotoImage(resized_img)
            
            img_label = ttk.Label(top, image=img_tk)
            img_label.image = img_tk
            img_label.pack(expand=True, fill='both')
            img_label.place(relx=0.5, rely=0.5, anchor='center')
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить изображение: {str(e)}")
            top.destroy()

    def minimize_to_tray(self):
        """Свернуть в системный трей"""
        if self.is_windows:
            self.root.iconify()
        elif self.is_linux:
            self.root.iconify()
            self.root.withdraw()
            
        self.status_var.set("Свернут в трей")

    def restore_from_tray(self):
        """Восстановить из трея"""
        self.root.deiconify()
        self.status_var.set("Готов")
        self.raise_to_top()

    def start_scheduler_thread(self):
        """Запуск фонового потока планировщика"""
        self.scheduler_thread = threading.Thread(target=self.check_schedule, daemon=True)
        self.scheduler_thread.start()

    def check_schedule(self):
        """Проверка расписания каждую минуту"""
        while self.scheduler_running:
            try:
                now = datetime.datetime.now()
                current_time = now.strftime("%H:%M")
                weekday = now.weekday()  # 0-Пн, 1-Вт, ... 6-Вс
                weekday_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                current_weekday = weekday_names[weekday]
                
                for entry in self.schedule.get("sleep_times", []):
                    if not isinstance(entry, dict):
                        continue
                        
                    entry_day = entry.get("weekday", "")
                    start_time = entry.get("start_time", "00:00")
                    end_time = entry.get("end_time", "00:00")
                    
                    if entry_day != current_weekday:
                        continue
                    
                    if start_time <= current_time <= end_time:
                        self.message_queue.put(("SLEEP", ""))
                        time.sleep(120)  # Повторная проверка через 2 минуты
                        break
                    
            except Exception as e:
                print(f"Ошибка планировщика: {str(e)}")
            finally:
                time.sleep(55)  # Проверка каждую минуту

    def sleep_pc(self):
        """Запрос подтверждения перехода в спящий режим"""
        confirmation = messagebox.askyesno(
            "Подтверждение",
            "Компьютер будет переведен в спящий режим.\nПродолжить?",
            icon=messagebox.WARNING
        )
        
        if confirmation:
            threading.Thread(target=self._perform_sleep, daemon=True).start()

    def _perform_sleep(self):
        """Реализация перевода в спящий режим"""
        if self.is_windows:
            try:
                subprocess.run(
                    ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], 
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except Exception as e:
                messagebox.showerror("Ошибка", f"Windows спящий режим не удался: {str(e)}")
                
        elif self.is_linux:
            # Попробуем основные методы
            commands = [
                ["systemctl", "suspend"],
                ["loginctl", "suspend"],
                ["dbus-send", "--system", "--print-reply", 
                 "--dest=org.freedesktop.login1", "/org/freedesktop/login1", 
                 "org.freedesktop.login1.Manager.Suspend", "boolean:true"]
            ]
            
            success = False
            for cmd in commands:
                try:
                    if subprocess.run(["which", cmd[0]], stdout=subprocess.DEVNULL).returncode == 0:
                        subprocess.run(cmd, check=True)
                        success = True
                        break
                except Exception:
                    continue
            
            if not success:
                # Fallback для старых систем
                try:
                    subprocess.run(
                        ["dbus-send", "--system", "--dest=org.freedesktop.ConsoleKit", 
                         "/org/freedesktop/ConsoleKit/Manager", 
                         "org.freedesktop.ConsoleKit.Manager.Suspend", "boolean:true"]
                    )
                except Exception:
                    messagebox.showerror("Ошибка", "Не удалось найти способ перехода в спящий режим")
        else:  # macOS
            try:
                subprocess.run(["pmset", "sleepnow"])
            except Exception as e:
                messagebox.showerror("Ошибка", f"macOS sleep не удался: {str(e)}")
    
    def add_schedule_item(self):
        """Добавление нового расписания"""
        day = self.day_var.get().strip()
        start_time = self.start_time_var.get().strip()
        end_time = self.end_time_var.get().strip()
        
        if not day or not start_time or not end_time:
            messagebox.showwarning("Ошибка", "Все поля должны быть заполнены!")
            return
            
        time_pattern = r"^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$"
        if not re.match(time_pattern, start_time) or not re.match(time_pattern, end_time):
            messagebox.showerror("Ошибка", "Неверный формат времени! Используйте ЧЧ:ММ")
            return
            
        try:
            # Форматирование времени (добавляем ведущие нули)
            s_h, s_m = start_time.split(':')
            start_time = f"{int(s_h):02d}:{int(s_m):02d}"
            
            e_h, e_m = end_time.split(':')
            end_time = f"{int(e_h):02d}:{int(e_m):02d}"
            
            if start_time >= end_time:
                messagebox.showerror("Ошибка", "Время окончания должно быть позже времени начала!")
                return
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка в формате времени: {str(e)}")
            return
        
        entry = {
            "weekday": day,
            "start_time": start_time,
            "end_time": end_time
        }
        
        if "sleep_times" not in self.schedule:
            self.schedule["sleep_times"] = []
            
        self.schedule["sleep_times"].append(entry)
        self.update_schedule_list()
        
        # Сброс значений
        self.start_time_var.set("00:00")
        self.end_time_var.set("00:00")
        
    def delete_schedule_item(self):
        """Удаление выбранного пункта расписания"""
        selected = self.schedule_listbox.curselection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите запись для удаления")
            return
            
        index = selected[0]
        if len(self.schedule.get("sleep_times", [])) > index:
            self.schedule["sleep_times"].pop(index)
            self.update_schedule_list()
            
    def clear_schedule(self):
        """Очистка всего расписания"""
        if messagebox.askyesno("Подтверждение", "Очистить все расписание?"):
            self.schedule["sleep_times"] = []
            self.update_schedule_list()
            
    def update_schedule_list(self):
        """Обновление списка расписания в UI"""
        self.schedule_listbox.delete(0, tk.END)
        for entry in self.schedule.get("sleep_times", []):
            if isinstance(entry, dict):
                text = f"{entry.get('weekday', '')}: {entry.get('start_time', '')} - {entry.get('end_time', '')}"
                self.schedule_listbox.insert(tk.END, text)
                
    def save_schedule_config(self):
        """Сохранение расписания в файл"""
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.schedule, f, indent=2)
            self.status_var.set("Расписание сохранено!")
            messagebox.showinfo("Успех", "Расписание успешно сохранено!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка сохранения: {str(e)}")
            
    def apply_settings(self):
        """Применение настроек"""
        self.status_var.set("Настройки применены")
        self.toggle_autostart()
        messagebox.showinfo("Настройки", "Настройки успешно применены!")
        
    def toggle_autostart(self):
        """Включение/отключение автозапуска"""
        enabled = self.autostart_var.get()
        
        if self.is_windows:
            import winreg
            
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = APP_NAME.replace(' ', '')
            exe_path = os.path.abspath(sys.executable if hasattr(sys, 'frozen') else sys.argv[0])
            
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
                if enabled:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                    except FileNotFoundError:
                        pass
                winreg.CloseKey(key)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Невозможно настроить автозапуск: {str(e)}")
                
        elif self.is_linux:
            autostart_dir = os.path.expanduser("~/.config/autostart")
            desktop_file = os.path.join(autostart_dir, "sleep-scheduler.desktop")
            
            if enabled:
                os.makedirs(autostart_dir, exist_ok=True)
                exe_path = os.path.abspath(sys.executable if hasattr(sys, 'frozen') else sys.argv[0])
                
                desktop_entry = (
                    "[Desktop Entry]\n"
                    "Name=Sleep Scheduler\n"
                    "Type=Application\n"
                    f"Exec={exe_path}\n"
                    "Terminal=false\n"
                    "X-GNOME-Autostart-enabled=true\n"
                )
                
                with open(desktop_file, "w") as f:
                    f.write(desktop_entry)
            elif os.path.exists(desktop_file):
                os.remove(desktop_file)
        
    def reset_settings(self):
        """Сброс настроек к значениям по умолчанию"""
        if messagebox.askyesno("Подтверждение", "Сбросить все настройки к значениям по умолчанию?"):
            self.autostart_var.set(False)
            self.notify_var.set(True)
            self.status_var.set("Настройки сброшены")

    def load_schedule(self):
        """Загрузка расписания из файла"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "sleep_times" in data:
                        # Отложенное обновление UI
                        self.root.after(500, self.update_schedule_list)
                        return data
        except Exception as e:
            print(f"Ошибка загрузки расписания: {str(e)}")
            
        # Возвращаем пустое расписание
        return {"sleep_times": []}
    
    def check_queue(self):
        """Проверка очереди сообщений от планировщика"""
        try:
            while not self.message_queue.empty():
                msg_type, data = self.message_queue.get_nowait()
                if msg_type == "SLEEP":
                    self._perform_sleep()
        except queue.Empty:
            pass
        
        # Планируем следующую проверку
        if self.root.winfo_exists():
            self.root.after(100, self.check_queue)
            
    def update_time_label(self):
        """Обновление метки времени в главной вкладке"""
        if self.root.winfo_exists():
            current_time = datetime.datetime.now().strftime('%H:%M:%S')
            self.time_label.config(text=f"Время: {current_time}")
            
            # Планируем обновление каждую секунду
            self.time_update_id = self.root.after(1000, self.update_time_label)
        
    def update_status_time(self):
        """Обновление времени в статусбаре"""
        if self.root.winfo_exists():
            current_time = datetime.datetime.now().strftime('%H:%M:%S')
            status_text = f"Готов | {platform.system()} | {APP_VERSION} | {current_time}"
            self.status_var.set(status_text)
            
            # Планируем обновление
            self.status_time_id = self.root.after(1000, self.update_status_time)

if __name__ == "__main__":
    root = tk.Tk()
    
    # Глобальные стили
    style = ttk.Style()
    style.theme_use("clam")
    style.configure('.', font=('Arial', 10))
    style.configure('TButton', padding=5)
    style.configure('TFrame', background='#f0f0f0')
    
    app = MediaApp(root)
    root.mainloop()