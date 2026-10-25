"""Exercise page drilldown, summary, export choices and audit capture without user data."""
import json
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

from seo_checker.app import Application
from seo_checker.dpi import enable_high_dpi
from seo_checker.engine import analyze_html, Report
from tests.test_engine import temporary_directory
from tests.insights_smoke import screenshot


def run():
    enable_high_dpi()
    with temporary_directory() as folder:
        root = tk.Tk()
        app = Application(root, database=Path(folder) / 'test.sqlite3')
        try:
            page, _ = analyze_html('<title>Ukázkový web</title><h1>Služby pro váš web</h1><h2>SEO konzultace</h2><a href="/kontakt">Kontakt</a>', 'https://ukazkovy-web.test/')
            report = Report(page.location, 'URL', pages=[page], discovered=3, complete=False, notes=['Dosažen limit kontroly; dvě adresy nebyly zpracovány.'])
            app.project_id, app.audit_id = app.store.save(report)
            app.display_report(report)
            root.update()
            assert 'na 1 stránce' in app.subtitle.get()
            app.open_pages()
            root.update()
            detail = app.page_window
            assert 'Ukázkový web' in detail.fields['Přehled'].get('1.0', 'end')
            assert 'SEO konzultace' in detail.fields['Nadpisy'].get('1.0', 'end')
            assert len(detail.tree.get_children()) == len(page.findings)
            with patch('seo_checker.report_ui.webbrowser.open') as opened:
                detail.open_browser()
                opened.assert_called_once_with(page.location)
            screenshot(detail, 'page-0.6.png')
            detail.win.destroy()
            app.open_summary()
            root.update()
            assert 'Nezpracováno: 2' in app.summary_window.detail.get('1.0', 'end')
            screenshot(app.summary_window, 'summary-0.6.png')
            app.summary_window.win.destroy()
            app.export()
            export = app.export_window
            root.update()
            assert export.sections['summary'].get() and not export.sections['pages'].get()
            screenshot(export, 'export-0.6.png')
            export.preset.set('Pro vývojáře')
            export.apply_preset()
            assert export.sections['pages'].get() and not export.sections['measurements'].get()
            for variable in export.sections.values():
                variable.set(False)
            with patch('seo_checker.report_ui.filedialog.asksaveasfilename') as chooser:
                export.save()
                chooser.assert_not_called()
            export.apply_preset()
            export.format.current(1)
            # Switching the main audit while the export window is open cannot change its data.
            app.display_report(Report('https://other.test/', 'URL'))
            path = Path(folder) / 'export.json'
            with patch('seo_checker.report_ui.filedialog.asksaveasfilename', return_value=str(path)):
                export.save()
            data = json.loads(path.read_text(encoding='utf-8'))
            assert data['source'] == report.source and data['pages'][0]['headings']
            assert data['comparison_available'] is False
            assert 'measurements' not in data
            app.display_report(report)
            class Main:
                win = root
            screenshot(Main(), 'overview-0.6.png')
        finally:
            app.close()
    print('Report UI passed: page evidence, browser action, summary, presets, validation, selected export and captured audit')


if __name__ == '__main__':
    run()
