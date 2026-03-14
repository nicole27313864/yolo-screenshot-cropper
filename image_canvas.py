import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import math


class CropCanvas(ttk.Frame):
    CROP_BORDER_COLOR = '#FF6B35'
    CROP_HANDLE_COLOR = '#FF6B35'
    MASK_COLOR = '#000000'
    MIN_CROP_SIZE = 50
    HANDLE_SIZE = 10

    def __init__(self, parent, on_crop_change=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.on_crop_change = on_crop_change

        self.original_image = None
        self.display_image = None
        self.tk_image = None

        self.canvas = tk.Canvas(
            self,
            bg='#1A1A1A',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind('<Configure>', self._on_canvas_resize)

        self.image_id = None
        self.mask_id = None
        self.crop_rect_id = None
        self.handle_ids = []

        self.img_x = 0
        self.img_y = 0
        self.img_width = 0
        self.img_height = 0
        self.scale = 1.0

        self.crop_x = 0
        self.crop_y = 0
        self.crop_width = 640
        self.crop_height = 640

        self.dragging = False
        self.resizing = False
        self.resize_handle = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.initial_crop_x = 0
        self.initial_crop_y = 0
        self.initial_crop_width = 0
        self.initial_crop_height = 0

        self._setup_bindings()

    def _setup_bindings(self):
        self.canvas.bind('<Button-1>', self._on_mouse_down)
        self.canvas.bind('<B1-Motion>', self._on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_mouse_up)

    def _on_canvas_resize(self, event):
        if self.original_image:
            self._update_display_image()

    def load_image(self, image_path):
        try:
            self.original_image = Image.open(image_path)
            if self.original_image.mode not in ('RGB', 'RGBA'):
                self.original_image = self.original_image.convert('RGB')

            self.img_width = self.original_image.width
            self.img_height = self.original_image.height

            self._update_display_image()
            self._center_crop_box()

            return True
        except Exception as e:
            print(f'載入圖片失敗: {e}')
            return False

    def set_image_from_pil(self, pil_image):
        try:
            self.original_image = pil_image.copy()
            if self.original_image.mode not in ('RGB', 'RGBA'):
                self.original_image = self.original_image.convert('RGB')

            self.img_width = self.original_image.width
            self.img_height = self.original_image.height

            self._update_display_image()
            self._center_crop_box()

            return True
        except Exception as e:
            print(f'載入圖片失敗: {e}')
            return False

    def _update_display_image(self):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            self.after(100, self._update_display_image)
            return

        canvas_ratio = canvas_width / canvas_height
        image_ratio = self.img_width / self.img_height

        if image_ratio > canvas_ratio:
            self.display_width = canvas_width
            self.display_height = int(canvas_width / image_ratio)
        else:
            self.display_height = canvas_height
            self.display_width = int(canvas_height * image_ratio)

        self.scale = self.display_width / self.img_width

        display_img = self.original_image.resize(
            (self.display_width, self.display_height),
            Image.LANCZOS
        )
        self.tk_image = ImageTk.PhotoImage(display_img)

        if self.image_id:
            self.canvas.delete(self.image_id)

        self.img_x = (canvas_width - self.display_width) // 2
        self.img_y = (canvas_height - self.display_height) // 2

        self.image_id = self.canvas.create_image(
            self.img_x, self.img_y,
            anchor=tk.NW,
            image=self.tk_image
        )

        self._redraw_crop()

    def _center_crop_box(self):
        self.crop_x = (self.img_width - self.crop_width) // 2
        self.crop_y = (self.img_height - self.crop_height) // 2

        self.crop_x = max(0, min(self.crop_x, self.img_width - self.crop_width))
        self.crop_y = max(0, min(self.crop_y, self.img_height - self.crop_height))

        self._redraw_crop()

    def center_crop_box(self):
        self._center_crop_box()

    def set_crop_size(self, width, height):
        self.crop_width = max(self.MIN_CROP_SIZE, min(width, self.img_width))
        self.crop_height = max(self.MIN_CROP_SIZE, min(height, self.img_height))

        if self.crop_x + self.crop_width > self.img_width:
            self.crop_x = max(0, self.img_width - self.crop_width)
        if self.crop_y + self.crop_height > self.img_height:
            self.crop_y = max(0, self.img_height - self.crop_height)

        self._redraw_crop()

    def get_crop_region(self):
        return {
            'x': int(self.crop_x),
            'y': int(self.crop_y),
            'width': int(self.crop_width),
            'height': int(self.crop_height)
        }

    def _redraw_crop(self):
        self.canvas.delete('crop_elements')

        if not self.original_image:
            return

        crop_display_x = self.img_x + self.crop_x * self.scale
        crop_display_y = self.img_y + self.crop_y * self.scale
        crop_display_width = self.crop_width * self.scale
        crop_display_height = self.crop_height * self.scale

        self.mask_id = self.canvas.create_rectangle(
            self.img_x, self.img_y,
            self.img_x + self.display_width,
            self.img_y + self.display_height,
            fill=self.MASK_COLOR,
            stipple='gray50',
            tags='crop_elements'
        )

        self.canvas.create_rectangle(
            crop_display_x, crop_display_y,
            crop_display_x + crop_display_width,
            crop_display_y + crop_display_height,
            outline=self.CROP_BORDER_COLOR,
            width=2,
            tags='crop_elements'
        )

        self.crop_rect_id = self.canvas.create_rectangle(
            crop_display_x, crop_display_y,
            crop_display_x + crop_display_width,
            crop_display_y + crop_display_height,
            outline='',
            fill='',
            tags='crop_elements'
        )

        handles = [
            ('nw', crop_display_x, crop_display_y),
            ('ne', crop_display_x + crop_display_width, crop_display_y),
            ('sw', crop_display_x, crop_display_y + crop_display_height),
            ('se', crop_display_x + crop_display_width, crop_display_y + crop_display_height),
        ]

        self.handle_ids = []
        for handle_name, hx, hy in handles:
            handle_id = self.canvas.create_rectangle(
                hx - self.HANDLE_SIZE // 2,
                hy - self.HANDLE_SIZE // 2,
                hx + self.HANDLE_SIZE // 2,
                hy + self.HANDLE_SIZE // 2,
                fill=self.CROP_HANDLE_COLOR,
                outline='#FFFFFF',
                width=1,
                tags='crop_elements'
            )
            self.handle_ids.append((handle_name, handle_id))

        dim_text = f'{int(self.crop_width)} x {int(self.crop_height)}'
        text_x = crop_display_x + crop_display_width / 2
        text_y = crop_display_y + crop_display_height - 20
        
        self.canvas.create_text(
            text_x, text_y,
            text=dim_text,
            fill='#FFFFFF',
            font=('Microsoft JhengHei', 10, 'bold'),
            tags='crop_elements'
        )

        self.canvas.tag_lower(self.mask_id)

        if self.on_crop_change:
            self.on_crop_change(self.get_crop_region())

    def _on_mouse_down(self, event):
        if not self.original_image:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        crop_display_x = self.img_x + self.crop_x * self.scale
        crop_display_y = self.img_y + self.crop_y * self.scale
        crop_display_width = self.crop_width * self.scale
        crop_display_height = self.crop_height * self.scale

        for handle_name, handle_id in self.handle_ids:
            coords = self.canvas.coords(handle_id)
            if coords:
                hx1, hy1, hx2, hy2 = coords
                if hx1 - 5 <= event.x <= hx2 + 5 and hy1 - 5 <= event.y <= hy2 + 5:
                    self.resizing = True
                    self.resize_handle = handle_name
                    self.drag_start_x = event.x
                    self.drag_start_y = event.y
                    self.initial_crop_x = self.crop_x
                    self.initial_crop_y = self.crop_y
                    self.initial_crop_width = self.crop_width
                    self.initial_crop_height = self.crop_height
                    return

        if (crop_display_x <= event.x <= crop_display_x + crop_display_width and
            crop_display_y <= event.y <= crop_display_y + crop_display_height):
            self.dragging = True
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self.initial_crop_x = self.crop_x
            self.initial_crop_y = self.crop_y

    def _on_mouse_drag(self, event):
        if not self.original_image:
            return

        if self.resizing:
            self._handle_resize(event)
        elif self.dragging:
            self._handle_drag(event)

    def _handle_drag(self, event):
        dx = (event.x - self.drag_start_x) / self.scale
        dy = (event.y - self.drag_start_y) / self.scale

        new_x = self.initial_crop_x + dx
        new_y = self.initial_crop_y + dy

        new_x = max(0, min(new_x, self.img_width - self.crop_width))
        new_y = max(0, min(new_y, self.img_height - self.crop_height))

        self.crop_x = new_x
        self.crop_y = new_y

        self._redraw_crop()

    def _handle_resize(self, event):
        dx = (event.x - self.drag_start_x) / self.scale
        dy = (event.y - self.drag_start_y) / self.scale

        new_x = self.initial_crop_x
        new_y = self.initial_crop_y
        new_width = self.initial_crop_width
        new_height = self.initial_crop_height

        if 'w' in self.resize_handle:
            new_x = self.initial_crop_x + dx
            new_width = self.initial_crop_width - dx
        if 'e' in self.resize_handle:
            new_width = self.initial_crop_width + dx

        if 'n' in self.resize_handle:
            new_y = self.initial_crop_y + dy
            new_height = self.initial_crop_height - dy
        if 's' in self.resize_handle:
            new_height = self.initial_crop_height + dy

        if new_width < self.MIN_CROP_SIZE:
            if 'w' in self.resize_handle:
                new_x = self.initial_crop_x + self.initial_crop_width - self.MIN_CROP_SIZE
            new_width = self.MIN_CROP_SIZE

        if new_height < self.MIN_CROP_SIZE:
            if 'n' in self.resize_handle:
                new_y = self.initial_crop_y + self.initial_crop_height - self.MIN_CROP_SIZE
            new_height = self.MIN_CROP_SIZE

        if new_x < 0:
            new_x = 0
        if new_y < 0:
            new_y = 0
        if new_x + new_width > self.img_width:
            new_width = self.img_width - new_x
        if new_y + new_height > self.img_height:
            new_height = self.img_height - new_y

        self.crop_x = new_x
        self.crop_y = new_y
        self.crop_width = new_width
        self.crop_height = new_height

        self._redraw_crop()

    def _on_mouse_up(self, event):
        self.dragging = False
        self.resizing = False
        self.resize_handle = None

    def reset(self):
        self.original_image = None
        self.display_image = None
        self.tk_image = None

        self.canvas.delete('all')
        self.image_id = None
        self.mask_id = None
        self.crop_rect_id = None
        self.handle_ids = []

        self.img_x = 0
        self.img_y = 0
        self.img_width = 0
        self.img_height = 0
        self.scale = 1.0

        self.crop_x = 0
        self.crop_y = 0
        self.crop_width = 640
        self.crop_height = 640

    def has_image(self):
        return self.original_image is not None
