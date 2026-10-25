"""Isolated, bounded Chromium rendering; never uses a person's browser profile."""
import os
import time
from http.client import HTTPException
from pathlib import Path

from .engine import MAX_BYTES
from .network import open_url


def browser_path():
    for root in (os.environ.get('PROGRAMFILES', ''), os.environ.get('PROGRAMFILES(X86)', ''), os.environ.get('LOCALAPPDATA', '')):
        for relative in ('Microsoft/Edge/Application/msedge.exe', 'Google/Chrome/Application/chrome.exe',
                         'BraveSoftware/Brave-Browser/Application/brave.exe'):
            path = Path(root) / relative
            if path.is_file():
                return str(path)
    raise RuntimeError('Pro vykreslení nainstalujte Microsoft Edge, Google Chrome nebo Brave.')


class Renderer:
    def __enter__(self):
        from playwright.sync_api import sync_playwright
        executable = browser_path()
        self.driver = None
        try:
            self.driver = sync_playwright().start()
            self.browser = self.driver.chromium.launch(executable_path=executable, headless=True,
                                                       chromium_sandbox=True,
                                                       args=['--force-webrtc-ip-handling-policy=disable_non_proxied_udp'])
        except Exception:
            if self.driver:
                self.driver.stop()
            raise RuntimeError('Prohlížeč nelze spustit. Zavřete audit a ověřte instalaci Edge, Chrome nebo Brave.') from None
        return self

    def render(self, result, cancel):
        # One fresh context per page: no login, history, cookies from another audit,
        # service workers, downloads or persistent profile.
        context = self.browser.new_context(viewport={'width': 1365, 'height': 900},
                                           service_workers='block', accept_downloads=False)
        page = context.new_page()
        failures = []
        redirected = []
        served = False
        transferred = 0
        requests = 0
        deadline = time.monotonic() + 40

        def route_request(route):
            nonlocal served, transferred, requests
            request = route.request
            if cancel.is_set():
                route.abort()
            elif request.is_navigation_request() and request.frame == page.main_frame:
                if not served and request.url == result.url:
                    served = True
                    # Reuse the already fetched, robots-checked document. Transport
                    # headers must not describe its decoded body to the browser.
                    headers = {k: v for k, v in result.headers.items()
                               if k.lower() not in ('content-length', 'content-encoding', 'transfer-encoding')}
                    route.fulfill(status=result.status, headers=headers, body=result.data)
                else:
                    redirected.append(request.url)
                    route.abort()
            elif request.url.startswith(('http://', 'https://')):
                # The browser never connects directly: DNS is checked and pinned
                # by our transport. Redirects are processed as new routed requests.
                requests += 1
                try:
                    if (request.method != 'GET' or requests > 100 or transferred >= 50 * 1024 * 1024
                            or time.monotonic() >= deadline):
                        raise ValueError('Limit vykreslování')
                    with open_url(request.url, timeout=5) as response:
                        body = response.read(MAX_BYTES + 1)
                        if len(body) > MAX_BYTES:
                            raise ValueError('Limit zdroje')
                        transferred += len(body)
                        headers = {k: v for k, v in response.headers.items()
                                   if k.lower() not in ('connection', 'transfer-encoding', 'content-length', 'set-cookie')}
                        route.fulfill(status=response.status, headers=headers, body=body)
                except (OSError, ValueError, HTTPException):
                    failures.append('Zdroj blokovaný bezpečnostními pravidly nebo nedostupný.')
                    route.abort()
            else:
                route.abort()

        context.route('**/*', route_request)
        # A routed socket is not connected unless connect_to_server is called.
        # Leave it disconnected; synchronous close in the route callback can hang.
        context.route_web_socket('**/*', lambda ws: None)
        page.on('requestfailed', lambda request: failures.append(request.url)
                if request.resource_type in ('script', 'xhr', 'fetch') else None)
        try:
            page.goto(result.url, wait_until='domcontentloaded', timeout=25000)
            # Explicit observation window, not a claim that all asynchronous work
            # or user-triggered content has finished.
            for _ in range(20):
                if cancel.is_set():
                    raise RuntimeError('Vykreslování bylo zastaveno.')
                page.wait_for_timeout(100)
            if redirected or page.url.split('#')[0] != result.url.split('#')[0]:
                raise RuntimeError('Stránka změnila adresu pomocí JavaScriptu. Zkontrolujte cílovou URL samostatně.')
            if failures:
                raise RuntimeError('Nepodařilo se načíst skript nebo datový požadavek: ' + failures[0][:300])
            html = page.content()
            if len(html.encode('utf-8')) > MAX_BYTES:
                raise RuntimeError('Vykreslené HTML překračuje limit 5 MB.')
            return html
        except RuntimeError:
            raise
        except Exception:
            raise RuntimeError('Vykreslení se nepodařilo dokončit do 25 sekund nebo prohlížeč selhal.') from None
        finally:
            context.close()

    def __exit__(self, *args):
        try:
            self.browser.close()
        finally:
            self.driver.stop()
