"""Isolated Google setup and coverage UI; no live credentials or API requests."""
import threading
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

from seo_checker.app import Application
from seo_checker.dpi import enable_high_dpi
from seo_checker.engine import Page, Report
from seo_checker.google_services import ServiceError, Vault, pagespeed
from seo_checker.insights_ui import InsightsWindow
from seo_checker.workspace import HistoryWindow
from tests.insights_smoke import wait, screenshot
from tests.test_engine import temporary_directory
from tests.test_google import PSI
from tests.test_projects import report_with


def run():
    enable_high_dpi()
    with temporary_directory() as folder:
        root = tk.Tk()
        app = Application(root, database=Path(folder) / 'db.sqlite3')
        try:
            vault = Vault(Path(folder) / 'secrets.dat')
            win = InsightsWindow(app, vault)
            app.insights_window = win
            win.show_settings('speed')
            root.update()
            assert win.api_entry.winfo_ismapped()
            assert not win.has_audit()
            win.api_key.set('fixture-key')
            win.save_key()
            win.verify_url.set('https://site.test/')
            result = pagespeed(win.verify_url.get(), 'mobile', transport=lambda *a, **k: PSI)
            with patch('seo_checker.insights_ui.pagespeed', return_value=result) as measured:
                win.verify_speed()
                wait(root, win)
                measured.assert_called_once_with('https://site.test/', 'mobile', 'fixture-key')
            assert 'Měření funguje' in win.setup_steps['speed'].cget('text')
            assert not app.store.projects(), 'Setup must not create a phantom audit'
            assert '76 / 100' in win.speed_test_result.cget('text')
            win.verify_url.set('invalid')
            with patch('seo_checker.insights_ui.pagespeed') as measured:
                win.verify_speed()
                measured.assert_not_called()
            assert 'Měření funguje' in win.indicators['speed'][0].cget('text')
            win.verify_url.set('https://site.test/')
            win.api_key.set('not-yet-saved')
            with patch('seo_checker.insights_ui.pagespeed') as measured:
                win.verify_speed()
                measured.assert_not_called()
            assert 'Uložit klíč' in win.error_text.cget('text')
            win.api_key.set('fixture-key')
            vault.update(client={'client_id': 'fixture'}, tokens={'access_token': 'fixture'})
            win.show_settings('search')
            with patch('seo_checker.insights_ui.SearchConsole.sites', return_value=['sc-domain:site.test']):
                win.fetch_sites(stay=True)
                wait(root, win)
            assert win.tabs.index(win.tabs.select()) == 2
            assert 'API funguje' in win.setup_steps['search'].cget('text')
            win.setup_index['search'].set(3)
            win.select_setup_step()
            screenshot(win, 'setup-search.png')
            win.show_settings('speed')
            with patch('seo_checker.insights_ui.pagespeed', side_effect=ServiceError('Quota exceeded', 429)):
                win.verify_speed()
                wait(root, win)
            assert 'HTTP 429' in win.error_text.cget('text')
            assert 'nezdařilo' in win.setup_steps['speed'].cget('text')
            assert 'API funguje' in win.setup_steps['search'].cget('text')
            with patch('seo_checker.insights_ui.webbrowser.open', return_value=True) as opened:
                win.error_browser.invoke()
                assert 'site.test' in opened.call_args.args[0]
            with patch('seo_checker.insights_ui.pagespeed', return_value=result):
                win.verify_speed()
                wait(root, win)
            win.setup_index['speed'].set(3)
            win.select_setup_step()
            screenshot(win, 'setup-speed.png')
            win.win.geometry(f'{app.px(850)}x{app.px(640)}')
            root.update()
            screenshot(win, 'setup-small.png')
            release = threading.Event()
            with patch('seo_checker.insights_ui.pagespeed', side_effect=lambda *a: (release.wait(3), result)[1]):
                win.verify_speed()
                win.stop()
                release.set()
                wait(root, win)
            assert 'zastaven' in win.speed_test_result.cget('text')
            win.close()

            old = report_with('<h1>Test</h1>')
            app.project_id, first = app.store.save(old)
            new = Report(old.source, 'URL', pages=[Page('https://site.test/other')], complete=False, discovered=7)
            app.project_id, app.audit_id = app.store.save(new)
            history = HistoryWindow(app)
            root.update()
            assert history.scope['shared'] == 0
            assert 'liší' in history.scope_notice.cget('text')
            assert history.delta_counts['Odstraněné'].cget('text') == '0'
            history.filter_changes('Neověřené')
            assert history.change_rows and all(row[0] == 'Neověřené' for row in history.change_rows)
            root.update()
            history.show_scope()
            assert old.source in history.detail.get('1.0', 'end')
            screenshot(history, 'history-scope.png')
            history.win.geometry(f'{app.px(850)}x{app.px(640)}')
            root.update()
            screenshot(history, 'history-small.png')
            history.filter_changes('Odstraněné')
            assert not history.change_rows
            assert 'Žádné nálezy' in history.detail.get('1.0', 'end')
            history.audit_picker.current(next(i for i, row in enumerate(history.audit_rows) if row['id'] == first))
            history.select_audit()
            assert 'První kontrola' in history.summary.cget('text')
            history.win.destroy()
        finally:
            app.close()
    print('Setup/progress UI passed: isolated verification, validation, 429, retry, cancel, coverage and filters')


if __name__ == '__main__':
    run()
