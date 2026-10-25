"""User workflows and visual previews for the compact 0.5 desktop layout."""
import os
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

from seo_checker.app import Application
from seo_checker.dpi import enable_high_dpi
from seo_checker.engine import Page, Report
from seo_checker.google_services import Vault
from seo_checker.insights_ui import InsightsWindow
from seo_checker.workspace import PlanWindow, HistoryWindow
from tests.test_engine import temporary_directory
from tests.insights_smoke import screenshot


def example():
    report = Report('https://ukazkovy-web.test/', 'URL', discovered=9)
    for index, path in enumerate(('', 'sluzby/', 'kontakt/', 'blog/', 'blog/navod/', 'o-nas/', 'cenik/', 'reference/', 'podpora/')):
        page = Page(report.source + path, title='Ukázkový web', html_checked=True)
        page.add('Správně', 'HTTP odpověď', 'Stránka je dostupná. HTTP 200.')
        page.add('Doporučení', 'Meta description', 'Chybí popis stránky.', 'Napište krátké shrnutí obsahu, které pomůže lidem rozhodnout se, zda stránku otevřít.')
        if index < 3:
            page.add('Doporučení', 'Prázdné alternativní texty', 'Obrázek nemá textový popis.', 'Doplňte popis významu obrázku. Dekorativní obrázky mohou mít prázdný alt.')
        if index == 0:
            page.add('Chyba', 'Cíl canonical', 'https://ukazkovy-web.test/archiv/: HTTP 200, HTML=True, noindex=True.', 'Nasměrujte canonical na dostupnou indexovatelnou stránku.', code='canonical.target')
        page.add('Neověřeno', 'Externí canonical', 'Externí stránka není součástí kontroly.')
        report.pages.append(page)
    return report


def run():
    enable_high_dpi()
    with temporary_directory() as folder:
        root = tk.Tk()
        app = Application(root, database=Path(folder) / 'db.sqlite3')
        try:
            root.geometry('1600x960+0+0')
            root.update()
            assert not app.inspector.winfo_ismapped()
            report = example()
            app.store.save(report)
            app.project_id, app.audit_id = app.store.save(report)
            app.url.set(report.source)
            app.display_report(report)
            root.update()
            total = len(app.rows)
            assert app.inspector.winfo_ismapped()
            assert app.tree.item('0', 'values')[2] == '/'
            with patch('seo_checker.app.webbrowser.open', return_value=True) as opened:
                app.open_selected_page()
                opened.assert_called_once_with(report.source)
            app.copy_page()
            assert root.clipboard_get() == report.source
            app.inspector.grid_remove()
            app.show_detail()
            root.update()
            assert app.inspector.winfo_ismapped()
            assert app.scope_button.winfo_rooty() + app.scope_button.winfo_height() <= app.workspace.winfo_rooty()
            assert app.tree.winfo_height() >= app.px(34 * 6), 'Too little space for results'
            app.quick_filter('Chyba')
            assert len(app.rows) == 1
            app.quick_filter('Chyba')
            assert len(app.rows) == total
            app.search.set('kontakt')
            app.refresh()
            assert app.rows and all('/kontakt/' in p.location for p, f in app.rows.values())
            app.search.set('this-will-match-nothing')
            app.refresh()
            assert not app.rows and app.copy_button.instate(['disabled'])
            app.reset_filters()
            assert len(app.rows) == total
            class Main:
                win = root
            screenshot(Main(), 'overview-0.5.png')
            app.search.set('Meta description')
            app.refresh()
            root.update()
            assert '<meta name="description"' in app.detail.get('1.0', 'end')
            screenshot(Main(), 'overview-meta-0.7.png')
            root.geometry(f'{app.px(1060)}x{app.px(700)}')
            root.update()
            assert app.search_entry.winfo_width() >= app.px(90)
            for control in (app.render_check, app.reset_button, app.filter_input, app.page_input):
                assert control.winfo_width() >= control.winfo_reqwidth(), 'Compact controls must remain readable'
            assert sum(app.tree.column(column, 'width') for column in ('#0', 'status', 'check', 'page')) <= app.tree.winfo_width(), 'All result columns must fit'
            assert app.open_page_button.winfo_rootx() + app.open_page_button.winfo_width() <= app.copy_button.winfo_rootx()
            screenshot(Main(), 'overview-compact-0.7.png')
            root.geometry('1600x960')
            app.reset_filters()
            plan = PlanWindow(app)
            root.update()
            # A group's individual occurrence updates both evidence and saved state.
            index = next(i for i, task in enumerate(plan.tasks) if task.name == 'Meta description')
            plan.tree.selection_set(str(index))
            plan.select()
            plan.occurrence.current(2)
            plan.select_occurrence()
            assert 'sluzby/' in plan.detail.get('1.0', 'end')
            plan.state.set('Záměrné')
            plan.save()
            assert list(app.store.states(app.project_id).values()).count('Záměrné') == 1
            plan.tree.selection_set('0')
            plan.select()
            screenshot(plan, 'plan-0.5.png')
            plan.win.destroy()
            history = HistoryWindow(app)
            root.update()
            assert history.open_button.instate(['!disabled'])
            screenshot(history, 'history-0.5.png')
            history.win.destroy()
            insights = InsightsWindow(app, Vault(Path(folder) / 'vault.dat'))
            app.insights_window = insights
            root.update()
            assert insights.speed_empty.winfo_ismapped()
            screenshot(insights, 'speed-empty-0.5.png')
            insights.tabs.select(1)
            root.update()
            assert insights.search_empty.winfo_ismapped()
            screenshot(insights, 'search-empty-0.5.png')
            insights.win.event_generate('<<BackToOverview>>')
            root.update()
            assert insights.closed and not insights.win.winfo_exists()
        finally:
            app.close()
    print('Redesign passed: usable table, quick filters, search/reset, scoped task state, detail, history and empty-state navigation')


if __name__ == '__main__':
    run()
