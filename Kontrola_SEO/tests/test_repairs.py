import json
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from seo_checker.crawler import Crawler, crawl_selected
from seo_checker.engine import Page, Report, audit_local
from seo_checker.planning import build_plan, issue_key
from seo_checker.repairs import repair_example, repair_instructions, verify_repairs
from seo_checker.storage import Store
from tests.test_engine import GOOD, temporary_directory
from tests.test_projects import report_with


class RepairTests(unittest.TestCase):
    def test_guidance_specific_and_escapes_headings(self):
        report = report_with('<h1>A &amp; B &lt;script&gt;</h1>')
        task = next(task for task in build_plan(report) if task.code == 'Titulek stránky')
        self.assertIn('Titulek', task.reason)
        self.assertIn('Proč priorita P2', repair_instructions(task, report.pages[0]))
        self.assertEqual(repair_example(task.code, report.pages[0]), '<title>A &amp; B &lt;script&gt;</title>')
        self.assertIn('dekorativní', repair_example('Prázdné alternativní texty').lower())

    def test_local_only_selected_and_original_history_unchanged(self):
        with temporary_directory() as folder:
            first, other = Path(folder)/'a.html', Path(folder)/'b.html'
            first.write_text('<h1>Test</h1>', encoding='utf-8')
            other.write_text('<h1>Other</h1>', encoding='utf-8')
            before = audit_local(folder)
            task = next(task for task in build_plan(before) if task.code == 'Titulek stránky')
            selected = [occurrence for occurrence in task.occurrences if occurrence[0].location == str(first)]
            first.write_text(GOOD, encoding='utf-8')
            with patch('seo_checker.engine.analyze_html', wraps=__import__('seo_checker.engine', fromlist=['analyze_html']).analyze_html) as analyzed:
                result = verify_repairs(before, selected)
            self.assertEqual(analyzed.call_count, 1)
            self.assertEqual(result['requested'], [str(first)])
            self.assertEqual(result['results'][0]['status'], 'Opraveno')
            store = Store(Path(folder)/'db.sqlite3')
            project, audit = store.save(before)
            original = store.load(audit)[1].to_dict()
            key = issue_key(*selected[0])
            store.set_states(project, audit, [key], 'Záměrné')
            store.save_repair_check(audit, result)
            self.assertEqual(store.load(audit)[1].to_dict(), original)
            self.assertEqual(len(store.audits(project)), 1)
            self.assertEqual(store.states(project)[key], 'Záměrné')
            store.close()
            store = Store(Path(folder)/'db.sqlite3')
            self.assertEqual(store.repair_checks(audit)[key]['status'], 'Opraveno')
            first.write_text('<h1>Still broken</h1>', encoding='utf-8')
            retry = verify_repairs(before, selected)
            store.save_repair_check(audit, retry)
            self.assertEqual(store.repair_checks(audit)[key]['status'], 'Přetrvává')
            store.close()

    def test_missing_local_file_and_zip_entry_not_fixed(self):
        with temporary_directory() as folder:
            file = Path(folder)/'a.html'
            file.write_text('<h1>Test</h1>', encoding='utf-8')
            before = audit_local(folder)
            task = next(task for task in build_plan(before) if task.code == 'Titulek stránky')
            file.unlink()
            result = verify_repairs(before, task.occurrences)
            self.assertEqual(result['results'][0]['status'], 'Neověřeno')
            archive = Path(folder)/'site.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('a.html', '<h1>Test</h1>')
            before = audit_local(str(archive))
            task = next(task for task in build_plan(before) if task.code == 'Titulek stránky')
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('b.html', GOOD)
            self.assertEqual(verify_repairs(before, task.occurrences)['results'][0]['status'], 'Neověřeno')

    def test_duplicates_render_failure_and_cancel_are_not_fixes(self):
        before = report_with('<title>Duplicate</title><h1>Test</h1>')
        page = before.pages[0]
        page.add('Doporučení', 'Duplicitní titulek', 'Two pages')
        occurrence = [(page, page.findings[-1])]
        after = report_with(GOOD)
        after.complete = False
        with patch('seo_checker.crawler.crawl_selected', return_value=after):
            self.assertEqual(verify_repairs(before, occurrence)['results'][0]['status'], 'Neověřeno')
        before = report_with('<h1>Test</h1>')
        before.rendering = True
        before.pages[0].analysis_mode = 'rendered'
        task = next(task for task in build_plan(before) if task.code == 'Titulek stránky')
        after.pages[0].analysis_mode = 'render_failed'
        with patch('seo_checker.crawler.crawl_selected', return_value=after) as crawl:
            self.assertEqual(verify_repairs(before, task.occurrences)['results'][0]['status'], 'Neověřeno')
            self.assertTrue(crawl.call_args.kwargs['rendering'])
        cancel = threading.Event()
        cancel.set()
        after.pages[0].analysis_mode = 'rendered'
        with patch('seo_checker.crawler.crawl_selected', return_value=after):
            self.assertEqual(verify_repairs(before, task.occurrences, cancel)['results'][0]['status'], 'Neověřeno')

    def test_invalid_target_never_requested(self):
        crawler = Crawler('https://site.test/', 2, None, None)
        with patch.object(crawler, 'request') as request:
            with self.assertRaises(ValueError):
                crawler.run_selected(['https://other.test/'])
            with self.assertRaises(ValueError):
                crawler.run_selected(['https://site.test/a', 'https://site.test/b', 'https://site.test/c'])
            request.assert_not_called()
