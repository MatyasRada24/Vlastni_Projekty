import hashlib
import base64
import json
import threading
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, urlencode
from urllib.request import urlopen
from urllib.error import HTTPError
from unittest.mock import patch

from seo_checker.engine import Report, Page, analyze_html
from seo_checker.export import save_report
from seo_checker.google_services import (Vault, SearchConsole, ServiceError, SCOPE, authorize,
    load_client, match_findings, opportunity, pagespeed, property_contains, validate_dates)
from seo_checker.planning import compare_reports
from seo_checker.storage import Store
from tests.test_engine import GOOD, temporary_directory

PSI = {'lighthouseResult': {'fetchTime': '2026-10-19T10:00:00Z', 'finalUrl': 'https://site.test/',
       'categories': {'performance': {'score': .76}}, 'audits': {
           'largest-contentful-paint': {'displayValue': '3.2 s', 'numericValue': 3200, 'numericUnit': 'millisecond', 'score': .4, 'title': 'LCP', 'description': 'Zrychlete obsah.'},
           'total-blocking-time': {'displayValue': '150 ms', 'numericValue': 150},
           'cumulative-layout-shift': {'displayValue': '0', 'numericValue': 0}}, 'lighthouseVersion': 'test'},
       'loadingExperience': {'id': 'https://site.test/', 'metrics': {'INTERACTION_TO_NEXT_PAINT': {'percentile': 180, 'category': 'FAST'}}},
       'originLoadingExperience': {'id': 'https://site.test', 'metrics': {'LARGEST_CONTENTFUL_PAINT_MS': {'percentile': 2200, 'category': 'FAST'}}}}


class MemoryVault:
    def __init__(self):
        self.data = {'client': {'client_id': 'test.apps.googleusercontent.com', 'client_secret': 'secret'},
                     'tokens': {'access_token': 'old', 'refresh_token': 'refresh', 'expires_at': 0}}
    def read(self):
        return self.data.copy()
    def update(self, **values):
        self.data.update(values)
    def replace_tokens(self, expected, client, tokens):
        if self.data['tokens'] != expected or self.data['client'] != client:
            raise ServiceError('Account changed')
        self.data['tokens'] = tokens


