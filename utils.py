import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image


SUPPORTED_FORMATS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']


def get_supported_filetypes():
    return [
        ('圖片檔案', '*.png *.jpg *.jpeg *.bmp *.gif *.webp'),
        ('PNG', '*.png'),
        ('JPEG', '*.jpg *.jpeg'),
        ('BMP', '*.bmp'),
        ('GIF', '*.gif'),
        ('WebP', '*.webp'),
        ('所有檔案', '*.*')
    ]


def is_supported_image(path):
    if not path:
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in SUPPORTED_FORMATS


def open_file_dialog():
    filepath = filedialog.askopenfilename(
        title='選擇圖片',
        filetypes=get_supported_filetypes()
    )
    return filepath


def save_file_dialog(default_name=''):
    filepath = filedialog.askdirectory(
        title='選擇輸出資料夾'
    )
    return filepath


def select_output_directory():
    directory = filedialog.askdirectory(title='選擇輸出資料夾')
    return directory


def get_image_info(image_path):
    try:
        with Image.open(image_path) as img:
            return {
                'width': img.width,
                'height': img.height,
                'format': img.format,
                'mode': img.mode
            }
    except Exception as e:
        return None


def validate_crop_region(img_width, img_height, x, y, crop_width, crop_height):
    x = max(0, min(x, img_width - 50))
    y = max(0, min(y, img_height - 50))

    if x + crop_width > img_width:
        crop_width = img_width - x
    if y + crop_height > img_height:
        crop_height = img_height - y

    crop_width = max(50, crop_width)
    crop_height = max(50, crop_height)

    return x, y, crop_width, crop_height


def center_crop_in_image(img_width, img_height, crop_width, crop_height):
    if img_width <= crop_width:
        x = 0
        crop_width = img_width
    else:
        x = (img_width - crop_width) // 2

    if img_height <= crop_height:
        y = 0
        crop_height = img_height
    else:
        y = (img_height - crop_height) // 2

    return x, y


