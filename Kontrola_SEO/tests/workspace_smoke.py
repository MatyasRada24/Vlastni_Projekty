"""End-to-end desktop workflow: audit, save task state, re-audit, compare, reopen."""
import time
import tkinter as tk
from pathlib import Path

from seo_checker.app import Application
from seo_checker.dpi import enable_high_dpi
from seo_checker.workspace import HistoryWindow, PlanWindow
from tests.test_engine import GOOD, temporary_directory


def wait(app, root):
    deadline = time.monotonic() + 10
    while app.running and time.monotonic() < deadline:
        root.update()
        time.sleep(.02)
    assert not app.running and app.audit_id
    root.update()


enable_high_dpi()
with temporary_directory() as folder:
    file = Path(folder) / "web.html"
    file.write_text("<h1>Test</h1>", encoding="utf-8")
    root = tk.Tk()
    root.withdraw()
    app = Application(root, database=Path(folder) / "projects.sqlite3")
    app.mode.set("Soubory")
    app.switch_mode()
    app.path.set(str(file))
    app.start()
    wait(app, root)
    first = app.audit_id
    plan = PlanWindow(app)
    root.update()
    assert plan.tasks and plan.tree.get_children()
    plan.state.set("Záměrné")
    plan.save()
    assert "Záměrné" in app.store.states(app.project_id).values()
    plan.win.destroy()
    file.write_text(GOOD, encoding="utf-8")
    app.start()
    wait(app, root)
    second = app.audit_id
    assert second != first and len(app.store.projects()) == 1
    history = HistoryWindow(app)
    root.update()
    assert len(history.audit_rows) == 2
    assert history.baselines and history.baselines[0]["id"] == first
    assert any(change == "Odstraněné" for change, page, finding in history.change_rows)
    history.audit_picker.current(next(i for i, row in enumerate(history.audit_rows) if row['id'] == first))
    history.select_audit()
    history.open_audit()
    assert app.audit_id == first and not app.running
    old_plan = PlanWindow(app)
    root.update()
    assert old_plan.save_button.instate(["disabled"]), "Historical audit cannot change current work states"
    old_plan.win.destroy()
    assert len(app.store.audits(app.project_id)) == 2, "Opening history must not create another audit"
    app.close()
print("Workspace smoke passed: autosave, repair states, second audit, comparison, reopening immutable history")
