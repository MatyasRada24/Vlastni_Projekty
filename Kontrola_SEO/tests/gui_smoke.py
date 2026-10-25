"""Integration smoke check: GUI, background audit, filtering and result selection."""
import time
import tkinter as tk
from pathlib import Path

from seo_checker.app import Application
from seo_checker.dpi import enable_high_dpi


enable_high_dpi()
root = tk.Tk()
root.withdraw()
app = Application(root, database=":memory:")
app.start()
assert app.error_banner.grid_info(), "Empty source must show inline validation"
assert not app.running
app.mode.set("Soubory")
app.switch_mode()
assert not app.error_banner.grid_info(), "Mode switch must clear validation"
app.path.set(str(Path(__file__).resolve().parents[1] / "priklady" / "ukazkovy-web.html"))
app.start()
deadline = time.monotonic() + 10
while app.running and time.monotonic() < deadline:
    root.update()
    time.sleep(0.02)
assert not app.running, "Audit did not finish"
assert app.report is not None and len(app.report.pages) == 1
assert app.tree.get_children(), "No findings in UI"
app.status_filter.set("Doporučení")
app.refresh()
assert app.rows and all(f.status == "Doporučení" for p, f in app.rows.values())
assert "Meta description" in app.detail.get("1.0", "end")
app.status_filter.set("Chyba")
app.refresh()
assert not app.rows and app.empty.grid_info(), "Empty filter needs an empty state"
app.status_filter.set("Všechny stavy")
app.refresh()
assert not app.empty.grid_info(), "Results must replace the empty state"
app.set_running(True)
assert app.stop_button.winfo_manager() == "pack"
assert app.start_button.instate(["disabled"])
app.stop()
assert app.cancel.is_set()
app.events.put(("error", "Test dostupnosti zdroje"))
app.poll()
assert not app.running and app.report is not None, "Failed new audit must preserve prior results"
assert app.error_banner.grid_info()
assert not app.stop_button.winfo_manager()
app.mode.set("URL")
app.switch_mode()
root.update()
app.close()
print("GUI smoke check passed: audit, filters, details, validation, empty state, cancellation, error recovery")
