import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageGrab
import os
import sys
import threading
from datetime import datetime
import json

try:
    from tkinterdnd2 import TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

from image_canvas import CropCanvas
from crop_algorithm import crop_and_save
import utils


VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']


class Settings:
    DEFAULT_SETTINGS = {
        'auto_naming': False,
        'auto_naming_format': '%y-%m-%d %h %n %s',
        'dont_ask_overwrite': False,
        'output_directory': '',
        'crop_width': 640,
        'crop_height': 640,
        'notification_sound': True
    }

    def __init__(self):
        self.settings_file = 'yolo_cropper_settings.json'
        self.settings = self.load_settings()

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    settings = self.DEFAULT_SETTINGS.copy()
                    settings.update(loaded)
                    return settings
        except:
            pass
        return self.DEFAULT_SETTINGS.copy()

    def save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except:
            pass

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()


class YOLOCropApp:
    DEFAULT_CROP_WIDTH = 640
    DEFAULT_CROP_HEIGHT = 640

    def __init__(self):
        self.settings = Settings()

        if DND_AVAILABLE:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()
        self.root.title('YOLO 螢幕截圖裁剪工具')
        self.root.geometry('1200x800')
        self.root.minsize(800, 600)

        self.current_image_path = None
        self.output_directory = self.settings.get('output_directory', '')
        self.last_saved_path = None
        self.folder_images = []
        self.current_folder_index = -1
        self.current_image_from_folder = None

        # Video related
        self.video_handler = None
        self.is_video_mode = False
        self.video_playback_id = None
        self.is_playing = False

        self._setup_styles()
        self._create_ui()
        self._load_settings_to_ui()
        self._setup_bindings()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('Dark.TFrame', background='#1A1A1A')
        style.configure('Dark.TLabel', background='#1A1A1A', foreground='#FFFFFF')
        style.configure('Dark.TButton', background='#2D2D2D', foreground='#FFFFFF')
        style.configure('Toolbar.TFrame', background='#2D2D2D')
        style.configure('Status.TLabel', background='#2D2D2D', foreground='#A0A0A0')
        style.configure('Nav.TButton', background='#3B3B3B', foreground='#FFFFFF')

    def _create_ui(self):
        self.root.configure(bg='#1A1A1A')

        self.toolbar = ttk.Frame(self.root, style='Toolbar.TFrame', height=50)
        self.toolbar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self._create_toolbar()

        self.nav_frame = ttk.Frame(self.root, style='Toolbar.TFrame', height=30)
        self.nav_frame.pack(side=tk.TOP, fill=tk.X, padx=10)
        self._create_navigation()

        self.main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.crop_canvas = CropCanvas(
            self.canvas_frame,
            on_crop_change=self._on_crop_change
        )
        self.crop_canvas.pack(fill=tk.BOTH, expand=True)

        self.statusbar = ttk.Frame(self.root, style='Toolbar.TFrame', height=30)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ttk.Label(
            self.statusbar,
            text='請載入圖片 (檔案對話框 / Ctrl+O 開啟資料夾 / Ctrl+V 貼上 / 拖放檔案)',
            style='Status.TLabel'
        )
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.size_label = ttk.Label(
            self.statusbar,
            text='',
            style='Status.TLabel'
        )
        self.size_label.pack(side=tk.RIGHT, padx=10)

    def _create_toolbar(self):
        self.btn_open = tk.Button(
            self.toolbar,
            text='📂 開啟檔案',
            command=self.open_file,
            bg='#1F6AA5',
            fg='#FFFFFF',
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor='hand2'
        )
        self.btn_open.pack(side=tk.LEFT, padx=5)

        self.btn_open_folder = tk.Button(
            self.toolbar,
            text='📁 開啟資料夾',
            command=self.open_folder,
            bg='#1F6AA5',
            fg='#FFFFFF',
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor='hand2'
        )
        self.btn_open_folder.pack(side=tk.LEFT, padx=5)

        self.btn_paste = tk.Button(
            self.toolbar,
            text='📋 貼上',
            command=self.paste_from_clipboard,
            bg='#3B8ED0',
            fg='#FFFFFF',
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor='hand2'
        )
        self.btn_paste.pack(side=tk.LEFT, padx=5)

        self.btn_open_video = tk.Button(
            self.toolbar,
            text='📹 開啟影片',
            command=self.open_video,
            bg='#6B5B95',
            fg='#FFFFFF',
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor='hand2'
        )
        self.btn_open_video.pack(side=tk.LEFT, padx=5)

        tk.Label(self.toolbar, text='寬度:', bg='#2D2D2D', fg='#FFFFFF').pack(side=tk.LEFT, padx=(20, 5))

        self.width_var = tk.StringVar(value=str(self.settings.get('crop_width', 640)))
        self.width_entry = tk.Entry(
            self.toolbar,
            textvariable=self.width_var,
            width=8,
            bg='#3B3B3B',
            fg='#FFFFFF',
            insertbackground='#FFFFFF',
            relief=tk.FLAT
        )
        self.width_entry.pack(side=tk.LEFT, padx=5)
        self.width_entry.bind('<FocusOut>', lambda e: self._on_size_change())
        self.width_entry.bind('<Return>', lambda e: self._on_size_change())

        tk.Label(self.toolbar, text='高度:', bg='#2D2D2D', fg='#FFFFFF').pack(side=tk.LEFT, padx=(15, 5))

        self.height_var = tk.StringVar(value=str(self.settings.get('crop_height', 640)))
        self.height_entry = tk.Entry(
            self.toolbar,
            textvariable=self.height_var,
            width=8,
            bg='#3B3B3B',
            fg='#FFFFFF',
            insertbackground='#FFFFFF',
            relief=tk.FLAT
        )
        self.height_entry.pack(side=tk.LEFT, padx=5)
        self.height_entry.bind('<FocusOut>', lambda e: self._on_size_change())
        self.height_entry.bind('<Return>', lambda e: self._on_size_change())

        self.btn_screen_size = tk.Button(
            self.toolbar,
            text='🖥️ 螢幕尺寸',
            command=self.use_screen_size,
            bg='#3B8ED0',
            fg='#FFFFFF',
            relief=tk.FLAT,
            padx=8,
            cursor='hand2'
        )
        self.btn_screen_size.pack(side=tk.LEFT, padx=5)

        tk.Label(self.toolbar, text='輸出路徑:', bg='#2D2D2D', fg='#FFFFFF').pack(side=tk.LEFT, padx=(20, 5))

        self.output_var = tk.StringVar()
        self.output_entry = tk.Entry(
            self.toolbar,
            textvariable=self.output_var,
            width=20,
            bg='#3B3B3B',
            fg='#FFFFFF',
            insertbackground='#FFFFFF',
            relief=tk.FLAT
        )
        self.output_entry.pack(side=tk.LEFT, padx=5)

        self.btn_output = tk.Button(
            self.toolbar,
            text='瀏覽',
            command=self.select_output_directory,
            bg='#3B3B3B',
            fg='#FFFFFF',
            relief=tk.FLAT,
            padx=8,
            cursor='hand2'
        )
        self.btn_output.pack(side=tk.LEFT, padx=5)

        self.btn_settings = tk.Button(
            self.toolbar,
            text='⚙️ 設定',
            command=self.show_settings,
            bg='#3B3B3B',
            fg='#FFFFFF',
            relief=tk.FLAT,
            padx=8,
            cursor='hand2'
        )
        self.btn_settings.pack(side=tk.LEFT, padx=5)

        self.btn_center = tk.Button(
            self.toolbar,
            text='⬜ 置中',
            command=self.center_crop_box,
            bg='#3B8ED0',
            fg='#FFFFFF',
            relief=tk.FLAT,
            padx=8,
            cursor='hand2'
        )
        self.btn_center.pack(side=tk.LEFT, padx=5)

        self.btn_save = tk.Button(
            self.toolbar,
            text='💾 保存',
            command=self.save_cropped,
            bg='#2CC985',
            fg='#FFFFFF',
            relief=tk.FLAT,
            padx=8,
            cursor='hand2'
        )
        self.btn_save.pack(side=tk.LEFT, padx=5)

    def _create_navigation(self):
        self.btn_prev = tk.Button(
            self.nav_frame,
            text='◀ 上一張',
            command=self.prev_image,
            bg='#3B3B3B',
            fg='#FFFFFF',
            relief=tk.FLAT,
            padx=10,
            pady=2,
            cursor='hand2',
            state='disabled'
        )
        self.btn_prev.pack(side=tk.LEFT, padx=5)

        self.nav_label = tk.Label(
            self.nav_frame,
            text='',
            bg='#2D2D2D',
            fg='#FFFFFF',
            padx=10
        )
        self.nav_label.pack(side=tk.LEFT, padx=5)

        self.btn_next = tk.Button(
            self.nav_frame,
            text='下一張 ▶',
            command=self.next_image,
            bg='#3B3B3B',
            fg='#FFFFFF',
            relief=tk.FLAT,
            padx=10,
            pady=2,
            cursor='hand2',
            state='disabled'
        )
        self.btn_next.pack(side=tk.LEFT, padx=5)

        # Video control frame
        self.video_control_frame = tk.Frame(self.nav_frame, bg='#2D2D2D')
        self.video_control_frame.pack(side=tk.LEFT, padx=(30, 5))
        self.video_control_frame.pack_forget()  # Hidden by default

        self.btn_video_prev = tk.Button(
            self.video_control_frame,
            text='◀◀',
            command=self.video_prev_frame,
            bg='#3B3B3B',
            fg='#FFFFFF',
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor='hand2',
            width=3
        )
        self.btn_video_prev.pack(side=tk.LEFT, padx=2)

        self.btn_video_play = tk.Button(
            self.video_control_frame,
            text='▶',
            command=self.video_toggle_play,
            bg='#3B3B3B',
            fg='#FFFFFF',
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor='hand2',
            width=3
        )
        self.btn_video_play.pack(side=tk.LEFT, padx=2)

        self.btn_video_next = tk.Button(
            self.video_control_frame,
            text='▶▶',
            command=self.video_next_frame,
            bg='#3B3B3B',
            fg='#FFFFFF',
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor='hand2',
            width=3
        )
        self.btn_video_next.pack(side=tk.LEFT, padx=2)

        self.video_frame_label = tk.Label(
            self.video_control_frame,
            text='',
            bg='#2D2D2D',
            fg='#FFFFFF',
            padx=10
        )
        self.video_frame_label.pack(side=tk.LEFT, padx=5)

    def _load_settings_to_ui(self):
        self.output_var.set(self.output_directory)
        self.width_var.set(str(self.settings.get('crop_width', 640)))
        self.height_var.set(str(self.settings.get('crop_height', 640)))

    def _setup_bindings(self):
        self.root.bind('<Control-o>', lambda e: self.open_folder())
        self.root.bind('<Control-O>', lambda e: self.open_folder())
        self.root.bind('<Control-v>', lambda e: self.paste_from_clipboard())
        self.root.bind('<Control-V>', lambda e: self.paste_from_clipboard())
        self.root.bind('<Control-s>', lambda e: self.save_cropped())
        self.root.bind('<Control-S>', lambda e: self.save_cropped())
        self.root.bind('<Return>', lambda e: self.save_cropped())

        # Arrow keys - handle both image folder and video navigation
        self.root.bind('<Left>', lambda e: self._handle_left_key())
        self.root.bind('<Right>', lambda e: self._handle_right_key())
        self.root.bind('<space>', lambda e: self._handle_space_key())

        # 點擊空白處取消聚焦
        self.root.bind('<Button-1>', lambda e: self._on_background_click(e))

        if DND_AVAILABLE:
            self.root.drop_target_register('DND_Files')
            self.root.dnd_bind('<<Drop>>', self.handle_file_drop)

    def _on_size_change(self, save_to_settings=False):
        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())

            width = max(50, min(width, 4000))
            height = max(50, min(height, 4000))

            self.width_var.set(str(width))
            self.height_var.set(str(height))

            if save_to_settings:
                self.settings.set('crop_width', width)
                self.settings.set('crop_height', height)

            if self.crop_canvas.has_image():
                self.crop_canvas.set_crop_size(width, height)
                self._update_status(f'裁剪框尺寸已更新: {width}x{height}')
        except ValueError:
            self.width_var.set(str(self.DEFAULT_CROP_WIDTH))
            self.height_var.set(str(self.DEFAULT_CROP_HEIGHT))

    def _on_crop_change(self, region):
        pass

    def center_crop_box(self):
        if self.crop_canvas.has_image():
            self.crop_canvas.center_crop_box()
            self._update_status('裁剪框已置中')
        else:
            utils.show_info('提示', '請先載入圖片', parent=self.root, play_sound=self.settings.get('notification_sound', True))

    def use_screen_size(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.width_var.set(str(screen_width))
        self.height_var.set(str(screen_height))
        self._on_size_change()
        self._update_status(f'已設定為螢幕尺寸: {screen_width}x{screen_height}')

    def open_file(self):
        filepath = utils.open_file_dialog()
        if filepath:
            self.load_image(filepath)

    def open_folder(self):
        folder_path = utils.select_output_directory()
        if folder_path:
            self.folder_images = []
            for f in os.listdir(folder_path):
                full_path = os.path.join(folder_path, f)
                if os.path.isfile(full_path) and utils.is_supported_image(full_path):
                    self.folder_images.append(full_path)

            if not self.folder_images:
                utils.show_info('提示', '資料夾中沒有圖片檔案', parent=self.root, play_sound=self.settings.get('notification_sound', True))
                return

            self.folder_images.sort()
            self.current_folder_index = 0
            self.load_image(self.folder_images[0], from_folder=True)
            self._update_navigation()

    def _update_navigation(self):
        if self.folder_images and self.current_folder_index >= 0:
            self.nav_label.config(text=f'{self.current_folder_index + 1} / {len(self.folder_images)}')
            self.btn_prev.config(state='normal' if self.current_folder_index > 0 else 'disabled')
            self.btn_next.config(state='normal' if self.current_folder_index < len(self.folder_images) - 1 else 'disabled')
        else:
            self.nav_label.config(text='')
            self.btn_prev.config(state='disabled')
            self.btn_next.config(state='disabled')

    def prev_image(self):
        if self.current_folder_index > 0:
            self.current_folder_index -= 1
            self.load_image(self.folder_images[self.current_folder_index], from_folder=True)
            self._update_navigation()

    def next_image(self):
        if self.current_folder_index < len(self.folder_images) - 1:
            self.current_folder_index += 1
            self.load_image(self.folder_images[self.current_folder_index], from_folder=True)
            self._update_navigation()

    def load_image(self, filepath, from_folder=False):
        if not utils.is_supported_image(filepath):
            utils.show_error('錯誤', '不支援的圖片格式', parent=self.root, play_sound=self.settings.get('notification_sound', True))
            return False

        success = self.crop_canvas.load_image(filepath)

        if success:
            self.current_image_path = filepath
            # 保存時覆蓋當前檔案
            self.last_saved_path = filepath
            if from_folder:
                self.current_image_from_folder = filepath
            self._update_status(f'已載入: {os.path.basename(filepath)}')
            self._update_size_label()

            width = int(self.width_var.get())
            height = int(self.height_var.get())
            self.crop_canvas.set_crop_size(width, height)

            return True
        else:
            utils.show_error('錯誤', '無法載入圖片', parent=self.root, play_sound=self.settings.get('notification_sound', True))
            return False

    def paste_from_clipboard(self):
        try:
            clipboard_content = ImageGrab.grabclipboard()

            # 情況 1: 剪貼簿包含圖片
            if clipboard_content is None:
                # 情況 2: 檢查剪貼簿是否包含文字形式的檔案路徑
                try:
                    text = self.root.clipboard_get()
                    # 如果是圖片檔案路徑，先嘗試載入圖片
                    if text and (utils.is_supported_image(text) or os.path.isfile(text)):
                        if self.load_image(text):
                            return True
                except:
                    pass
                # 如果沒有圖片，檢查焦點是否在輸入欄位上
                focused = self.root.focus_get()
                if focused and isinstance(focused, (tk.Entry, ttk.Entry)):
                    return  # 讓預設貼上行為發生
                utils.show_info('提示', '剪貼簿中無圖片', parent=self.root, play_sound=self.settings.get('notification_sound', True))
                return False

            if isinstance(clipboard_content, list):
                if clipboard_content and utils.is_supported_image(clipboard_content[0]):
                    self.load_image(clipboard_content[0])
                    return True
                utils.show_info('提示', '剪貼簿中無圖片', parent=self.root, play_sound=self.settings.get('notification_sound', True))
                return False

            if self.crop_canvas.set_image_from_pil(clipboard_content):
                self.current_image_path = None
                self.current_image_from_folder = None
                self.last_saved_path = None
                self._update_status('已從剪貼簿貼上圖片')
                self._update_size_label()

                width = int(self.width_var.get())
                height = int(self.height_var.get())
                self.crop_canvas.set_crop_size(width, height)

                return True
            else:
                utils.show_error('錯誤', '無法從剪貼簿讀取圖片', parent=self.root, play_sound=self.settings.get('notification_sound', True))
                return False

        except Exception as e:
            utils.show_error('錯誤', f'無法從剪貼簿貼上圖片: {str(e)}', parent=self.root, play_sound=self.settings.get('notification_sound', True))
            return False

    def handle_file_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        if files:
            filepath = files[0]
            if os.path.isdir(filepath):
                self.load_folder_from_path(filepath)
            elif utils.is_supported_video(filepath):
                self.open_video_file(filepath)
            elif utils.is_supported_image(filepath):
                self.load_image(filepath)

    def load_folder_from_path(self, folder_path):
        self.folder_images = []
        for f in os.listdir(folder_path):
            full_path = os.path.join(folder_path, f)
            if os.path.isfile(full_path) and utils.is_supported_image(full_path):
                self.folder_images.append(full_path)

        if not self.folder_images:
            utils.show_info('提示', '資料夾中沒有圖片檔案', parent=self.root, play_sound=self.settings.get('notification_sound', True))
            return

        self.folder_images.sort()
        self.current_folder_index = 0
        self.load_image(self.folder_images[0], from_folder=True)
        self._update_navigation()

    def select_output_directory(self):
        directory = utils.select_output_directory()
        if directory:
            self.output_directory = directory
            self.output_var.set(directory)
            self.settings.set('output_directory', directory)

    def _center_window(self, window, width, height):
        window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (width // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')

    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title('設定')
        settings_window.geometry('400x480')
        self._center_window(settings_window, 400, 480)
        settings_window.configure(bg='#1A1A1A')
        settings_window.transient(self.root)
        settings_window.grab_set()

        frame = ttk.Frame(settings_window, style='Dark.TFrame')
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        auto_naming_var = tk.BooleanVar(value=self.settings.get('auto_naming', False))
        auto_naming_check = tk.Checkbutton(
            frame,
            text='啟用自動命名',
            variable=auto_naming_var,
            bg='#1A1A1A',
            fg='#FFFFFF',
            selectcolor='#2D2D2D',
            activebackground='#1A1A1A',
            activeforeground='#FFFFFF'
        )
        auto_naming_check.pack(anchor=tk.W, pady=10)

        tk.Label(frame, text='自動命名格式:', bg='#1A1A1A', fg='#FFFFFF').pack(anchor=tk.W)
        format_var = tk.StringVar(value=self.settings.get('auto_naming_format', '%y-%m-%d %h %n %s'))
        format_entry = tk.Entry(frame, textvariable=format_var, width=30, bg='#3B3B3B', fg='#FFFFFF', insertbackground='#FFFFFF')
        format_entry.pack(anchor=tk.W, pady=5)
        tk.Label(frame, text='格式說明: %y=年 %m=月 %d=日 %h=時 %n=分 %s=秒', bg='#1A1A1A', fg='#A0A0A0', font=('Arial', 8)).pack(anchor=tk.W)

        dont_ask_var = tk.BooleanVar(value=self.settings.get('dont_ask_overwrite', False))
        dont_ask_check = tk.Checkbutton(
            frame,
            text='覆蓋檔案時不再詢問',
            variable=dont_ask_var,
            bg='#1A1A1A',
            fg='#FFFFFF',
            selectcolor='#2D2D2D',
            activebackground='#1A1A1A',
            activeforeground='#FFFFFF'
        )
        dont_ask_check.pack(anchor=tk.W, pady=10)

        sound_var = tk.BooleanVar(value=self.settings.get('notification_sound', True))
        sound_check = tk.Checkbutton(
            frame,
            text='提示音效',
            variable=sound_var,
            bg='#1A1A1A',
            fg='#FFFFFF',
            selectcolor='#2D2D2D',
            activebackground='#1A1A1A',
            activeforeground='#FFFFFF'
        )
        sound_check.pack(anchor=tk.W, pady=10)

        tk.Label(frame, text='預設裁剪尺寸:', bg='#1A1A1A', fg='#FFFFFF').pack(anchor=tk.W, pady=(15, 5))

        default_size_frame = tk.Frame(frame, bg='#1A1A1A')
        default_size_frame.pack(anchor=tk.W, pady=5)

        tk.Label(default_size_frame, text='寬度:', bg='#1A1A1A', fg='#FFFFFF').pack(side=tk.LEFT)
        default_width_var = tk.StringVar(value=str(self.settings.get('crop_width', 640)))
        default_width_entry = tk.Entry(default_size_frame, textvariable=default_width_var, width=8, bg='#3B3B3B', fg='#FFFFFF', insertbackground='#FFFFFF')
        default_width_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(default_size_frame, text='高度:', bg='#1A1A1A', fg='#FFFFFF').pack(side=tk.LEFT, padx=(15, 0))
        default_height_var = tk.StringVar(value=str(self.settings.get('crop_height', 640)))
        default_height_entry = tk.Entry(default_size_frame, textvariable=default_height_var, width=8, bg='#3B3B3B', fg='#FFFFFF', insertbackground='#FFFFFF')
        default_height_entry.pack(side=tk.LEFT, padx=5)

        def save_settings():
            self.settings.set('auto_naming', auto_naming_var.get())
            self.settings.set('auto_naming_format', format_var.get())
            self.settings.set('dont_ask_overwrite', dont_ask_var.get())
            self.settings.set('notification_sound', sound_var.get())
            try:
                self.settings.set('crop_width', int(default_width_var.get()))
                self.settings.set('crop_height', int(default_height_var.get()))
            except ValueError:
                pass
            self._load_settings_to_ui()
            settings_window.destroy()
            utils.show_info('設定', '設定已保存', parent=self.root, play_sound=self.settings.get('notification_sound', True))

        btn_frame = ttk.Frame(frame, style='Dark.TFrame')
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text='保存', command=save_settings, bg='#2CC985', fg='#FFFFFF', relief=tk.FLAT, padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text='取消', command=settings_window.destroy, bg='#FF6B35', fg='#FFFFFF', relief=tk.FLAT, padx=20).pack(side=tk.LEFT, padx=5)

        def restore_default():
            self.settings.settings = self.settings.DEFAULT_SETTINGS.copy()
            self.settings.save_settings()
            self._load_settings_to_ui()
            utils.show_info('設定', '已恢復預設設定', parent=self.root, play_sound=self.settings.get('notification_sound', True))

        restore_frame = ttk.Frame(frame, style='Dark.TFrame')
        restore_frame.pack(pady=10)
        tk.Button(restore_frame, text='恢復預設', command=restore_default, bg='#6B5B95', fg='#FFFFFF', relief=tk.FLAT, padx=15).pack()

    def generate_auto_filename(self, extension):
        format_str = self.settings.get('auto_naming_format', '%y-%m-%d %h %n %s')
        now = datetime.now()

        filename = format_str.replace('%y', f'{now.year:04d}')
        filename = filename.replace('%m', f'{now.month:02d}')
        filename = filename.replace('%d', f'{now.day:02d}')
        filename = filename.replace('%h', f'{now.hour:02d}')
        filename = filename.replace('%n', f'{now.minute:02d}')
        filename = filename.replace('%s', f'{now.second:02d}')

        if not filename.endswith(extension):
            filename += extension

        # 檢查檔案是否已存在，若存在則自動編號
        # 使用 UI 中選擇的輸出目錄
        output_dir = self.output_var.get().strip() if hasattr(self, 'output_var') else ''
        if not output_dir:
            output_dir = self.settings.get('output_dir', '')

        if output_dir and os.path.exists(output_dir):
            full_path = os.path.join(output_dir, filename)
            if os.path.exists(full_path):
                base_name = filename[:filename.rfind(extension)]
                counter = 1
                while os.path.exists(os.path.join(output_dir, f'{base_name}_{counter}{extension}')):
                    counter += 1
                filename = f'{base_name}_{counter}{extension}'

        return filename

    def save_cropped(self):
        if not self.crop_canvas.has_image():
            utils.show_info('提示', '請先載入圖片', parent=self.root, play_sound=self.settings.get('notification_sound', True))
            return

        output_dir = self.output_var.get().strip()

        if not output_dir:
            utils.show_info('提示', '請選擇輸出路徑', parent=self.root, play_sound=self.settings.get('notification_sound', True))
            self.select_output_directory()
            output_dir = self.output_var.get().strip()
            if not output_dir:
                return

        if not os.path.isdir(output_dir):
            utils.show_error('錯誤', '輸出路徑無效', parent=self.root, play_sound=self.settings.get('notification_sound', True))
            return

        crop_region = self.crop_canvas.get_crop_region()

        use_auto_naming = self.settings.get('auto_naming', False)
        dont_ask = self.settings.get('dont_ask_overwrite', False)

        # 啟用自動命名：自動依格式產生檔名
        if use_auto_naming:
            if self.crop_canvas.original_image:
                img_format = self.crop_canvas.original_image.format
                if img_format:
                    ext = f'.{img_format.lower()}'
                else:
                    ext = '.png'
            else:
                ext = '.png'

            # 如果已經有儲存路徑，則覆蓋該檔案
            # 否則產生新檔名
            if self.last_saved_path:
                output_path = self.last_saved_path
            else:
                # 影片模式：使用影片檔名生成
                if self.is_video_mode:
                    original_filename = self.generate_video_filename(ext)
                else:
                    original_filename = self.generate_auto_filename(ext)
                output_path = os.path.join(output_dir, original_filename)
        else:
            # 未啟用自動命名：彈出另存新檔視窗，使用命名格式作為預設檔名
            if self.crop_canvas.original_image:
                img_format = self.crop_canvas.original_image.format
                if img_format:
                    ext = f'.{img_format.lower()}'
                else:
                    ext = '.png'
            else:
                ext = '.png'
            # 使用自動命名格式作為預設檔名
            if self.is_video_mode:
                initial_filename = self.generate_video_filename(ext)
            else:
                initial_filename = self.generate_auto_filename(ext)

            output_path = tk.filedialog.asksaveasfilename(
                initialdir=output_dir,
                initialfile=initial_filename,
                title='另存新檔',
                defaultextension='.png',
                filetypes=[
                    ('PNG 圖片', '*.png'),
                    ('JPEG 圖片', '*.jpg *.jpeg'),
                    ('所有檔案', '*.*')
                ]
            )
            if not output_path:
                return

        if os.path.exists(output_path):
            if not dont_ask:
                result = self._ask_overwrite_with_checkbox(output_path)
                if result is None:
                    return
                if not result:
                    return
            else:
                pass

        success, result = crop_and_save(
            self.crop_canvas.original_image,
            crop_region,
            output_path
        )

        if success:
            self.last_saved_path = output_path
            self.current_image_path = output_path
            self._update_status(f'已保存: {result}')
        else:
            utils.show_error('錯誤', f'保存失敗: {result}', parent=self.root, play_sound=self.settings.get('notification_sound', True))

    def _ask_overwrite_with_checkbox(self, filepath):
        dialog = tk.Toplevel(self.root)
        dialog.title('檔案已存在')
        dialog.geometry('400x150')
        self._center_window(dialog, 400, 150)
        dialog.configure(bg='#1A1A1A')
        dialog.transient(self.root)
        dialog.grab_set()

        result = [None]
        dont_ask_var = tk.BooleanVar(value=False)

        tk.Label(
            dialog,
            text=f'檔案 "{os.path.basename(filepath)}" 已存在，是否覆蓋?',
            bg='#1A1A1A',
            fg='#FFFFFF',
            wraplength=350
        ).pack(pady=20)

        dont_ask_check = tk.Checkbutton(
            dialog,
            text='不再詢問 (可從設定中重新開啟)',
            variable=dont_ask_var,
            bg='#1A1A1A',
            fg='#FFFFFF',
            selectcolor='#2D2D2D',
            activebackground='#1A1A1A',
            activeforeground='#FFFFFF'
        )
        dont_ask_check.pack(pady=10)

        btn_frame = tk.Frame(dialog, bg='#1A1A1A')
        btn_frame.pack(pady=10)

        def on_yes():
            if dont_ask_var.get():
                self.settings.set('dont_ask_overwrite', True)
            result[0] = True
            dialog.destroy()

        def on_no():
            result[0] = False
            dialog.destroy()

        tk.Button(btn_frame, text='是 (Y)', command=on_yes, bg='#2CC985', fg='#FFFFFF', relief=tk.FLAT, padx=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text='否 (N)', command=on_no, bg='#FF6B35', fg='#FFFFFF', relief=tk.FLAT, padx=15).pack(side=tk.LEFT, padx=5)

        dialog.bind('<y>', lambda e: on_yes())
        dialog.bind('<Y>', lambda e: on_yes())
        dialog.bind('<n>', lambda e: on_no())
        dialog.bind('<N>', lambda e: on_no())

        self.root.wait_window(dialog)
        return result[0]

    def reset(self):
        # 停止影片播放
        self._stop_video_playback()

        # 關閉影片
        if self.video_handler:
            self.video_handler.close()
            self.video_handler = None

        self.is_video_mode = False

        # 恢復圖片導航控制
        self._hide_video_controls()
        self._update_navigation()

        self.crop_canvas.reset()
        self.current_image_path = None
        self.current_image_from_folder = None
        self.last_saved_path = None
        self.folder_images = []
        self.current_folder_index = -1
        self._update_status('請載入圖片 (檔案對話框 / Ctrl+O 開啟資料夾 / Ctrl+V 貼上 / 拖放檔案)')
        self.size_label.config(text='')

    def _on_background_click(self, event):
        # 如果點擊的是 Entry 或其他輸入 widget，不做處理
        if event.widget and isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text)):
            return
        # 點擊空白處將焦點設到 root，解除輸入欄位的聚焦
        self.root.focus_set()

    def _handle_left_key(self):
        if self.is_video_mode:
            self.video_prev_frame()
        else:
            self.prev_image()

    def _handle_right_key(self):
        if self.is_video_mode:
            self.video_next_frame()
        else:
            self.next_image()

    def _handle_space_key(self):
        if self.is_video_mode:
            self.video_toggle_play()

    def _update_status(self, message):
        self.status_label.config(text=message)

    def _update_size_label(self):
        if self.crop_canvas.has_image():
            img_info = f'圖片尺寸: {self.crop_canvas.img_width} x {self.crop_canvas.img_height}'
            self.size_label.config(text=img_info)

    def open_video(self):
        video_path = utils.open_video_dialog()
        if not video_path:
            return
        self._load_video(video_path)

    def open_video_file(self, video_path):
        if not utils.is_supported_video(video_path):
            return False
        return self._load_video(video_path)

    def _load_video(self, video_path):
        if self.video_handler:
            self.video_handler.close()
            self._stop_video_playback()

        self.video_handler = utils.VideoHandler()
        success, message = self.video_handler.open(video_path)

        if not success:
            utils.show_error('錯誤', message, parent=self.root, play_sound=self.settings.get('notification_sound', True))
            return False

        self.is_video_mode = True
        self.current_image_path = video_path

        frame = self.video_handler.get_current_frame_as_pil()
        if frame:
            self.crop_canvas.set_image_from_pil(frame)
            width = int(self.width_var.get())
            height = int(self.height_var.get())
            self.crop_canvas.set_crop_size(width, height)

        self._show_video_controls()
        self._update_video_label()
        self._update_status(f'已載入影片: {os.path.basename(video_path)}')
        self._update_size_label()
        return True

    def _show_video_controls(self):
        self.video_control_frame.pack(side=tk.LEFT, padx=(30, 5))
        self.btn_prev.pack_forget()
        self.nav_label.pack_forget()
        self.btn_next.pack_forget()
        self.btn_prev = None
        self.btn_next = None

    def _hide_video_controls(self):
        self.video_control_frame.pack_forget()
        self.btn_prev.pack(side=tk.LEFT, padx=5)
        self.nav_label.pack(side=tk.LEFT, padx=5)
        self.btn_next.pack(side=tk.LEFT, padx=5)

    def _update_video_label(self):
        if self.video_handler and self.video_handler.is_opened():
            current = self.video_handler.get_frame_number() + 1
            total = self.video_handler.get_total_frames()
            fps = self.video_handler.get_fps()
            self.video_frame_label.config(text=f'第 {current} / {total} 幀 | {fps:.2f} FPS')
        else:
            self.video_frame_label.config(text='')

    def video_prev_frame(self):
        if self.video_handler and self.video_handler.is_opened():
            frame = self.video_handler.prev_frame()
            if frame:
                self.crop_canvas.set_image_from_pil(frame)
                self._update_video_label()
                self._update_status(f'已跳至第 {self.video_handler.get_frame_number() + 1} 幀')

    def video_next_frame(self):
        if self.video_handler and self.video_handler.is_opened():
            frame = self.video_handler.next_frame()
            if frame:
                self.crop_canvas.set_image_from_pil(frame)
                self._update_video_label()
                self._update_status(f'已跳至第 {self.video_handler.get_frame_number() + 1} 幀')

    def video_toggle_play(self):
        if not self.video_handler or not self.video_handler.is_opened():
            return

        if self.is_playing:
            self._stop_video_playback()
        else:
            self._start_video_playback()

    def _start_video_playback(self):
        if not self.video_handler or not self.video_handler.is_opened():
            return

        self.is_playing = True
        self.btn_video_play.config(text='⏸')

        fps = self.video_handler.get_fps()
        if fps <= 0:
            fps = 30

        delay = int(1000 / fps)

        def play_loop():
            if not self.is_playing or not self.video_handler.is_opened():
                return

            frame = self.video_handler.next_frame()
            if frame:
                self.crop_canvas.set_image_from_pil(frame)
                self._update_video_label()
                self.video_playback_id = self.root.after(delay, play_loop)
            else:
                self._stop_video_playback()

        play_loop()

    def _stop_video_playback(self):
        self.is_playing = False
        self.btn_video_play.config(text='▶')
        if self.video_playback_id:
            self.root.after_cancel(self.video_playback_id)
            self.video_playback_id = None

    def generate_video_filename(self, extension='.png'):
        if not self.video_handler or not self.video_handler.video_path:
            return self.generate_auto_filename(extension)

        video_name = os.path.splitext(os.path.basename(self.video_handler.video_path))[0]
        frame_num = self.video_handler.get_frame_number()
        frame_str = f'{frame_num:04d}'

        filename = f'{video_name}_frame_{frame_str}{extension}'

        output_dir = self.output_var.get().strip() if hasattr(self, 'output_var') else ''
        if not output_dir:
            output_dir = self.settings.get('output_dir', '')

        if output_dir and os.path.exists(output_dir):
            full_path = os.path.join(output_dir, filename)
            if os.path.exists(full_path):
                base_name = filename[:filename.rfind(extension)]
                counter = 1
                while os.path.exists(os.path.join(output_dir, f'{base_name}_{counter}{extension}')):
                    counter += 1
                filename = f'{base_name}_{counter}{extension}'

        return filename

    def run(self):
        self.root.mainloop()


def main():
    app = YOLOCropApp()
    app.run()


if __name__ == '__main__':
    main()
