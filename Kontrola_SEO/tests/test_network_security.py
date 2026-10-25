import unittest
from unittest.mock import patch, MagicMock
from seo_checker.network import addresses, local_target, open_url

class NetworkSecurityTests(unittest.TestCase):
    def dns(self, *ips):
        return [(2, 1, 6, '', (ip, 80)) for ip in ips]

    def test_private_and_mixed_dns_blocked(self):
        for ip in ['127.0.0.1', '10.0.0.1', '169.254.169.254', '::1', '::ffff:127.0.0.1', '0.0.0.0', '224.0.0.1']:
            with self.subTest(ip=ip), patch('socket.getaddrinfo', return_value=self.dns('8.8.8.8', ip)):
                with self.assertRaises(ValueError):
                    addresses('public.test', 80)

    def test_local_opt_in_is_exact(self):
        self.assertEqual(local_target('http://127.0.0.1/'), '127.0.0.1')
        self.assertEqual(local_target('http://public.test/'), '')
        with patch('socket.getaddrinfo', return_value=self.dns('127.0.0.1')):
            self.assertEqual(addresses('127.0.0.1', 80, '127.0.0.1'), ['127.0.0.1'])
            with self.assertRaises(ValueError):
                addresses('evil.test', 80, '127.0.0.1')

    def test_pinned_ip_preserves_tls_hostname(self):
        with patch('socket.getaddrinfo', return_value=self.dns('8.8.8.8')) as dns, \
             patch('socket.create_connection') as connect, \
             patch('ssl.create_default_context') as tls, \
             patch('http.client.HTTPConnection') as http:
            open_url('https://public.test/page?q=1')
            dns.assert_called_once()
            connect.assert_called_once_with(('8.8.8.8', 443), timeout=12)
            tls.return_value.wrap_socket.assert_called_once_with(connect.return_value, server_hostname='public.test')
            self.assertEqual(http.return_value.request.call_args.args[:2], ('GET', '/page?q=1'))

    def test_non_http_and_credentials_rejected(self):
        for url in ['file:///etc/passwd', 'ftp://example.com/a', 'https://user:pass@example.com/']:
            with self.assertRaises(ValueError):
                open_url(url)
