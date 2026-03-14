import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image


SUPPORTED_FORMATS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']


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
