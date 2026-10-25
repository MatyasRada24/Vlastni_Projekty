"""Real Tk integration: native awareness, proportional scaling and state retention."""
import ctypes
import sys
import tkinter as tk
from tkinter import font, ttk

from seo_checker.app import Application
from seo_checker.dpi import enable_high_dpi
from seo_checker.engine import audit_local

enable_high_dpi()
root = tk.Tk()
root.withdraw()
app = Application(root, database=":memory:")
root.after_cancel(app._dpi_after)  # Synthetic DPI changes must not be reset to the real monitor.
if sys.platform == "win32":
    user32 = ctypes.WinDLL("user32")
    user32.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    user32.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    assert user32.GetAwarenessFromDpiAwarenessContext(user32.GetThreadDpiAwarenessContext()) == 2

app.mode.set("Soubory")
app.path.set("priklady/ukazkovy-web.html")
app.switch_mode()
report = audit_local(app.path.get())
app.events.put(("done", report))
app.poll()
app.status_filter.set("Doporučení")
app.refresh()
app.tree.selection_set("1")
app.show_detail()
chosen = app.detail.get("1.0", "end")
heights = []
for dpi in (96, 120, 144, 192, 96):
    app.apply_dpi(dpi)
    root.update_idletasks()
    assert app.report is report and app.status_filter.get() == "Doporučení"
    assert app.detail.get("1.0", "end") == chosen
    assert app.mode.get() == "Soubory" and app.files_frame.winfo_manager() == "pack"
    assert not app.url_frame.winfo_manager()
    assert app.path.get() == "priklady/ukazkovy-web.html"
    assert int(app.input_panel.cget("height")) >= round(108 * dpi / 96)
    assert int(ttk.Style(root).lookup("Treeview", "rowheight")) == round(34 * dpi / 96)
    heights.append(font.Font(root, font=app.url_entry.cget("font")).metrics("linespace"))
    app.set_running(True)
    assert int(app.input_panel.cget("height")) == round(120 * dpi / 96)
    app.set_running(False)
assert heights[1] > heights[0] and heights[2] > heights[1] and heights[3] > heights[2], heights
assert heights[-1] == heights[0], heights
app.set_running(True)
app.apply_dpi(120)
assert app.running and app.stop_button.winfo_manager() == "pack"
assert app.start_button.instate(["disabled"])
app.close()
print("DPI smoke passed: Per-Monitor awareness, 100/125/150/200%, report/filter/selection/source/worker preserved; font heights", heights)
