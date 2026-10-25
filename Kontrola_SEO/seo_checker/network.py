"""Bounded HTTP transport with validated, pinned DNS and normal TLS verification."""
import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urlsplit


def local_target(url):
    """Only an explicitly entered local IP/localhost opts into local auditing."""
    host = urlsplit(url).hostname or ''
    if host == 'localhost':
        return host
    try:
        ip = ipaddress.ip_address(host)
        return host if ip.is_private or ip.is_loopback else ''
    except ValueError:
        return ''


def addresses(host, port, allowed_local=''):
    rows = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    ips = list(dict.fromkeys(row[4][0] for row in rows))
    if not ips or any((not ipaddress.ip_address(ip).is_global or ipaddress.ip_address(ip).is_multicast)
                      for ip in ips) and host != allowed_local:
        raise ValueError('Požadavek do místní nebo neveřejné sítě byl zablokován.')
    return ips


def open_url(url, headers=None, timeout=12, allowed_local=''):
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise ValueError('Nepovolená síťová adresa.')
    host = parts.hostname
    port = parts.port or (443 if parts.scheme == 'https' else 80)
    ips = addresses(host, port, allowed_local)
    connection = http.client.HTTPConnection(host, port, timeout=timeout)
    # Connect to the validated literal IP, never resolve the hostname a second time.
    sock = socket.create_connection((ips[0], port), timeout=timeout)
    try:
        if parts.scheme == 'https':
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        connection.sock = sock
        connection.request('GET', (parts.path or '/') + ('?' + parts.query if parts.query else ''),
                           headers={**(headers or {}), 'Connection': 'close'})
        response = connection.getresponse()
        response.code = response.status
        return response
    except BaseException:
        sock.close()
        connection.close()
        raise
