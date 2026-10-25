import io
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from seo_checker.google_services import SITES_URL, PSI_URL, TOKEN_URL, ServiceError, request_json


class GoogleErrorTests(unittest.TestCase):
    def error(self, payload, url=SITES_URL, code=403):
        stream = io.BytesIO(payload if isinstance(payload, bytes) else json.dumps(payload).encode())
        response = HTTPError(url, code, 'secret server text', {}, stream)
        with patch('seo_checker.google_services.build_opener') as opener:
            opener.return_value.open.side_effect = response
            with self.assertRaises(ServiceError) as caught:
                request_json(url, token='secret-token')
        self.assertTrue(stream.closed)
        self.assertEqual(caught.exception.status, code)
        self.assertNotIn('secret', str(caught.exception))
        return caught.exception

    def test_disabled_api_modern_and_legacy_responses(self):
        for field, reason in [('details', 'SERVICE_DISABLED'), ('errors', 'accessNotConfigured')]:
            with self.subTest(field=field):
                error = self.error({'error': {'message': 'secret-token', field: [{'reason': reason, 'metadata': {'activationUrl': 'https://untrusted.test/secret'}}]}})
                self.assertEqual(error.reason, 'service_disabled')
                self.assertIn('Google Search Console API není zapnuté', str(error))
                self.assertNotIn('untrusted', str(error))
        speed = self.error({'error': {'details': [{'reason': 'SERVICE_DISABLED'}]}}, PSI_URL)
        self.assertIn('PageSpeed Insights API není zapnuté', str(speed))

    def test_scope_quota_and_expired_login_are_distinct(self):
        scope = self.error({'error': {'details': [{'reason': 'ACCESS_TOKEN_SCOPE_INSUFFICIENT'}]}})
        self.assertEqual(scope.reason, 'insufficient_scope')
        quota = self.error({'error': {'errors': [{'reason': 'dailyLimitExceeded'}]}})
        self.assertEqual(quota.reason, 'quota')
        self.assertNotIn('API klíč', str(quota))
        expired = self.error({'error': 'invalid_grant', 'error_description': 'secret'}, TOKEN_URL, 400)
        self.assertEqual(expired.reason, 'login_expired')

    def test_unknown_or_malformed_error_keeps_safe_fallback(self):
        for payload in [b'<html>secret</html>', b'\xff', b'[]', {'error': None}, {'error': {'details': None, 'errors': [None, {'reason': []}, {'reason': 'secret'}]}}]:
            with self.subTest(payload=payload):
                error = self.error(payload)
                self.assertEqual(error.reason, '')
                self.assertIn('HTTP 403', str(error))
                self.assertNotIn('API klíč', str(error))


if __name__ == '__main__':
    unittest.main()
