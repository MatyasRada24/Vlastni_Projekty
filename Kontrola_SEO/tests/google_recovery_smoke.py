"""Recovery from quota limits and missing Google setup, without user credentials."""
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from seo_checker.app import Application
from seo_checker.dpi import enable_high_dpi
from seo_checker.engine import Report, analyze_html
from seo_checker.google_services import Vault, ServiceError, pagespeed
from seo_checker.insights_ui import InsightsWindow
from tests.insights_smoke import wait, screenshot
from tests.test_engine import temporary_directory
from tests.test_google import PSI


def run():
    enable_high_dpi()
    with temporary_directory() as folder:
        root = tk.Tk()
        app = Application(root, database=Path(folder) / 'db.sqlite3')
        try:
            page, _ = analyze_html('<h1>Test</h1>', 'https://site.test/?a=one&b=two')
            report = Report(page.location, 'URL', pages=[page], discovered=1)
            app.project_id, app.audit_id = app.store.save(report)
            app.display_report(report)
            vault = Vault(Path(folder) / 'test-vault.dat')
            win = InsightsWindow(app, vault)
            app.insights_window = win
            root.update()
            assert 'není nastaven' in win.key_status.cget('text')
            with patch('seo_checker.insights_ui.pagespeed', side_effect=ServiceError('Quota exceeded', 429)):
                win.measure()
                wait(root, win)
            assert win.error_box.winfo_ismapped()
            assert 'HTTP 429' in win.error_text.cget('text')
            assert 'nezdařilo' in win.indicators['speed'][0].cget('text')
            assert 'nezdařila' in win.activity.cget('text')
            assert not win.loading.winfo_ismapped()
            assert not app.store.measurements(app.audit_id)
            screenshot(win, 'pagespeed-quota-0.6.1.png')
            with patch('seo_checker.insights_ui.webbrowser.open', return_value=True) as opened:
                win.error_browser.invoke()
                destination = opened.call_args.args[0]
                assert urlsplit(destination).netloc == 'pagespeed.web.dev'
                assert parse_qs(urlsplit(destination).query)['url'] == [page.location]
                assert 'neukládá' in win.status.get()
            win.error_settings.invoke()
            root.update()
            assert win.tabs.index(win.tabs.select()) == 2
            assert win.api_entry.winfo_ismapped()
            win.error_box.grid_remove()
            win.tabs.select(1)
            with patch('seo_checker.insights_ui.SearchConsole.query') as queried:
                win.fetch_search()
                queried.assert_not_called()
            root.update()
            assert 'OAuth JSON' in win.error_text.cget('text')
            assert win.error_box.winfo_ismapped()
            screenshot(win, 'search-setup-0.6.1.png')
            # Stored credentials must offer a way to load sites after reopening.
            vault.update(client={'client_id': 'test.apps.googleusercontent.com'}, tokens={'access_token': 'fixture'})
            win.refresh_connection()
            assert win.search_empty_button.cget('text') == 'Načíst weby'
            with patch('seo_checker.insights_ui.SearchConsole.sites', side_effect=ServiceError('Google Search Console API není zapnuté.', 403, 'service_disabled')):
                win.fetch_sites()
                wait(root, win)
            assert 'není zapnuté' in win.connection.cget('text')
            assert 'nepodařilo ověřit' in win.indicators['search'][0].cget('text')
            assert 'Zapnout Search Console API' in win.error_settings.cget('text')
            assert vault.read()['tokens']['access_token'] == 'fixture'
            with patch('seo_checker.insights_ui.webbrowser.open', return_value=True) as opened:
                win.error_settings.invoke()
                assert opened.call_args.args[0] == 'https://console.cloud.google.com/apis/library/searchconsole.googleapis.com'
            screenshot(win, 'search-disabled-api-0.6.2.png')
            with patch('seo_checker.insights_ui.SearchConsole.sites', return_value=[]):
                win.fetch_sites()
                wait(root, win)
            assert 'nemá dostupný web' in win.error_text.cget('text')
            with patch('seo_checker.insights_ui.SearchConsole.sites', return_value=['sc-domain:site.test']):
                win.fetch_search()  # Empty property automatically loads sites.
                wait(root, win)
            assert win.property.get() == 'sc-domain:site.test'
            assert 'Přístup k Search Console ověřen' in win.connection.cget('text')
            assert not win.error_box.winfo_ismapped()
            win.api_key.set('fixture-key')
            win.save_key()
            assert 'Klíč uložen' in win.key_status.cget('text')
            win.tabs.select(0)
            result = pagespeed(page.location, 'mobile', transport=lambda *a, **k: PSI)
            with patch('seo_checker.insights_ui.pagespeed', return_value=result):
                win.measure()
                wait(root, win)
            assert '76 / 100' in win.speed_values['score'].cget('text')
            assert not win.error_box.winfo_ismapped()
            assert len(app.store.measurements(app.audit_id)) == 1
            assert 'fixture-key' not in str(app.store.measurements(app.audit_id))
        finally:
            app.close()
    print('Google recovery passed: visible 429, browser fallback, setup routing, missing account, no sites, reload sites, retry and save')


if __name__ == '__main__':
    run()