class GoogleTests(unittest.TestCase):
    def test_pagespeed_lab_and_url_origin_field_stay_separate(self):
        calls = []
        def transport(url, **kwargs):
            calls.append(url)
            return PSI
        data = pagespeed('https://site.test/', 'mobile', 'key+/=', transport)
        self.assertEqual(data['score'], 76)
        self.assertEqual([f['scope'] for f in data['field']], ['URL', 'Původ (origin)'])
        self.assertFalse(any(m['name'] == 'INP' for m in data['lab']))
        self.assertEqual(parse_qs(urlsplit(calls[0]).query)['key'], ['key+/='])
        self.assertNotIn('key+/=', json.dumps(data))
        missing = pagespeed('https://site.test/', 'desktop', transport=lambda *a, **k: {'lighthouseResult': PSI['lighthouseResult']})
        self.assertEqual(missing['field'], [])
        self.assertIn('chybějící data', missing['field_note'])
        with self.assertRaises(ServiceError):
            pagespeed('https://site.test/', 'mobile', transport=lambda *a, **k: {'lighthouseResult': {'runtimeError': {'code': 'error'}}})

    def test_property_boundaries_and_date_validation(self):
        self.assertTrue(property_contains('sc-domain:site.test', 'https://sub.site.test/path'))
        self.assertFalse(property_contains('sc-domain:site.test', 'https://site.test.evil/path'))
        self.assertFalse(property_contains('https://site.test/a/', 'http://site.test/a/'))
        self.assertFalse(property_contains('https://site.test/a/', 'https://site.test/b/'))
        self.assertTrue(property_contains('https://site.test/a/', 'https://site.test/a/b'))
        with self.assertRaises(ServiceError):
            validate_dates('2025-02-30', '2025-03-01')
        with self.assertRaises(ServiceError):
            validate_dates('2025-02-02', '2025-02-01')

    def test_refresh_pagination_final_data_and_query_filter(self):
        vault = MemoryVault()
        requests = []
        def transport(url, **kwargs):
            if url.endswith('/token'):
                self.assertEqual(kwargs['data']['grant_type'], 'refresh_token')
                return {'access_token': 'new', 'expires_in': 3600, 'scope': SCOPE}
            requests.append((url, kwargs))
            body = kwargs['data']
            if body['dimensions'] == ['query']:
                return {'rows': [{'keys': ['dotaz'], 'clicks': 1}]}
            return {'rows': [{'keys': [f'https://site.test/{i}']} for i in range(25000)]} if body['startRow'] == 0 else {'rows': [{'keys': ['https://site.test/last']}]}
        api = SearchConsole(vault, transport)
        data = api.query('sc-domain:site.test', '2025-01-01', '2025-01-28', threading.Event())
        self.assertEqual(len(data['rows']), 25001)
        self.assertFalse(data['truncated'])
        self.assertEqual(requests[1][1]['data']['startRow'], 25000)
        self.assertEqual(requests[0][1]['data']['dataState'], 'final')
        self.assertIn('sc-domain%3Asite.test', requests[0][0])
        self.assertEqual(vault.read()['tokens']['refresh_token'], 'refresh')
        api.query('sc-domain:site.test', '2025-01-01', '2025-01-28', threading.Event(), page='https://site.test/last', max_rows=1000)
        self.assertEqual(requests[-1][1]['data']['dimensionFilterGroups'][0]['filters'][0]['expression'], 'https://site.test/last')

    def test_unauthorized_retry_once_and_cancel(self):
        vault = MemoryVault()
        vault.data['tokens']['expires_at'] = time.time() + 3600
        calls = []
        def transport(url, **kwargs):
            calls.append(url)
            if url.endswith('/token'):
                return {'access_token': 'new', 'scope': SCOPE}
            if kwargs['token'] == 'old':
                raise ServiceError('expired', 401)
            return {'siteEntry': [{'siteUrl': 'sc-domain:site.test', 'permissionLevel': 'siteOwner'}, {'siteUrl': 'hidden', 'permissionLevel': 'siteUnverifiedUser'}]}
        api = SearchConsole(vault, transport)
        self.assertEqual(api.sites(), ['sc-domain:site.test'])
        self.assertEqual(len(calls), 3)
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(ServiceError):
            api.query('sc-domain:site.test', '2025-01-01', '2025-01-28', cancel)
        self.assertEqual(len(calls), 3)

    def test_real_loopback_oauth_state_pkce_and_scope(self):
        observed = {}
        completed = threading.Event()
        errors = []
        def opener(url):
            query = parse_qs(urlsplit(url).query)
            observed.update(query)
            def callback():
                try:
                    try:
                        urlopen(query['redirect_uri'][0] + '?' + urlencode({'state': 'wrong', 'code': 'attacker'})).close()
                    except HTTPError as exc:
                        exc.close()
                    urlopen(query['redirect_uri'][0] + '?' + urlencode({'state': query['state'][0], 'code': 'test-code'})).close()
                except Exception as exc:
                    errors.append(exc)
                finally:
                    completed.set()
            threading.Thread(target=callback, daemon=True).start()
            return True
        def exchange(url, **kwargs):
            body = kwargs['data']
            self.assertEqual(body['code'], 'test-code')
            challenge = base64.urlsafe_b64encode(hashlib.sha256(body['code_verifier'].encode()).digest()).rstrip(b'=').decode()
            self.assertEqual(observed['code_challenge'], [challenge])
            self.assertEqual(observed['scope'], [SCOPE])
            self.assertTrue(body['redirect_uri'].startswith('http://127.0.0.1:'))
            return {'access_token': 'a', 'refresh_token': 'r', 'scope': SCOPE}
        result = authorize({'client_id': 'test'}, threading.Event(), opener, exchange, timeout=5)
        self.assertEqual(result['refresh_token'], 'r')
        self.assertTrue(completed.wait(2))
        self.assertFalse(errors)

    def test_windows_vault_and_client_validation(self):
        with temporary_directory() as folder:
            vault = Vault(Path(folder) / 'secrets.dat')
            vault.update(api_key='sensitive-key', tokens={'refresh_token': 'sensitive-token'})
            self.assertNotIn(b'sensitive', vault.path.read_bytes())
            self.assertEqual(vault.read()['api_key'], 'sensitive-key')
            vault.update(tokens=None)
            self.assertIsNone(vault.read()['tokens'])
            path = Path(folder) / 'client.json'
            path.write_text(json.dumps({'web': {'client_id': 'x'}}))
            with self.assertRaises(ServiceError):
                load_client(path)
            path.write_text(json.dumps({'installed': {'client_id': 'x.apps.googleusercontent.com', 'token_uri': 'https://evil.invalid'}}))
            self.assertNotIn('token_uri', load_client(path))

    def test_disconnect_during_refresh_cannot_restore_tokens(self):
        vault = MemoryVault()
        def transport(*args, **kwargs):
            vault.update(tokens=None)
            return {'access_token': 'late', 'refresh_token': 'r', 'scope': SCOPE}
        with self.assertRaises(ServiceError):
            SearchConsole(vault, transport).token()
        self.assertIsNone(vault.read()['tokens'])

    def test_matching_opportunity_and_immutable_measurements(self):
        page = Page('https://site.test/old', canonical='https://site.test/new')
        page.add('Chyba', 'Titulek', '<script>alert(1)</script>')
        report = Report('https://site.test/', 'URL', pages=[page])
        self.assertEqual(len(match_findings(report, 'https://site.test/new')), 1)
        self.assertFalse(match_findings(report, 'http://site.test/new'))
        self.assertTrue(opportunity({'impressions': 120, 'ctr': .01}))
        self.assertFalse(opportunity({'impressions': 1, 'ctr': 0}))
        with temporary_directory() as folder:
            store = Store(Path(folder) / 'db.sqlite3')
            _, audit_id = store.save(report)
            before = store.load(audit_id)[1].to_dict()
            data = pagespeed(report.source, 'mobile', transport=lambda *a, **k: PSI)
            data['warnings'] = ['<script>bad()</script>']
            store.save_measurement(audit_id, 'pagespeed', data)
            self.assertEqual(before, store.load(audit_id)[1].to_dict())
            saved = store.measurements(audit_id)
            save_report(report, Path(folder) / 'out.html', measurements=saved)
            self.assertNotIn('<script>bad()', (Path(folder) / 'out.html').read_text(encoding='utf-8'))
            store.close()
            store = Store(Path(folder) / 'db.sqlite3')
            self.assertEqual(store.measurements(audit_id), saved)
            store.close()

    def test_changed_rendering_is_not_a_confirmed_fix(self):
        old, _ = analyze_html('<h1>Test</h1>', 'https://site.test/')
        new, _ = analyze_html(GOOD, old.location)
        new.analysis_mode = 'rendered'
        before = Report(old.location, 'URL', pages=[old])
        after = Report(old.location, 'URL', pages=[new], rendering=True)
        self.assertFalse(compare_reports(before, after)['Odstraněné'])
        new.analysis_mode = old.analysis_mode = 'rendered'
        self.assertTrue(compare_reports(before, after)['Odstraněné'])
        new.analysis_mode = 'render_failed'
        self.assertFalse(compare_reports(before, after)['Odstraněné'])


if __name__ == '__main__':
    unittest.main()
