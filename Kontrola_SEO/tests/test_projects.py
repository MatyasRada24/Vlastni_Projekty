import json
import unittest
from pathlib import Path

from seo_checker.engine import Page, Report, analyze_html
from seo_checker.export import save_report
from seo_checker.planning import build_plan, compare_reports, comparison_scope, issue_key, issues
from seo_checker.storage import Store
from tests.test_engine import GOOD, temporary_directory


def report_with(html, location="https://site.test/"):
    page, _ = analyze_html(html, location, online=True)
    return Report("https://site.test/", "URL", pages=[page], discovered=1)


class PlanningTests(unittest.TestCase):
    def test_coverage_compares_addresses_not_just_counts(self):
        old = report_with(GOOD)
        new = report_with(GOOD, 'https://site.test/other')
        scope = comparison_scope(old, new)
        self.assertEqual((scope['before'], scope['after'], scope['shared']), (1, 1, 0))
        self.assertEqual(scope['omitted'], ['https://site.test/'])
        self.assertEqual(scope['added'], ['https://site.test/other'])
        self.assertTrue(scope['warnings'])

    def test_scope_partial_and_changed_checks_or_rendering(self):
        old = report_with(GOOD)
        new = Report.from_dict(old.to_dict())
        self.assertFalse(comparison_scope(old, new)['warnings'])
        new.complete = False
        new.pages[0].analysis_mode = 'render_failed'
        new.pages[0].checked_rules.clear()
        self.assertEqual(len(comparison_scope(old, new)['warnings']), 3)
        self.assertIn('První kontrola', comparison_scope(None, new)['summary'])

    def test_grouping_priority_and_evidence(self):
        report = Report("https://site.test/", "URL")
        for path in ("/one", "/two", "/three"):
            page = Page("https://site.test" + path, inbound=["https://site.test/menu"])
            page.add("Chyba", "Nefunkční interní odkaz", "HTTP 404", "Opravte href.", "link.broken", "https://site.test/missing")
            page.add("Doporučení", "Meta description", "Chybí popis.")
            report.pages.append(page)
        tasks = build_plan(report)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].priority, 1)
        self.assertEqual(len(tasks[0].pages), 3)
        self.assertIn("šablonu", tasks[0].description())
        self.assertIn("/menu", tasks[0].description())

    def test_real_fix_vs_missing_page_or_failed_download(self):
        old = report_with("<h1>Test</h1>")
        new = report_with(GOOD)
        delta = compare_reports(old, new)
        self.assertIn("Titulek stránky", [f.name for p, f in delta["Odstraněné"]])
        self.assertTrue(delta["Přetrvávající"] == [])
        absent = Report(old.source, "URL", pages=[], complete=False)
        delta = compare_reports(old, absent)
        self.assertFalse(delta["Odstraněné"])
        self.assertTrue(delta["Neověřené"])
        failed = Report(old.source, "URL", pages=[Page(old.source)], complete=False)
        self.assertFalse(compare_reports(old, failed)["Odstraněné"])

    def test_new_vs_first_coverage_and_stable_detail(self):
        old = report_with(GOOD)
        new = report_with("<h1>New</h1>")
        self.assertIn("Titulek stránky", [f.name for p, f in compare_reports(old, new)["Nové"]])
        new.pages[0].location = "https://site.test/new"
        self.assertFalse(compare_reports(old, new)["Nové"])
        self.assertTrue(compare_reports(old, new)["Poprvé kontrolované"])
        changed = Report.from_dict(new.to_dict())
        changed.pages[0].findings[0].detail = "Stejný problém, jiný text"
        self.assertEqual(set(issues(changed)), set(issues(new)))

    def test_removed_link_and_canonical_provenance(self):
        old_page = Page("https://site.test/", html_checked=True, links=["https://site.test/bad"])
        old_page.add("Chyba", "Odkaz", "404", code="link.broken", target=old_page.links[0])
        old = Report(old_page.location, "URL", pages=[old_page])
        new_page = Page(old_page.location, html_checked=True)
        new = Report(old.source, "URL", pages=[new_page], complete=False)
        self.assertEqual(len(compare_reports(old, new)["Odstraněné"]), 1)
        new_page.links = old_page.links
        self.assertFalse(compare_reports(old, new)["Odstraněné"])


class StorageTests(unittest.TestCase):
    def test_disk_reopen_history_isolation_and_manual_states(self):
        with temporary_directory() as folder:
            path = Path(folder) / "history.sqlite3"
            old = report_with("<h1>Test</h1>")
            store = Store(path)
            project, first = store.save(old)
            original = json.dumps(store.load(first)[1].to_dict(), ensure_ascii=False)
            keys = list(issues(old))
            store.set_states(project, first, [keys[0]], "Vyřešené")
            store.set_states(project, first, [keys[1]], "Záměrné")
            project2, second = store.save(old)
            self.assertEqual(project, project2)
            self.assertEqual(store.states(project)[keys[0]], "Otevřené")
            self.assertEqual(store.states(project)[keys[1]], "Záměrné")
            self.assertEqual(json.dumps(store.load(first)[1].to_dict(), ensure_ascii=False), original)
            self.assertEqual(store.previous(second).to_dict(), old.to_dict())
            self.assertIsNone(store.previous(first))
            store.rename(project, "Můj obchod")
            store.close()
            store = Store(path)
            self.assertEqual(store.projects()[0]["name"], "Můj obchod")
            self.assertEqual(len(store.audits(project)), 2)
            another = report_with("<h1>Test</h1>", "https://other.test/")
            another.source = "https://other.test/"
            other_project, other_audit = store.save(another)
            self.assertNotEqual(project, other_project)
            with self.assertRaises(ValueError):
                store.set_states(project, other_audit, list(issues(another)), "Záměrné")
            with self.assertRaises(ValueError):
                store.set_states(project, first, ["unknown-key"], "Vyřešené")
            store.close()

    def test_export_contains_plan_comparison_and_escaped_evidence(self):
        with temporary_directory() as folder:
            old = report_with("<h1>Test</h1>")
            new = report_with(GOOD)
            new.pages[0].inbound = ['<script>alert(1)</script>']
            target = Path(folder) / "report.html"
            comparison = compare_reports(old, new)
            save_report(new, str(target), comparison=comparison)
            html = target.read_text(encoding="utf-8")
            self.assertIn("Plán oprav", html)
            self.assertIn("Odstraněné", html)
            self.assertNotIn("<script>", html)
            target = target.with_suffix(".json")
            save_report(new, str(target), comparison=comparison)
            data = json.loads(target.read_text(encoding="utf-8"))
            self.assertTrue(data["comparison"]["Odstraněné"])
            self.assertIn("repair_plan", data)
