"""Shared desktop palette and lightweight rounded surfaces; no extra runtime dependencies."""
import tkinter as tk
from .dpi import pixels

BG = "#f3f5fa"
SURFACE = "#ffffff"
INK = "#161b2e"
MUTED = "#5f6782"
LINE = "#e2e6f0"
ACCENT = "#4f46e5"
ACCENT_DARK = "#3730a3"
ACCENT_SOFT = "#eef0ff"
SOFT = "#f7f8fc"
CONTROL = "#eef0f7"
SIDEBAR = "#141a2e"
SIDEBAR_ACTIVE = "#262e50"
SIDEBAR_TEXT = "#a9b0cc"
DANGER = "#d1343a"
WARNING = "#b4690e"
SUCCESS = "#16803c"
NEUTRAL = "#64708a"
ROW_HEIGHT = 38
STATUS_COLORS = {"Chyba": DANGER, "Doporučení": WARNING, "Správně": SUCCESS, "Neověřeno": NEUTRAL}
STATUS_SOFT = {"Chyba": "#fdecec", "Doporučení": "#fff4e0", "Správně": "#e8f6ed", "Neověřeno": "#eef1f6"}


def status_icon(parent, status, size=24, background=SURFACE):
    scale = getattr(parent.winfo_toplevel(), 'dpi_scale', 1.0)
    n = pixels(size, scale)
    canvas = tk.Canvas(parent, width=n, height=n, bg=background, bd=0, highlightthickness=0)
    canvas.create_oval(1, 1, n-1, n-1, fill=STATUS_COLORS[status], outline='')
    canvas.create_text(n/2, n/2, text={'Chyba': '!', 'Doporučení': '!', 'Správně': '✓', 'Neověřeno': '?'}[status],
                       fill='white', font=('Segoe UI Semibold', max(9, round(size*.42))))
    return canvas


def status_image(parent, status, size=10):
    """Small DPI-sized status dots for native Treeview, without image dependencies."""
    n = pixels(size, getattr(parent.winfo_toplevel(), 'dpi_scale', 1.0))
    result = tk.PhotoImage(master=parent, width=n, height=n)
    for y in range(n):
        for x in range(n):
            if (x-(n-1)/2)**2 + (y-(n-1)/2)**2 <= (n/2-.5)**2:
                result.put(STATUS_COLORS[status], (x, y))
    return result


def readable(value):
    return str(value).replace('HTML=True', 'HTML stránka').replace('HTML=False', 'nejde o HTML').replace('noindex=True', 'indexování zakázáno (noindex)').replace('noindex=False', 'bez zákazu indexování')


class Surface(tk.Canvas):
    """A rounded panel with a regular Tk frame inside for native controls."""
    def __init__(self, parent, *, color=SURFACE, background=BG, radius=16, padding=20, fit_height=False, border=LINE, **kwargs):
        scale = getattr(parent.winfo_toplevel(), "dpi_scale", 1.0)
        radius, padding = pixels(radius, scale), pixels(padding, scale)
        for key in ("width", "height"):
            if key in kwargs:
                kwargs[key] = pixels(kwargs[key], scale)
        super().__init__(parent, bg=background, highlightthickness=0, bd=0, **kwargs)
        self.color, self.radius, self.padding, self.border = color, radius, padding, border
        self.body = tk.Frame(self, bg=color)
        self.window = self.create_window(padding, padding, window=self.body, anchor="nw")
        self.bind("<Configure>", self._resize)
        if fit_height:
            self.minimum_height = int(kwargs.get("height", 0))
            self.body.bind("<Configure>", self._fit_height)

    def _fit_height(self, event):
        height = max(self.minimum_height, self.body.winfo_reqheight() + 2*self.padding)
        if int(self.cget("height")) != height:
            self.configure(height=height)

    def _resize(self, event):
        # Inset by one pixel so the hairline border is not clipped by the canvas edge.
        w, h, r = event.width - 1, event.height - 1, self.radius
        self.delete("surface")
        points = (r, 1, w-r, 1, w, 1, w, r, w, h-r, w, h, w-r, h, r, h, 1, h, 1, h-r, 1, r, 1, 1)
        self.create_polygon(points, smooth=True, splinesteps=24, fill=self.color, outline=self.border or "", tags="surface")
        self.tag_lower("surface")
        w, h = event.width, event.height
        self.itemconfigure(self.window, width=max(1, w-2*self.padding), height=max(1, h-2*self.padding))

    def set_color(self, color, border=None):
        self.color = color
        self.body.configure(bg=color)
        self.itemconfigure("surface", fill=color, outline=border or self.border or "")


def mark(parent, size=36, background=SURFACE):
    """Brand mark: a rounded accent tile with a magnifier and check."""
    scale = getattr(parent.winfo_toplevel(), "dpi_scale", 1.0)
    canvas = tk.Canvas(parent, width=size, height=size, bg=background, bd=0, highlightthickness=0)
    r = size * .28
    canvas.create_polygon(r, 0, size-r, 0, size, 0, size, r, size, size-r, size, size, size-r, size, r, size,
                          0, size, 0, size-r, 0, r, 0, 0, smooth=True, splinesteps=24, fill=ACCENT, outline="", width=0)
    canvas.create_oval(size*.22, size*.2, size*.66, size*.64, outline="white", width=max(1.5, size/16))
    canvas.create_line(size*.62, size*.6, size*.78, size*.76, fill="white", width=max(2, size/11), capstyle="round")
    canvas.create_line(size*.33, size*.42, size*.42, size*.51, size*.56, size*.33, fill="white", width=max(1.5, size/18),
                       capstyle="round", joinstyle="round")
    canvas.scale("all", 0, 0, scale, scale)
    for item in canvas.find_all():
        canvas.itemconfigure(item, width=float(canvas.itemcget(item, "width")) * scale)
    canvas.configure(width=pixels(size, scale), height=pixels(size, scale))
    return canvas