def _center_on_parent(window, parent):
    if parent is None:
        return
    window.update_idletasks()
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_w = parent.winfo_width()
    parent_h = parent.winfo_height()

    win_w = window.winfo_width()
    win_h = window.winfo_height()

    x = parent_x + (parent_w // 2) - (win_w // 2)
    y = parent_y + (parent_h // 2) - (win_h // 2)
    window.geometry(f'+{x}+{y}')


def show_error(title, message, parent=None, play_sound=True):
    if play_sound:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONHAND)
    if parent is None:
        messagebox.showerror(title, message)
        return
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry('350x150')
    dialog.configure(bg='#1A1A1A')
    dialog.transient(parent)
    dialog.grab_set()
    _center_on_parent(dialog, parent)

    tk.Label(dialog, text='⚠️', font=('Arial', 24), bg='#1A1A1A', fg='#FF6B6B').pack(pady=(15, 5))
    tk.Label(dialog, text=message, bg='#1A1A1A', fg='#FFFFFF', wraplength=300, justify='center').pack(pady=5)
    tk.Button(dialog, text='確定', command=dialog.destroy, bg='#4A4A4A', fg='#FFFFFF',
              relief='flat', padx=20, pady=5).pack(pady=10)


def show_info(title, message, parent=None, play_sound=True):
    if play_sound:
        import winsound
        winsound.MessageBeep(winsound.MB_OK)
    if parent is None:
        messagebox.showinfo(title, message)
        return
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry('350x150')
    dialog.configure(bg='#1A1A1A')
    dialog.transient(parent)
    dialog.grab_set()
    _center_on_parent(dialog, parent)

    tk.Label(dialog, text='ℹ️', font=('Arial', 24), bg='#1A1A1A', fg='#4ECDC4').pack(pady=(15, 5))
    tk.Label(dialog, text=message, bg='#1A1A1A', fg='#FFFFFF', wraplength=300, justify='center').pack(pady=5)
    tk.Button(dialog, text='確定', command=dialog.destroy, bg='#4A4A4A', fg='#FFFFFF',
              relief='flat', padx=20, pady=5).pack(pady=10)

    dialog.wait_window()


def show_warning(title, message, parent=None, play_sound=True):
    if play_sound:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    if parent is None:
        messagebox.showwarning(title, message)
        return
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry('350x150')
    dialog.configure(bg='#1A1A1A')
    dialog.transient(parent)
    dialog.grab_set()
    _center_on_parent(dialog, parent)

    tk.Label(dialog, text='⚡', font=('Arial', 24), bg='#1A1A1A', fg='#FFE66D').pack(pady=(15, 5))
    tk.Label(dialog, text=message, bg='#1A1A1A', fg='#FFFFFF', wraplength=300, justify='center').pack(pady=5)
    tk.Button(dialog, text='確定', command=dialog.destroy, bg='#4A4A4A', fg='#FFFFFF',
              relief='flat', padx=20, pady=5).pack(pady=10)


def ask_overwrite(filepath, parent=None):
    if parent is None:
        return messagebox.askyesno('檔案已存在', f'檔案 "{os.path.basename(filepath)}" 已存在，是否覆蓋?')

    dialog = tk.Toplevel(parent)
    dialog.title('檔案已存在')
    dialog.geometry('400x180')
    dialog.configure(bg='#1A1A1A')
    dialog.transient(parent)
    dialog.grab_set()
    _center_on_parent(dialog, parent)

    result = [None]

    tk.Label(
        dialog,
        text=f'檔案 "{os.path.basename(filepath)}" 已存在，是否覆蓋?',
        bg='#1A1A1A',
        fg='#FFFFFF',
        wraplength=350
    ).pack(pady=20)

    btn_frame = tk.Frame(dialog, bg='#1A1A1A')
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text='是', command=lambda: dialog.destroy() or result.__setitem__(0, True),
              bg='#4A4A4A', fg='#FFFFFF', relief='flat', padx=20, pady=5).pack(side='left', padx=10)
    tk.Button(btn_frame, text='否', command=lambda: dialog.destroy() or result.__setitem__(0, False),
              bg='#4A4A4A', fg='#FFFFFF', relief='flat', padx=20, pady=5).pack(side='left', padx=10)

    dialog.wait_window()
    return result[0]


def get_unique_filepath(directory, filename):
    base_name, ext = os.path.splitext(filename)
    filepath = os.path.join(directory, filename)
    counter = 1

    while os.path.exists(filepath):
        new_filename = f"{base_name}_{counter}{ext}"
        filepath = os.path.join(directory, new_filename)
        counter += 1

    return filepath


def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))


def get_video_filetypes():
    return [
        ('影片檔案', '*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm'),
        ('MP4', '*.mp4'),
        ('AVI', '*.avi'),
        ('MOV', '*.mov'),
        ('MKV', '*.mkv'),
        ('所有影片', '*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm'),
        ('所有檔案', '*.*')
    ]


def is_supported_video(path):
    if not path:
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in SUPPORTED_VIDEO_FORMATS


def open_video_dialog():
    filepath = filedialog.askopenfilename(
        title='選擇影片',
        filetypes=get_video_filetypes()
    )
    return filepath


