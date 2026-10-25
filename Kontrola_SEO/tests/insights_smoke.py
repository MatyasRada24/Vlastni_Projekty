"""Exercise new UI with deterministic API fixtures, save and reopen snapshots."""
import os
import threading
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

from seo_checker.app import Application
from seo_checker.dpi import enable_high_dpi
from seo_checker.engine import Report, analyze_html
from seo_checker.google_services import Vault, pagespeed
from seo_checker.insights_ui import InsightsWindow
from tests.test_engine import temporary_directory
from tests.test_google import PSI


def wait(root, win):
    deadline = time.monotonic() + 5
    while win.busy and time.monotonic() < deadline:
        root.update()
        time.sleep(.01)
    root.update()
    assert not win.busy, 'Service job did not finish'


def screenshot(win, name):
    folder = os.environ.get('SEO_PREVIEW_DIR')
    if not folder:
        return
    import ctypes
    from PIL import ImageGrab
    win.win.geometry('+20+20')
    win.win.update()
    win.win.after(180, win.win.quit)
    win.win.mainloop()
    api = ctypes.windll.user32
    api.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    api.GetAncestor.restype = ctypes.c_void_p
    Path(folder).mkdir(parents=True, exist_ok=True)
    ImageGrab.grab(window=api.GetAncestor(win.win.winfo_id(), 2)).save(str(Path(folder) / name))


def run():
    enable_high_dpi()
    with temporary_directory() as folder:
        root = tk.Tk()
        app = Application(root, database=Path(folder) / 'projects.sqlite3')
        page, _ = analyze_html('<h1>Test</h1>', 'https://site.test/', online=True)
        report = Report(page.location, 'URL', pages=[page], discovered=1)
        app.project_id, app.audit_id = app.store.save(report)
        app.display_report(report)
        vault = Vault(Path(folder) / 'secrets.dat')
        win = InsightsWindow(app, vault)
        app.insights_window = win
        assert 'Nejste přihlášen' in win.indicators['account'][0].cget('text')
        win.api_key.set('example-secret')
        win.save_key()
        speed = pagespeed(report.source, 'mobile', transport=lambda *a, **k: PSI)
        with patch('seo_checker.insights_ui.pagespeed', return_value=speed):
            win.measure()
            wait(root, win)
        assert '76 / 100' in win.speed_values['score'].cget('text')
        assert 'Měření funguje' in win.indicators['speed'][0].cget('text')
        assert 'Hotovo' in win.activity.cget('text')
        assert 'Data skutečných návštěvníků' in win.speed_detail.get('1.0', 'end')
        screenshot(win, 'speed-0.4.png')
        data = {'property': 'sc-domain:site.test', 'start': '2025-01-01', 'end': '2025-01-28', 'page': None,
                'rows': [{'keys': [page.location], 'clicks': 4, 'impressions': 900, 'ctr': 4/900, 'position': 7.4}],
                'truncated': False, 'created': '2025-02-01', 'note': 'Testovací data API, nikoli živá data webu.'}
        vault.update(client={'client_id': 'test.apps.googleusercontent.com'}, tokens={'access_token': 'fixture-token'})
        win.property.set(data['property'])
        win.start.set(data['start'])
        win.end.set(data['end'])
        with patch('seo_checker.insights_ui.SearchConsole.query', return_value=data):
            win.fetch_search()
            wait(root, win)
        assert len(win.pages.get_children()) == 1
        assert 'Přihlášen' in win.indicators['account'][0].cget('text')
        assert 'API funguje' in win.indicators['search'][0].cget('text')
        win.pages.selection_set('0')
        win.select_page()
        assert 'Titulek stránky' in win.search_detail.get('1.0', 'end')
        queries = dict(data, page=page.location, rows=[{'keys': ['ukázkový dotaz'], 'clicks': 4, 'impressions': 900, 'ctr': 4/900, 'position': 7.4}])
        with patch('seo_checker.insights_ui.SearchConsole.query', return_value=queries):
            win.fetch_queries()
            wait(root, win)
        assert len(win.queries.get_children()) == 1
        win.tabs.select(1)
        screenshot(win, 'search-console-0.4.png')
        win.tabs.select(2)
        screenshot(win, 'google-settings-0.4.png')
        saved = app.store.measurements(app.audit_id)
        assert len(saved) == 3
        assert 'example-secret' not in str(saved)
        # A canceled API response must not become a saved successful measurement.
        release = threading.Event()
        win.run('speed', lambda: (release.wait(3), speed)[1])
        assert 'Měřím rychlost' in win.activity.cget('text')
        win.operation_started -= 3
        deadline = time.monotonic() + .6
        while time.monotonic() < deadline:
            root.update()
            time.sleep(.02)
        assert '3 s' in win.activity.cget('text')
        win.stop()
        release.set()
        wait(root, win)
        assert app.store.measurements(app.audit_id) == saved
        assert 'zastavena' in win.activity.cget('text')
        win.close()
        reopened = InsightsWindow(app, vault)
        app.insights_window = reopened
        assert len(reopened.pages.get_children()) == 1
        assert '76 / 100' in reopened.speed_values['score'].cget('text')
        assert 'Přihlášení uložené' in reopened.indicators['account'][0].cget('text')
        assert 'Přístup neověřen' in reopened.indicators['search'][0].cget('text')
        assert 'Uložené měření' in reopened.indicators['speed'][0].cget('text')
        with patch('seo_checker.insights_ui.SearchConsole.sites', return_value=['sc-domain:site.test']):
            reopened.fetch_sites()
            wait(root, reopened)
        assert 'API funguje' in reopened.indicators['search'][0].cget('text')
        reopened.tabs.select(2)
        screenshot(reopened, 'service-indicators-0.7.1.png')
        reopened.disconnect()
        assert 'Nejste přihlášen' in reopened.indicators['account'][0].cget('text')
        assert 'Přístup neověřen' in reopened.indicators['search'][0].cget('text')
        app.close()
    print('Insights UI passed: measurement, page/query matching, encrypted key, cancel, immutable snapshots and reopen')


if __name__ == '__main__':
    run()
