"""Windows DPI setup. Call before creating the first Tk window."""
import ctypes
import sys


def enable_high_dpi():
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        setter = user32.SetProcessDpiAwarenessContext
        setter.argtypes = [ctypes.c_void_p]
        setter.restype = ctypes.c_bool
        # ACCESS_DENIED means the executable manifest already selected a mode.
        if setter(ctypes.c_void_p(-4)) or ctypes.get_last_error() == 5:
            return
    except (AttributeError, OSError):
        pass
    try:
        setter = ctypes.WinDLL("shcore").SetProcessDpiAwareness
        setter.argtypes = [ctypes.c_int]
        setter.restype = ctypes.c_long
        if setter(2) in (0, -2147024891):
            return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.WinDLL("user32").SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def window_dpi(root):
    if sys.platform == "win32":
        try:
            user32 = ctypes.WinDLL("user32")
            user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            user32.GetAncestor.restype = ctypes.c_void_p
            hwnd = user32.GetAncestor(root.winfo_id(), 2)
            user32.GetDpiForWindow.argtypes = [ctypes.c_void_p]
            user32.GetDpiForWindow.restype = ctypes.c_uint
            dpi = user32.GetDpiForWindow(hwnd)
            if dpi:
                return dpi
        except (AttributeError, OSError):
            pass
    return round(float(root.winfo_fpixels("1i")))


def pixels(value, scale):
    """Scale logical pixels, including symmetric/asymmetric Tk paddings."""
    if isinstance(value, (tuple, list)):
        return tuple(pixels(item, scale) for item in value)
    return round(value * scale)


def work_area(root):
    """Available physical pixels on the window's monitor (excluding taskbar)."""
    if sys.platform == "win32":
        from ctypes import wintypes

        class MonitorInfo(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                        ("work", wintypes.RECT), ("flags", wintypes.DWORD)]
        try:
            user32 = ctypes.WinDLL("user32")
            user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
            user32.MonitorFromWindow.restype = wintypes.HANDLE
            user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
            info = MonitorInfo()
            info.size = ctypes.sizeof(info)
            monitor = user32.MonitorFromWindow(root.winfo_id(), 2)
            if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                return info.work.right - info.work.left, info.work.bottom - info.work.top
        except (AttributeError, OSError):
            pass
    return root.winfo_screenwidth(), root.winfo_screenheight()
