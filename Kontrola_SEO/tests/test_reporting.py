import json
import unittest
from pathlib import Path

from seo_checker.engine import Page, Report, analyze_html
from seo_checker.export import save_report, PRESETS
from seo_checker.reporting import audit_summary, page_sections, indexability, browser_url
from seo_checker.storage import Store
from tests.test_engine import temporary_directory


class ReportingTests(unittest.TestCase):
    def test_page_evidence_roundtrip_and_legacy_missing(self):
        page, _ = analyze_html('<title>Titulek</title><meta name="description" content="Popis"><h1>Hlavní <em>nadpis</em></h1><h2>Druhý</h2><a href="/cil">Cíl</a><a href="https://external.test/">Ven</a><link rel="canonical" href="/preferovana">', 'https://site.test/')
        report = Report(page.location, 'URL', pages=[page], discovered=1)
        store = Store(':memory:')
        try:
            project, audit = store.save(report)
            self.assertEqual(store.load(audit)[1].to_dict(), report.to_dict())
            restored = store.load(audit)[1].pages[0]
            self.assertEqual(restored.headings, [[1, 'Hlavní nadpis'], [2, 'Druhý']])
            self.assertEqual(restored.source_links, ['/cil', 'https://external.test/'])
            self.assertIn('/preferovana', page_sections(restored, 'URL')['Přehled'])
            legacy = report.to_dict()
            for key in ('headings', 'source_links', 'declared_canonicals'):
                legacy['pages'][0].pop(key)
            old = Report.from_dict(legacy).pages[0]
            self.assertIn('nebyl uložen', page_sections(old, 'URL')['Nadpisy'])
            self.assertIn('nebyl uložen', page_sections(old, 'URL')['Odkazy'])
        finally:
            store.close()

    def test_counts_distinguish_findings_pages_and_coverage(self):
        first = Page('https://site.test/', html_checked=True)
        first.add('Chyba', 'Titulek', 'Chybí', 'Doplňte')
        first.add('Doporučení', 'Popis', 'Chybí', 'Doplňte')
        first.add('Správně', 'Jazyk', 'cs')
        failed = Page('https://site.test/fail')
        failed.add('Neověřeno', 'Stažení stránky', 'Timeout')
        report = Report(first.location, 'URL', pages=[first, failed], discovered=5, complete=False)
        summary = audit_summary(report)
        self.assertEqual((summary['problems'], summary['affected_pages']), (2, 1))
        self.assertEqual((summary['visited'], summary['html_checked'], summary['not_visited']), (2, 1, 3))
        self.assertEqual(summary['uncertain_reasons'], {'Stažení stránky': 1})
        self.assertEqual(summary['scope'], 'Částečná kontrola')
        self.assertLessEqual(len(summary['next_steps']), 3)

    def test_unknown_and_blocked_are_not_positive_indexability(self):
        page = Page('https://site.test/')
        self.assertIn('Nelze posoudit', indexability(page, 'URL'))
        page.html_checked = True
        self.assertIn('neověřený', indexability(page, 'URL'))
        page.noindex = True
        self.assertIn('zákaz', indexability(page, 'URL'))
        page.noindex = False
        self.assertIn('serveru', indexability(page, 'Soubory'))

    def test_browser_only_http_urls_without_credentials(self):
        for url in ['javascript:alert(1)', 'file:///C:/test.exe', 'https://user:pass@site.test/', 'https://[bad']:
            self.assertFalse(browser_url(url))
        self.assertTrue(browser_url('https://site.test/page'))

    def test_export_selected_sections_and_html_escape(self):
        page, _ = analyze_html('<h1>Stránka</h1>', 'https://site.test/')
        page.headings.append((2, '<script>alert(1)</script>'))
        page.source_links = ['javascript:alert(1)']
        report = Report(page.location, 'URL', pages=[page], discovered=2, complete=False, notes=['Limit kontrolovaného vzorku.'])
        measurements = [{'kind': 'search-console', 'saved': '2026-10-21', 'data': {'secret_query': 'NEVEREJNY_DOTAZ'}}]
        with temporary_directory() as folder:
            for extension in ('.html', '.json'):
                path = Path(folder) / ('client'+extension)
                save_report(report, path, sections=PRESETS['Pro klienta'], measurements=measurements)
                data = path.read_text(encoding='utf-8')
                self.assertNotIn('NEVEREJNY_DOTAZ', data)
                self.assertNotIn('alert(1)', data)
                self.assertIn('Limit kontrolovaného vzorku.', data)
                if extension == '.json':
                    payload = json.loads(data)
                    self.assertNotIn('pages', payload)
                    self.assertFalse(payload['comparison_available'])
            path = Path(folder) / 'developer.html'
            save_report(report, path, sections=PRESETS['Pro vývojáře'], title='<img src=x onerror=alert(1)>')
            data = path.read_text(encoding='utf-8')
            self.assertNotIn('<script>', data)
            self.assertNotIn('<img', data)
            self.assertIn('&lt;script&gt;', data)
            self.assertIn('Všechny nálezy stránky', data)
            path = Path(folder) / 'data.json'
            save_report(report, path, sections={'pages'}, measurements=measurements)
            payload = json.loads(path.read_text(encoding='utf-8'))
            self.assertIn('pages', payload)
            for key in ('summary', 'repair_plan', 'comparison', 'measurements'):
                self.assertNotIn(key, payload)
            self.assertEqual(payload['scope_summary']['not_visited'], 1)
            with self.assertRaises(ValueError):
                save_report(report, path, sections=set())

    def test_empty_and_truncated_evidence(self):
        page, _ = analyze_html('<html lang="cs"></html>', 'local.html')
        self.assertIn('nejsou nadpisy', page_sections(page, 'Soubory')['Nadpisy'])
        page.source_links_complete = False
        self.assertIn('10 000', page_sections(page, 'Soubory')['Odkazy'])
        self.assertEqual(audit_summary(Report('empty', 'Soubory'))['problems'], 0)


if __name__ == '__main__':
    unittest.main()
