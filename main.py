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
        'notification_sound': True,
        'video_hardware_acceleration': False
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

        # 影片相關
        self.video_handler = None
        self.vlc_player = None
        self.is_video_mode = False
        self.video_playback_id = None
        self.is_playing = False
        self.use_vlc = True  # 使用 VLC 進行流暢播放
        self.is_dragging_slider = False  # 滑塊拖動狀態
        self._slider_was_playing = False  # 滑塊拖動前的播放狀態

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

        # 圖片畫布（用於圖片和影片幀）
        self.crop_canvas = CropCanvas(
            self.canvas_frame,
            on_crop_change=self._on_crop_change
        )
        self.crop_canvas.pack(fill=tk.BOTH, expand=True)

        # 影片帧容器（用于 VLC 嵌入）
        self.video_frame = tk.Frame(self.canvas_frame, bg='#000000')
        # Don't pack yet - will be shown when video mode is active

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

        # 影片控制框架
        self.video_control_frame = tk.Frame(self.nav_frame, bg='#2D2D2D')
        self.video_control_frame.pack(side=tk.LEFT, padx=(30, 5))
        self.video_control_frame.pack_forget()  # 預設隱藏

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

        # 時間軌道（slider）
        self.video_slider = tk.Scale(
            self.video_control_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=800,
            showvalue=False,
            bg='#2D2D2D',
            fg='#FFFFFF',
            troughcolor='#3B3B3B',
            highlightthickness=0,
            command=self._on_video_slider_change
        )
        self.video_slider.pack(side=tk.LEFT, padx=5)
        self.video_slider.pack_forget()  # 預設隱藏

        # 綁定滑塊釋放事件，處理拖動結束時的跳轉
        self.video_slider.bind('<ButtonRelease-1>', self._on_slider_drag_end)

        # 時間顯示標籤
        self.video_time_label = tk.Label(
            self.video_control_frame,
            text='',
            bg='#2D2D2D',
            fg='#FFFFFF',
            padx=10
        )
        self.video_time_label.pack(side=tk.LEFT, padx=5)
        self.video_time_label.pack_forget()  # 預設隱藏

        # 標記滑塊是否正在被拖動（避免拖動時觸發自動更新）
        self.is_dragging_slider = False

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

        # 方向鍵 - 處理圖片資料夾和影片導航
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
            # 保存時覆蓋目前檔案
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
        settings_window.geometry('400x550')
        self._center_window(settings_window, 400, 550)
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

        hw_accel_var = tk.BooleanVar(value=self.settings.get('video_hardware_acceleration', False))
        hw_accel_check = tk.Checkbutton(
            frame,
            text='影片硬體加速 (使用顯示卡解碼)',
            variable=hw_accel_var,
            bg='#1A1A1A',
            fg='#FFFFFF',
            selectcolor='#2D2D2D',
            activebackground='#1A1A1A',
            activeforeground='#FFFFFF'
        )
        hw_accel_check.pack(anchor=tk.W, pady=10)
        tk.Label(frame, text='建議: 大影片開啟可提升效能，小影片建議關閉', bg='#1A1A1A', fg='#A0A0A0', font=('Arial', 8)).pack(anchor=tk.W)

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
            old_hw_accel = self.settings.get('video_hardware_acceleration', False)
            new_hw_accel = hw_accel_var.get()

            self.settings.set('auto_naming', auto_naming_var.get())
            self.settings.set('auto_naming_format', format_var.get())
            self.settings.set('dont_ask_overwrite', dont_ask_var.get())
            self.settings.set('notification_sound', sound_var.get())
            self.settings.set('video_hardware_acceleration', new_hw_accel)
            try:
                self.settings.set('crop_width', int(default_width_var.get()))
                self.settings.set('crop_height', int(default_height_var.get()))
            except ValueError:
                pass
            self._load_settings_to_ui()
            settings_window.destroy()

            # 硬體加速設置改變時提示重啟
            if old_hw_accel != new_hw_accel:
                msg = "硬體加速設置已更改，需要重新啟動程式才能生效。"
                if new_hw_accel:
                    msg += "\n\n開啟硬體加速可提升大影片的解碼速度。"
                utils.show_info('設定', msg, parent=self.root, play_sound=self.settings.get('notification_sound', True))
            else:
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

        # 關閉影片 (both OpenCV and VLC)
        if self.video_handler:
            self.video_handler.close()
            self.video_handler = None
        if self.vlc_player:
            self.vlc_player.close()
            self.vlc_player = None

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

    def _on_video_slider_change(self, value):
        """處理時間軌道滑塊的變化（拖動時更新UI，釋放時跳轉）"""
        if not self.is_video_mode:
            return

        self.is_dragging_slider = True

        # 如果正在播放，停止定時更新以避免衝突
        # 保存目前播放狀態，拖動結束後根據此狀態恢復
        self._slider_was_playing = self.is_playing
        if self.use_vlc:
            self._stop_vlc_position_update()

        # 拖動時只更新 UI 顯示目前位置，不立即跳轉視頻
        # 實際的視頻跳轉在 _on_slider_drag_end 中處理

    def _on_slider_drag_end(self, event):
        """滑塊拖動結束時執行跳轉"""
        if not self.is_video_mode:
            return

        try:
            slider_value = self.video_slider.get()

            # 先嘗試 VLC
            if self.use_vlc and self.vlc_player and self.vlc_player.player:
                try:
                    length = self.vlc_player.get_length()  # 毫秒
                    if length > 0:
                        new_time = int(slider_value / 100 * length)
                        self.vlc_player.set_time(new_time)
                        # 使用 after 延遲執行，避免阻塞
                        self.root.after(50, self._capture_vlc_frame)
                        self.root.after(50, self._update_video_time_display)
                        self.root.after(50, self._update_video_label)
                except Exception as e:
                    print(f"VLC slider seek error: {e}")

            # 回退到 OpenCV
            elif self.video_handler and self.video_handler.is_opened():
                total_frames = self.video_handler.get_total_frames()
                if total_frames > 0:
                    target_frame = int(slider_value / 100 * total_frames)
                    frame = self.video_handler.seek_to_frame(target_frame)
                    if frame:
                        self.crop_canvas.set_image_from_pil(frame)
                    self._update_video_time_display()
                    self._update_video_label()

        finally:
            # 根據拖動前的播放狀態決定是否恢復定時更新
            if self._slider_was_playing and self.use_vlc:
                self.root.after(150, self._start_vlc_position_update)

            # 延迟重置拖动标记
            self.root.after(100, lambda: setattr(self, 'is_dragging_slider', False))

    def _reset_slider_drag_flag(self):
        """重置滑块拖动标记"""
        self.is_dragging_slider = False

    def _update_status(self, message):
        self.status_label.config(text=message)

    def _update_size_label(self):
        if self.crop_canvas.has_image():
            img_info = f'圖片尺寸: {self.crop_canvas.img_width} x {self.crop_canvas.img_height}'
            self.size_label.config(text=img_info)

    def open_video(self):
        # 防止重複點擊
        if getattr(self, 'is_loading_video', False):
            return
        video_path = utils.open_video_dialog()
        if not video_path:
            return
        self._load_video_async(video_path)

    def open_video_file(self, video_path):
        # 防止重複點擊
        if getattr(self, 'is_loading_video', False):
            return False
        if not utils.is_supported_video(video_path):
            return False
        self._load_video_async(video_path)
        return True

    def _load_video_async(self, video_path):
        """使用執行緒非同步載入影片，避免阻塞 UI"""
        if getattr(self, 'is_loading_video', False):
            return

        self.is_loading_video = True
        self.btn_open_video.config(state='disabled')
        self._update_status('正在載入影片...')

        # 在執行緒中載入影片
        def load_in_thread():
            try:
                # 關閉現有的影片處理器
                if self.video_handler:
                    self.video_handler.close()
                    self.video_handler = None
                if self.vlc_player:
                    self.vlc_player.close()
                    self.vlc_player = None

                # 等待上一個播放執行緒停止
                import time
                time.sleep(0.1)

                # 先嘗試 VLC, fall back to OpenCV if VLC fails
                use_vlc = self.use_vlc
                vlc_player = None
                video_handler = None

                if use_vlc:
                    try:
                        vlc_player = utils.VLCVideoPlayer(self.video_frame)
                        use_hw_accel = self.settings.get('video_hardware_acceleration', False)
                        success, message = vlc_player.open(video_path, use_hw_accel)
                        if not success:
                            raise Exception(message)
                    except Exception as vlc_error:
                        print(f"VLC failed: {vlc_error}, falling back to OpenCV")
                        use_vlc = False
                        vlc_player = None

                # 回退到 OpenCV if VLC not available
                result = {
                    'success': False,
                    'video_path': video_path,
                    'use_vlc': use_vlc,
                    'vlc_player': vlc_player,
                    'video_handler': None,
                    'error': None
                }

                if not use_vlc or vlc_player is None:
                    video_handler = utils.VideoHandler()
                    success, message = video_handler.open(video_path)
                    if not success:
                        result['error'] = message
                        self.root.after(0, lambda: self._on_video_load_error(result))
                        return
                    result['video_handler'] = video_handler

                result['success'] = True
                self.root.after(0, lambda: self._on_video_loaded(result))

            except Exception as e:
                result = {'success': False, 'error': str(e), 'video_path': video_path}
                self.root.after(0, lambda: self._on_video_load_error(result))

        # 啟動執行緒
        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()

    def _on_video_loaded(self, result):
        """影片載入完成後的 UI 更新（在主執行緒執行）"""
        try:
            video_path = result['video_path']

            # 恢復 VLC 設置（因為執行緒中可能修改了）
            self.use_vlc = result['use_vlc']
            self.vlc_player = result.get('vlc_player')
            self.video_handler = result.get('video_handler')

            if not self.use_vlc or self.vlc_player is None:
                if self.video_handler:
                    frame = self.video_handler.get_current_frame_as_pil()
                    if frame:
                        self.crop_canvas.set_image_from_pil(frame)
                        width = int(self.width_var.get())
                        height = int(self.height_var.get())
                        self.crop_canvas.set_crop_size(width, height)

            self.is_video_mode = True
            self.current_image_path = video_path
            self._show_video_controls()

            # 初始化滑块位置为0
            if self.video_slider:
                self.video_slider.set(0)
                self.video_slider.config(state='normal')

            # 對於 VLC，需要延遲後再嵌入播放器
            if self.use_vlc and self.vlc_player:
                self.root.after(100, self._embed_vlc_player)

            self._update_video_label()
            self._update_status(f'已載入影片: {os.path.basename(video_path)}')
            self._update_size_label()

        except Exception as e:
            utils.show_error('錯誤', f'載入影片失敗: {str(e)}', parent=self.root, play_sound=self.settings.get('notification_sound', True))

        # 重置加載狀態
        self.is_loading_video = False
        self.btn_open_video.config(state='normal')

    def _on_video_load_error(self, result):
        """影片載入失敗後的 UI 更新（在主執行緒執行）"""
        error_msg = result.get('error', '未知錯誤')
        utils.show_error('錯誤', f'載入影片失敗: {error_msg}', parent=self.root, play_sound=self.settings.get('notification_sound', True))

        # 重置加載狀態
        self.is_loading_video = False
        self.btn_open_video.config(state='normal')
        self._update_status('準備就緒')

    def _embed_vlc_player(self):
        """嵌入 VLC 播放器到 Tkinter 視窗"""
        if not self.vlc_player or not self.use_vlc:
            return

        # 隱藏圖片畫布，顯示影片框架
        self.crop_canvas.pack_forget()
        self.video_frame.pack(fill=tk.BOTH, expand=True)

        # 強制框架更新
        self.video_frame.update_idletasks()

        # 取得視窗 handle
        hwnd = self.video_frame.winfo_id()

        # 設定 VLC 輸出視窗
        self.vlc_player.player.set_hwnd(hwnd)

        # 開始播放
        self.vlc_player.play()
        self.is_playing = True
        self.btn_video_play.config(text='⏸')

        # 啟動定時更新播放位置
        self._start_vlc_position_update()

    def _show_video_controls(self):
        self.video_control_frame.pack(side=tk.LEFT, padx=(30, 5))
        if self.btn_prev:
            self.btn_prev.pack_forget()
        if self.nav_label:
            self.nav_label.pack_forget()
        if self.btn_next:
            self.btn_next.pack_forget()

        # 顯示時間軌道和時間標籤
        if self.video_slider:
            self.video_slider.pack(side=tk.LEFT, padx=5)
        if self.video_time_label:
            self.video_time_label.pack(side=tk.LEFT, padx=5)

    def _hide_video_controls(self):
        self.video_control_frame.pack_forget()

        # 隱藏並停用時間軌道和時間標籤
        if self.video_slider:
            self.video_slider.pack_forget()
            self.video_slider.config(state='disabled')
        if self.video_time_label:
            self.video_time_label.pack_forget()

    def _update_video_label(self, is_automatic_update=False):
        # 自動更新 slider 時設置標誌，防止觸發回調
        was_updating_slider = False
        skip_slider_update = False

        # 如果是自動更新，則跳過設置拖動標誌
        if is_automatic_update:
            skip_slider_update = True

        if self.is_video_mode and hasattr(self, 'video_slider') and self.video_slider and not skip_slider_update:
            was_updating_slider = True
            self.is_dragging_slider = True

        # Try VLC first
        if self.use_vlc and self.vlc_player and self.vlc_player.player:
            try:
                length = self.vlc_player.get_length()
                current_time = self.vlc_player.get_time()
                fps = self.vlc_player.get_fps()

                if length > 0 and fps > 0:
                    total_frames = int(length / 1000 * fps)
                    current_frame = int(current_time / 1000 * fps) + 1
                    self.video_frame_label.config(text=f'第 {current_frame} / {total_frames} 幀 | {fps:.2f} FPS')

                    # 延遲更新軌道位置，減少卡頓
                    if self.video_slider and total_frames > 0:
                        progress = int(current_time / length * 100)
                        # 總是更新slider，因爲視頻播放時進度可能很長時間保持在小於1%
                        try:
                            current_slider_val = self.video_slider.get()
                            if abs(current_slider_val - progress) >= 1 or progress < 10:
                                self.video_slider.set(progress)
                                self.video_slider.update_idletasks()
                        except:
                            pass

                    # 雖然不更新 slider 了，但仍要更新時間顯示
                    self._update_video_time_display()

                    # 恢復標誌
                    if was_updating_slider:
                        self.root.after(50, lambda: setattr(self, 'is_dragging_slider', False))
                    return
            except:
                pass

        # Fall back to OpenCV
        if self.video_handler and self.video_handler.is_opened():
            current = self.video_handler.get_frame_number() + 1
            total = self.video_handler.get_total_frames()
            fps = self.video_handler.get_fps()
            self.video_frame_label.config(text=f'第 {current} / {total} 幀 | {fps:.2f} FPS')

            # 更新軌道位置（優化版本）
            if self.video_slider and total > 0:
                try:
                    current_slider_val = self.video_slider.get()
                    progress = int((self.video_handler.get_frame_number() / total) * 100)
                    if abs(current_slider_val - progress) > 1:
                        self.video_slider.set(progress)
                except:
                    pass

            # 雖然不更新 slider 了，但仍要更新時間顯示
            self._update_video_time_display()

            # 恢復標誌
            if was_updating_slider:
                self.root.after(50, lambda: setattr(self, 'is_dragging_slider', False))
        else:
            # 恢復標誌
            if was_updating_slider:
                self.root.after(50, lambda: setattr(self, 'is_dragging_slider', False))

    def _update_video_time_display(self):
        """更新時間顯示標籤（目前時間/總時長）"""
        if not self.video_time_label:
            return

        # Try VLC first
        if self.use_vlc and self.vlc_player and self.vlc_player.player:
            try:
                length = self.vlc_player.get_length()  # 毫秒
                current_time = self.vlc_player.get_time()  # 毫秒

                if length > 0:
                    current_str = self._format_time(current_time / 1000)  # 转换为秒
                    total_str = self._format_time(length / 1000)  # 转换为秒
                    self.video_time_label.config(text=f'{current_str} / {total_str}')
                    return
            except:
                pass

        # Fall back to OpenCV
        if self.video_handler and self.video_handler.is_opened():
            fps = self.video_handler.get_fps()
            current_frame = self.video_handler.get_frame_number()
            total_frames = self.video_handler.get_total_frames()

            if fps > 0 and total_frames > 0:
                current_seconds = current_frame / fps
                total_seconds = total_frames / fps
                current_str = self._format_time(current_seconds)
                total_str = self._format_time(total_seconds)
                self.video_time_label.config(text=f'{current_str} / {total_str}')
                return

        self.video_time_label.config(text='')

    def _format_time(self, seconds):
        """格式化時間為 MM:SS 或 HH:MM:SS 格式"""
        if seconds < 0:
            seconds = 0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f'{hours:02d}:{minutes:02d}:{secs:02d}'
        else:
            return f'{minutes:02d}:{secs:02d}'

    def _update_vlc_position_loop(self):
        """定時更新 VLC 播放位置（迴圈版本）"""
        if not self.use_vlc or not self.vlc_player or not self.is_video_mode:
            return

        # 只使用 self.is_playing 來判斷是否繼續，這樣更穩定
        if self.is_playing and self.vlc_player.player:
            self._update_video_label(is_automatic_update=True)
            # 繼續定時更新
            self.video_playback_id = self.root.after(100, self._update_vlc_position_loop)
        else:
            # 播放停止了
            self.is_playing = False
            self.btn_video_play.config(text='▶')
            self._update_video_label()

    def video_prev_frame(self):
        # Try VLC first
        if self.use_vlc and self.vlc_player and self.vlc_player.player:
            try:
                current_time = self.vlc_player.get_time()  # 毫秒
                fps = self.vlc_player.get_fps()

                # 退後 1 幀 (1幀的時間 = 1000ms / fps)
                if fps > 0:
                    frame_duration_ms = 1000.0 / fps
                    new_time = max(0, current_time - frame_duration_ms)
                    self.vlc_player.set_time(int(new_time))

                    # 稍微等待 VLC 渲染新幀
                    import time
                    time.sleep(0.05)

                    # Capture frame for cropping
                    self._capture_vlc_frame()
                    self._update_video_label()
                    self._update_status('已跳至上一幀')
                    return
            except Exception as e:
                print(f"VLC prev frame error: {e}")

        # Fall back to OpenCV
        if self.video_handler and self.video_handler.is_opened():
            frame = self.video_handler.prev_frame()
            if frame:
                self.crop_canvas.set_image_from_pil(frame)
                self._update_video_label()
                self._update_status(f'已跳至第 {self.video_handler.get_frame_number() + 1} 幀')

    def video_next_frame(self):
        # Try VLC first
        if self.use_vlc and self.vlc_player and self.vlc_player.player:
            try:
                current_time = self.vlc_player.get_time()  # 毫秒
                length = self.vlc_player.get_length()  # 毫秒
                fps = self.vlc_player.get_fps()

                # 前進 1 幀 (1幀的時間 = 1000ms / fps)
                if fps > 0:
                    frame_duration_ms = 1000.0 / fps
                    new_time = min(length, current_time + frame_duration_ms)
                    self.vlc_player.set_time(int(new_time))

                    # 稍微等待 VLC 渲染新幀
                    import time
                    time.sleep(0.05)

                    # Capture frame for cropping
                    self._capture_vlc_frame()
                    self._update_video_label()
                    self._update_status('已跳至下一幀')
                    return
            except Exception as e:
                print(f"VLC next frame error: {e}")

        # Fall back to OpenCV
        if self.video_handler and self.video_handler.is_opened():
            frame = self.video_handler.next_frame()
            if frame:
                self.crop_canvas.set_image_from_pil(frame)
                self._update_video_label()
                self._update_status(f'已跳至第 {self.video_handler.get_frame_number() + 1} 幀')

    def _capture_vlc_frame(self):
        """從 VLC 目前的播放位置擷取幀用於裁剪"""
        if not self.use_vlc or not self.vlc_player:
            return

        try:
            current_time = self.vlc_player.get_time()
            frame = self.vlc_player.get_frame_at_time(current_time)
            if frame:
                self.crop_canvas.set_image_from_pil(frame)
                width = int(self.width_var.get())
                height = int(self.height_var.get())
                self.crop_canvas.set_crop_size(width, height)
        except Exception as e:
            print(f"Failed to capture frame: {e}")

    def video_toggle_play(self):
        # Try VLC first
        if self.use_vlc and self.vlc_player and self.vlc_player.player:
            try:
                # 直接使用按鈕文字來判斷目前狀態，而不是依賴 is_playing_state()
                is_currently_paused = self.btn_video_play.cget('text') == '▶'

                if is_currently_paused:
                    # 當前是暫停狀態，開始播放
                    self.vlc_player.play()
                    self.vlc_player.is_playing = True
                    self.is_playing = True
                    self.btn_video_play.config(text='⏸')
                    # 啟動定時更新
                    self._start_vlc_position_update()
                else:
                    # 當前是播放狀態，暫停
                    self.vlc_player.pause()
                    self.vlc_player.is_playing = False
                    self.is_playing = False
                    self.btn_video_play.config(text='▶')
                    # 停止定時更新
                    self._stop_vlc_position_update()

                # 更新一次顯示
                self._update_video_label()
                return
            except Exception as e:
                print(f"VLC toggle play error: {e}")

        # Fall back to OpenCV
        if not self.video_handler or not self.video_handler.is_opened():
            return

        if self.is_playing:
            self._stop_video_playback()
        else:
            self._start_video_playback()

    def _stop_vlc_position_update(self):
        """停止 VLC 播放位置的定時更新"""
        if self.video_playback_id:
            self.root.after_cancel(self.video_playback_id)
            self.video_playback_id = None

    def _start_vlc_position_update(self):
        """啟動 VLC 播放位置的定時更新"""
        if not self.use_vlc or not self.vlc_player or not self.is_video_mode:
            return

        # 先更新一次
        self._update_video_label()

        # 持續定時更新
        if self.video_playback_id:
            self.root.after_cancel(self.video_playback_id)
        self.video_playback_id = self.root.after(100, self._update_vlc_position_loop)

    def _start_video_playback(self):
        # Try VLC first
        if self.use_vlc and self.vlc_player and self.vlc_player.player:
            try:
                self.vlc_player.play()
                self.is_playing = True
                self.btn_video_play.config(text='⏸')
                self._start_vlc_position_update()
                return
            except:
                pass

        # Fall back to OpenCV
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

        # 若 VLC 正在使用則停止
        if self.use_vlc and self.vlc_player:
            try:
                self.vlc_player.pause()
            except:
                pass

        if self.video_playback_id:
            self.root.after_cancel(self.video_playback_id)
            self.video_playback_id = None

    def generate_video_filename(self, extension='.png'):
        video_path = None

        # Try VLC first
        if self.use_vlc and self.vlc_player:
            video_path = self.vlc_player.video_path

        # Fall back to OpenCV
        if not video_path and self.video_handler:
            video_path = self.video_handler.video_path

        if not video_path:
            return self.generate_auto_filename(extension)

        video_name = os.path.splitext(os.path.basename(video_path))[0]

        # 取得目前幀編號
        frame_num = 0
        if self.use_vlc and self.vlc_player and self.vlc_player.player:
            try:
                current_time = self.vlc_player.get_time()
                fps = self.vlc_player.get_fps()
                if fps > 0:
                    frame_num = int(current_time / 1000 * fps)
            except:
                pass
        elif self.video_handler:
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
