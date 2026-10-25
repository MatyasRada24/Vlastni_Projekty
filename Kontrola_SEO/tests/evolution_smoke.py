"""New workflows use isolated databases and local files, without real Google accounts."""
import threading
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

from seo_checker.app import Application
from seo_checker.diagnostics import copy_diagnostic
from seo_checker.dpi import enable_high_dpi
from seo_checker.engine import Report, analyze_html, audit_local
from seo_checker.evolution_ui import PageComparisonWindow, TrendsWindow
from seo_checker.workspace import PlanWindow, HistoryWindow
from tests.insights_smoke import screenshot
from tests.test_engine import temporary_directory


def wait(app):
    deadline = time.monotonic() + 10
    while app.running and time.monotonic() < deadline:
        app.root.update()
        time.sleep(.01)
    app.root.update()
    assert not app.running, 'Audit did not finish'


def run():
    enable_high_dpi()
    with temporary_directory() as folder:
        source, db = Path(folder) / 'site', Path(folder) / 'projects.sqlite3'
        source.mkdir()
        for i in range(3):
            (source / f'{i}.html').write_text('<h1>Test</h1>', encoding='utf-8')
        ready = threading.Event()
        def slow_audit(*args, **kwargs):
            original = kwargs['checkpoint']
            def checkpoint(data):
                original(data)
                if len(data['report']['pages']) == 1:
                    ready.set()
                    kwargs['cancel'].wait(8)
            kwargs['checkpoint'] = checkpoint
            return audit_local(*args, **kwargs)
        root = tk.Tk()
        app = Application(root, database=db)
        app.mode.set('Soubory')
        app.path.set(str(source))
        app.switch_mode()
        with patch('seo_checker.app.audit_local', slow_audit):
            app.start()
            deadline = time.monotonic() + 5
            while not ready.is_set() and time.monotonic() < deadline:
                root.update()
                time.sleep(.01)
            assert ready.is_set()
            root.update()
            assert 'Dokončeno' in app.activity_label.cget('text')
            app.close()
            while app.worker_thread.is_alive():
                time.sleep(.01)
            try:
                app.finish_close()
            except tk.TclError:
                pass
        root = tk.Tk()
        app = Application(root, database=db)
        try:
            root.update()
            assert app.saved_draft and len(app.saved_draft['report']['pages']) == 1
            assert app.resume_bar.winfo_ismapped()
            app.resume_audit()
            wait(app)
            assert len(app.report.pages) == 3 and not app.store.draft()
            assert not app.resume_bar.winfo_ismapped()
            # Populate an independent web project with two real parsed snapshots.
            url = 'https://example.com/'
            before, _ = analyze_html('<title>Starý titulek</title><h1>Původní obsah</h1>', url, True)
            after, _ = analyze_html('<title>Nový titulek</title><h1>Nový obsah</h1><meta name="description" content="Nový popis">', url, True)
            old = Report(url, 'URL', pages=[before])
            new = Report(url, 'URL', pages=[after])
            project, first = app.store.save(old)
            app.project_id, app.audit_id = app.store.save(new)
            app.display_report(new)
            gsc = {'property': 'sc-domain:example.com', 'start': '2026-09-01', 'end': '2026-09-28',
                   'rows': [{'keys': [url], 'clicks': 42, 'impressions': 1500}]}
            app.store.save_measurement(app.audit_id, 'search-console', gsc)
            plan = PlanWindow(app)
            assert plan.tasks and any(t.traffic and t.traffic['clicks'] == 42 for t in plan.tasks)
            assert 'Search Console' in plan.detail.get('1.0', 'end')
            screenshot(plan, 'traffic-plan.png')
            plan.win.destroy()
            diff = PageComparisonWindow(app, old, new, url)
            assert any(r['field'] == 'Titulek' and r['state'] == 'Změněno' for r in diff.rows)
            assert 'Starý titulek' in diff.values[0].get('1.0', 'end')
            assert 'Nový titulek' in diff.values[1].get('1.0', 'end')
            screenshot(diff, 'page-comparison.png')
            diff.win.destroy()
            app.store.save_measurement(first, 'pagespeed:mobile:' + url, {'url': url, 'strategy': 'mobile', 'score': 45,
                                       'created': '2026-10-01T12:00:00+02:00', 'version': '12', 'environment': {}})
            app.store.save_measurement(app.audit_id, 'pagespeed:mobile:' + url, {'url': url, 'strategy': 'mobile', 'score': 80,
                                       'created': '2026-10-24T12:00:00+02:00', 'version': '12', 'environment': {}})
            trends = TrendsWindow(app, project)
            root.update()
            assert len(trends.points) == 2 and trends.canvas.find_all()
            screenshot(trends, 'audit-trends.png')
            trends.metric.current(1)
            trends.refresh()
            assert all(p[0][0] is not None for p in trends.points)
            trends.metric.current(2)
            trends.refresh()
            assert [p[0][0] for p in trends.points] == [45, 80]
            assert trends.points[1][1]
            screenshot(trends, 'speed-trends.png')
            trends.win.destroy()
            history = HistoryWindow(app)
            history.open_trends()
            assert history.trends.win.winfo_exists()
            history.compare_page()
            assert history.page_comparison.win.winfo_exists()
            history.trends.win.destroy()
            history.page_comparison.win.destroy()
            history.win.destroy()
            app.show_diagnostic(RuntimeError('token=hidden-secret'))
            copy_diagnostic(root, app.last_diagnostic)
            assert 'hidden-secret' not in root.clipboard_get()
        finally:
            app.close()
    print('Evolution UI passed: persistent resume after close, traffic priorities, page comparison, three trend modes and safe diagnostics')


if __name__ == '__main__':
    run()
