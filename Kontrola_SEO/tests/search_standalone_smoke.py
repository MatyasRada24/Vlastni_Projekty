"""Search Console can be used before opening an SEO audit."""
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

from seo_checker.app import Application
from seo_checker.dpi import enable_high_dpi
from seo_checker.google_services import Vault, ServiceError
from seo_checker.insights_ui import InsightsWindow
from tests.insights_smoke import wait, screenshot
from tests.test_engine import temporary_directory


def run():
    enable_high_dpi()
    with temporary_directory() as folder:
        root = tk.Tk()
        app = Application(root, database=Path(folder) / 'test.sqlite3')
        vault = Vault(Path(folder) / 'vault.dat')
        vault.update(client={'client_id': 'fixture.apps.googleusercontent.com'}, tokens={'access_token': 'fixture'})
        win = InsightsWindow(app, vault)
        app.insights_window = win
        try:
            assert app.report is None and app.audit_id is None
            with patch('seo_checker.insights_ui.SearchConsole.sites', return_value=['sc-domain:site.test']):
                win.fetch_sites()
                wait(root, win)
            data = {'property': 'sc-domain:site.test', 'start': '2025-01-01', 'end': '2025-01-28',
                    'rows': [{'keys': ['https://site.test/'], 'clicks': 3, 'impressions': 100, 'ctr': .03, 'position': 6}],
                    'created': '2025-02-01', 'page': None, 'truncated': False, 'note': 'Testovací data.'}
            win.start.set(data['start'])
            win.end.set(data['end'])
            with patch('seo_checker.insights_ui.SearchConsole.query', return_value=data) as query:
                win.search_empty_button.invoke()
                wait(root, win)
                query.assert_called_once()
            assert 'API funguje' in win.indicators['search'][0].cget('text')
            assert len(win.pages.get_children()) == 1
            assert win.pages.item('0', 'values')[-1] == '—'
            assert 'neukládají' in win.status.get()
            win.pages.selection_set('0')
            win.select_page()
            assert 'Samostatné zobrazení' in win.search_detail.get('1.0', 'end')
            with patch('seo_checker.insights_ui.SearchConsole.query', return_value=dict(data, page='https://site.test/', rows=[{'keys': ['dotaz']}])):
                win.fetch_queries()
                wait(root, win)
            assert len(win.queries.get_children()) == 1
            assert app.store.db.execute('SELECT COUNT(*) FROM measurements').fetchone()[0] == 0
            assert app.store.projects() == []
            # Local validation must not undo a successful API verification.
            verified = win.api_check
            win.start.set('bad date')
            with patch('seo_checker.insights_ui.SearchConsole.query') as query:
                win.fetch_search()
                query.assert_not_called()
            assert win.api_check == verified
            assert 'API funguje' in win.indicators['search'][0].cget('text')
            win.measure()  # PageSpeed still requires an audit, without blaming API.
            assert win.api_check == verified and win.speed_check is None
            win.start.set(data['start'])
            with patch('seo_checker.insights_ui.SearchConsole.query', side_effect=ServiceError('Odmítnuto', 403)):
                win.fetch_search()
                wait(root, win)
            assert 'nepodařilo ověřit' in win.indicators['search'][0].cget('text')
            with patch('seo_checker.insights_ui.SearchConsole.query', return_value=data):
                win.fetch_search()
                wait(root, win)
            assert not win.error_box.winfo_ismapped()
            assert 'API funguje' in win.indicators['search'][0].cget('text')
            screenshot(win, 'standalone-search-0.7.2.png')
        finally:
            app.close()
    print('Standalone Search Console passed: pages, queries, no false API failure on validation, no audit writes, API error and retry')


if __name__ == '__main__':
    run()
