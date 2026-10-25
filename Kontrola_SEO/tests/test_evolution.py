import copy
import json
import threading
import unittest
import zipfile
from pathlib import Path
from http.server import ThreadingHTTPServer

from seo_checker.diagnostics import diagnose
from seo_checker.engine import Page, Report, audit_local, audit_url
from seo_checker.evolution import page_changes, traffic_evidence, traffic_text, trend_rows
from seo_checker.google_services import ServiceError
from seo_checker.planning import build_plan, issue_key
from seo_checker.storage import Store
from tests.test_crawler import DeepServer
from tests.test_engine import temporary_directory


class EvolutionTests(unittest.TestCase):
    def test_traffic_orders_within_technical_priority_without_double_counting(self):
        a = Page('https://example.com/a', canonical='https://example.com/preferred')
        a.add('Doporučení', 'Popis', 'x')
        a.add('Doporučení', 'Popis', 'x', target='other')
        b = Page('https://example.com/b')
        b.add('Doporučení', 'Alt', 'x')
        critical = Page('https://example.com/c')
        critical.add('Chyba', 'HTTP odpověď', '404')
        report = Report('https://example.com/', 'URL', pages=[b, a, critical])
        snapshot = {'property': 'sc-domain:example.com', 'start': '2026-09-01', 'end': '2026-09-28',
                    'rows': [{'keys': [a.canonical], 'clicks': 150, 'impressions': 1000},
                             {'keys': [a.canonical], 'clicks': 150, 'impressions': 1000},
                             {'keys': [b.location], 'clicks': 2, 'impressions': 2000}]}
        plan = build_plan(report, search=snapshot)
        self.assertEqual([t.name for t in plan], ['HTTP odpověď', 'Popis', 'Alt'])
        self.assertEqual(plan[1].traffic['clicks'], 150)
        self.assertEqual(plan[1].traffic['matched'], 1)
        self.assertEqual(plan[0].traffic['matched'], 0)
        self.assertIn('neznamenají nulovou', traffic_text(plan[0].traffic))
        self.assertIsNone(traffic_evidence(report, [a], dict(snapshot, property='sc-domain:other.test')))
        self.assertIsNone(traffic_evidence(report, [a], None))
        self.assertEqual(report.pages[1].findings[0].status, 'Doporučení')

    def test_page_comparison_unknown_is_not_empty_or_fixed(self):
        old = Page('https://example.com/a', title='Před', description='', headings=None, html_checked=True)
        new = Page(old.location, title='Po', description='', headings=[(1, 'Nový H1')], html_checked=True, noindex=True)
        new.add('Doporučení', 'Pokyny k indexaci', 'noindex')
        a, b = Report(old.location, 'URL', pages=[old]), Report(old.location, 'URL', pages=[new])
        rows = {r['field']: r for r in page_changes(a, b, old.location)}
        self.assertEqual(rows['Titulek']['state'], 'Změněno')
        self.assertEqual(rows['Meta popis']['state'], 'Beze změny')
        self.assertEqual(rows['H1']['state'], 'Neověřeno')
        self.assertEqual(rows['Pokyny k indexaci']['state'], 'Neověřeno')
        new.analysis_mode = 'rendered'
        self.assertTrue(all(r['state'] == 'Neověřeno' for r in page_changes(a, b, old.location)))
        self.assertTrue(all(r['state'] == 'Neověřeno' for r in page_changes(None, b, old.location)))

    def test_historical_states_and_scope_are_not_rewritten(self):
        store = Store(':memory:')
        try:
            page = Page('https://example.com/a')
            page.add('Chyba', 'Titulek stránky', 'Chybí')
            report = Report(page.location, 'URL', pages=[page])
            project, first = store.save(report)
            _, second = store.save(report)
            store.set_states(project, second, [issue_key(page, page.findings[0])], 'Vyřešené')
            rows = trend_rows(store, project)
            self.assertEqual([r['open'] for r in rows], [1, 0])
            self.assertTrue(rows[1]['comparable'])
            partial = Report(report.source, 'URL', pages=[], complete=False)
            store.save(partial)
            self.assertFalse(trend_rows(store, project)[-1]['comparable'])
            store.db.execute('DELETE FROM audit_work_states WHERE audit_id=?', (first,))
            self.assertIsNone(trend_rows(store, project)[0]['open'])
        finally:
            store.close()

    def test_diagnostic_copy_uses_only_controlled_metadata(self):
        secret = 'api_key=secret-token https://example.com/?password=hello C:/private/client.json'
        for error in [RuntimeError(secret), ValueError(secret), ServiceError(secret, 403, secret)]:
            detail = diagnose(error, secret)['technical']
            for value in ('secret-token', 'password=hello', 'client.json', 'example.com'):
                self.assertNotIn(value, detail)
        self.assertEqual(diagnose(ServiceError('', 429))['category'], 'Kvóta služby')
        self.assertEqual(diagnose(ServiceError('', reason='network'))['category'], 'Síťové spojení selhalo')
        self.assertEqual(diagnose(TimeoutError())['category'], 'Vypršel časový limit')

    def test_local_checkpoint_persists_and_rejects_changed_files(self):
        with temporary_directory() as folder:
            root = Path(folder)
            for i in range(3):
                (root / f'{i}.html').write_text('<title>Duplicitní</title><h1>Test</h1>', encoding='utf-8')
            store = Store(root / 'draft.sqlite3')
            cancel = threading.Event()
            def checkpoint(data):
                store.save_draft(data)
                if len(data['report']['pages']) == 1:
                    cancel.set()
            partial = audit_local(folder, cancel=cancel, checkpoint=checkpoint)
            self.assertFalse(partial.complete)
            store.close()
            store = Store(root / 'draft.sqlite3')
            saved = store.draft()
            self.assertEqual(len(saved['report']['pages']), 1)
            full = audit_local(folder, resume=saved)
            self.assertEqual(len(full.pages), 3)
            self.assertTrue(full.complete)
            self.assertTrue(any(f.rule == 'Duplicitní titulek' for f in full.pages[0].findings))
            self.assertFalse(any(f['name'].startswith('Duplicitní') for f in saved['report']['pages'][0]['findings']))
            (root / '1.html').write_text('změněno', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'změnily'):
                audit_local(folder, resume=saved)
            self.assertEqual(store.draft(), saved)
            store.close()

    def test_zip_resume_validates_crc(self):
        with temporary_directory() as folder:
            path = Path(folder) / 'site.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('a.html', '<h1>A</h1>')
                archive.writestr('b.html', '<h1>B</h1>')
            saved = []
            audit_local(path, limit=1, checkpoint=lambda data: saved.append(copy.deepcopy(data)))
            full = audit_local(path, limit=2, resume=saved[-1])
            self.assertEqual(len(full.pages), 2)
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('a.html', '<h1>C</h1>')
                archive.writestr('b.html', '<h1>B</h1>')
            with self.assertRaisesRegex(ValueError, 'změnily'):
                audit_local(path, resume=saved[-1])

    def test_url_resume_keeps_queue_and_does_not_refetch_completed_pages(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), DeepServer)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            DeepServer.paths.clear()
            DeepServer.fixed = False
            snapshots, activities = [], []
            partial = audit_url(base, limit=2, checkpoint=lambda data: snapshots.append(json.loads(json.dumps(data))), activity=activities.append)
            self.assertFalse(partial.complete)
            saved = snapshots[-1]
            self.assertEqual(len(saved['report']['pages']), 2)
            self.assertTrue(saved['queue'])
            DeepServer.paths.clear()
            full = audit_url(base, limit=40, resume=saved)
            self.assertNotIn('/', DeepServer.paths)
            self.assertNotIn('/broken', DeepServer.paths)
            self.assertNotIn('/blocked', DeepServer.paths)
            self.assertIn('/only-map', DeepServer.paths)
            self.assertEqual(len({p.location for p in full.pages}), len(full.pages))
            self.assertTrue(any(f.rule == 'link.broken' and f.target.endswith('/broken') for f in full.pages[0].findings))
            self.assertFalse(any(f['code'] == 'link.broken' for f in saved['report']['pages'][0]['findings']))
            self.assertTrue(any(a['current'] for a in activities))
            cancel = threading.Event()
            last = []
            def checkpoint(data):
                last.append(copy.deepcopy(data))
                if data['report']['pages']:
                    cancel.set()
            audit_url(base, cancel=cancel, checkpoint=checkpoint)
            resumed = audit_url(base, limit=40, resume=last[-1])
            self.assertEqual(len(resumed.pages), len(full.pages))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
