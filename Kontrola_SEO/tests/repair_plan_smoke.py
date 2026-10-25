"""Exercise repair guidance, persisted rechecks and cancellation without live sites."""
import threading
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

from seo_checker.app import Application
from seo_checker.dpi import enable_high_dpi
from seo_checker.engine import audit_local
from seo_checker.planning import issue_key
from seo_checker.workspace import PlanWindow
from tests.insights_smoke import screenshot
from tests.test_engine import GOOD, temporary_directory


def wait(app, root):
    deadline = time.monotonic() + 5
    while app.running and time.monotonic() < deadline:
        root.update()
        time.sleep(.02)
    root.update()
    assert not app.running


def choose_title(plan):
    index = next(i for i, task in enumerate(plan.tasks) if task.code == 'Titulek stránky')
    plan.tree.selection_set(str(index))
    plan.select()


def run():
    enable_high_dpi()
    with temporary_directory() as folder:
        file = Path(folder)/'web.html'
        file.write_text('<h1>Opravy notebooků</h1>', encoding='utf-8')
        root = tk.Tk()
        app = Application(root, database=Path(folder)/'db.sqlite3')
        try:
            report = audit_local(str(file))
            app.project_id, app.audit_id = app.store.save(report)
            app.display_report(report)
            plan = PlanWindow(app)
            app.plan_window = plan
            root.update()
            choose_title(plan)
            assert '<title>Opravy notebooků</title>' in plan.detail.get('1.0', 'end')
            plan.occurrence.current(1)
            plan.select_occurrence()
            assert 'Proč priorita P2' in plan.detail.get('1.0', 'end')
            screenshot(plan, 'repair-guide.png')
            file.write_text(GOOD, encoding='utf-8')
            original = app.store.load(app.audit_id)[1].to_dict()
            plan.recheck()
            assert plan.verify_button.instate(['disabled'])
            wait(app, root)
            assert 'Opraveno: 1' in plan.verification_detail.get('1.0', 'end')
            assert len(app.store.audits(app.project_id)) == 1
            assert app.store.load(app.audit_id)[1].to_dict() == original
            assert app.report is report
            assert not app.store.states(app.project_id)
            screenshot(plan, 'repair-verified.png')
            saved = app.store.repair_checks(app.audit_id)
            plan.win.destroy()
            plan = PlanWindow(app)
            app.plan_window = plan
            root.update()
            choose_title(plan)
            assert 'Opraveno: 1' in plan.verification_detail.get('1.0', 'end')
            # The user cancels before a late successful response arrives.
            release = threading.Event()
            with patch('seo_checker.repairs.verify_repairs', side_effect=lambda *a, **kw: (release.wait(3), {'results': []})[1]):
                plan.recheck()
                plan.stop_recheck()
                release.set()
                wait(app, root)
            assert 'zastaveno' in plan.recheck_status.cget('text')
            assert app.store.repair_checks(app.audit_id) == saved
            assert plan.verify_button.instate(['!disabled'])
            # Closing only the plan cancels its work and releases the main UI.
            release = threading.Event()
            with patch('seo_checker.repairs.verify_repairs', side_effect=lambda *a, **kw: (release.wait(3), {'results': []})[1]):
                plan.recheck()
                plan.win.destroy()
                release.set()
                wait(app, root)
            assert app.store.repair_checks(app.audit_id) == saved
        finally:
            app.close()
    print('Repair plan UI passed: guidance, selected recheck, immutable audit, persisted results, cancel and close')


if __name__ == '__main__':
    run()