class VideoHandler:
    def __init__(self):
        self.cap = None
        self.video_path = None
        self.total_frames = 0
        self.fps = 0
        self.current_frame = 0
        self.frame_cache = {}
        self.max_cache_size = 50

    def open(self, video_path):
        try:
            import cv2
            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                return False, "無法開啟影片"

            self.video_path = video_path
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.current_frame = 0
            self.frame_cache = {}
            return True, f"已開啟影片: {self.total_frames} 幀, {self.fps:.2f} FPS"
        except Exception as e:
            return False, f"開啟影片失敗: {str(e)}"

    def get_frame(self, frame_number):
        import cv2
        if not self.cap or frame_number < 0 or frame_number >= self.total_frames:
            return None

        if frame_number in self.frame_cache:
            return self.frame_cache[frame_number]

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if len(self.frame_cache) >= self.max_cache_size:
                oldest_key = min(self.frame_cache.keys())
                del self.frame_cache[oldest_key]
            self.frame_cache[frame_number] = frame
            return frame
        return None

    def get_frame_as_pil(self, frame_number):
        import cv2
        frame = self.get_frame(frame_number)
        if frame is None:
            return None
        return Image.fromarray(frame)

    def get_current_frame_as_pil(self):
        return self.get_frame_as_pil(self.current_frame)

    def next_frame(self):
        if self.current_frame < self.total_frames - 1:
            self.current_frame += 1
            return self.get_current_frame_as_pil()
        return None

    def prev_frame(self):
        if self.current_frame > 0:
            self.current_frame -= 1
            return self.get_current_frame_as_pil()
        return None

    def seek_to(self, frame_number):
        if 0 <= frame_number < self.total_frames:
            self.current_frame = frame_number
            return self.get_current_frame_as_pil()
        return None

    def get_frame_number(self):
        return self.current_frame

    def get_total_frames(self):
        return self.total_frames

    def get_fps(self):
        return self.fps

    def get_duration_seconds(self):
        if self.fps > 0:
            return self.total_frames / self.fps
        return 0

    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()

    def close(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        self.video_path = None
        self.total_frames = 0
        self.fps = 0
        self.current_frame = 0
        self.frame_cache = {}


class VLCVideoPlayer:
    """VLC 嵌入播放器 - 使用硬體加速，流暢播放"""

    def __init__(self, parent_window):
        self.parent = parent_window
        self.instance = None
        self.player = None
        self.media = None
        self.video_path = None
        self.is_playing = False

    def open(self, video_path):
        try:
            import vlc
            self.video_path = video_path

            # 建立 VLC instance - 禁用硬體加速以避免嵌入式問題
            self.instance = vlc.Instance('--avcodec-hw=none')
            self.player = self.instance.media_player_new()

            # 建立 media 並載入
            self.media = self.instance.media_new(video_path)
            self.player.set_media(self.media)

            return True, f"已載入: {os.path.basename(video_path)}"
        except Exception as e:
            return False, f"VLC 載入失敗: {str(e)}\n請確認已安裝 VLC 播放器"

    def get_hwnd(self):
        """取得視窗 handle 用於嵌入"""
        if self.player:
            return self.player.get_hwnd()
        return None

    def play(self):
        if self.player:
            self.player.play()
            self.is_playing = True

    def pause(self):
        if self.player:
            self.player.pause()
            self.is_playing = False

    def toggle_play(self):
        if self.player:
            if self.is_playing:
                self.pause()
            else:
                self.play()

    def stop(self):
        if self.player:
            self.player.stop()
            self.is_playing = False

    def seek(self, position):
        """跳轉到指定位置 (0.0 - 1.0)"""
        if self.player:
            self.player.set_position(position)

    def get_position(self):
        """取得目前播放位置 (0.0 - 1.0)"""
        if self.player:
            return self.player.get_position()
        return 0.0

    def get_time(self):
        """取得目前時間 (毫秒)"""
        if self.player:
            return self.player.get_time()
        return 0

    def set_time(self, time_ms):
        """設定目前時間 (毫秒)"""
        if self.player:
            self.player.set_time(time_ms)

    def get_length(self):
        """取得影片長度 (毫秒)"""
        if self.player:
            return self.player.get_length()
        return 0

    def get_fps(self):
        """取得 FPS"""
        if self.player:
            return self.player.get_fps()
        return 0

    def is_playing_state(self):
        if self.player:
            return self.player.is_playing()
        return False

    def get_frame_at_time(self, time_ms):
        """取得指定時間的幀 (用於裁剪)"""
        try:
            import cv2
            if not self.video_path:
                return None

            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                return None

            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30

            frame_number = int(time_ms / 1000 * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

            ret, frame = cap.read()
            cap.release()

            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return Image.fromarray(frame)
            return None
        except Exception:
            return None

    def close(self):
        if self.player:
            self.player.stop()
            self.player = None
        if self.instance:
            self.instance.release()
            self.instance = None
        self.media = None
        self.video_path = None
        self.is_playing = False
