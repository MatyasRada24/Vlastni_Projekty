"""Read-only Google integrations. Tokens never enter audit snapshots or exports."""
from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import secrets
import threading
import time
import webbrowser
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .engine import normalize_url
from .storage import default_database

SCOPE = 'https://www.googleapis.com/auth/webmasters.readonly'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
SITES_URL = 'https://www.googleapis.com/webmasters/v3/sites'
PSI_URL = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
VAULT_LOCK = threading.RLock()


class ServiceError(RuntimeError):
    def __init__(self, message, status=0, reason=''):
        super().__init__(message)
        self.status = status
        self.reason = reason


def api_error(payload, code, url):
    """Classify bounded error JSON without displaying server text or credentials."""
    reasons = set()
    try:
        error = json.loads(payload).get('error', {})
        if isinstance(error, str):
            reasons.add(error)
        elif isinstance(error, dict):
            for field in ('details', 'errors'):
                entries = error.get(field)
                if isinstance(entries, list):
                    for entry in entries:
                        if isinstance(entry, dict) and isinstance(entry.get('reason'), str):
                            reasons.add(entry['reason'])
    except (ValueError, UnicodeError, AttributeError):
        pass
    is_search = urlsplit(url).path.startswith('/webmasters/')
    if code == 403 and reasons & {'SERVICE_DISABLED', 'accessNotConfigured'}:
        service = 'Google Search Console API' if is_search else 'PageSpeed Insights API'
        return ServiceError(f'{service} není zapnuté v projektu použitého připojení. V Google Cloud vyberte stejný projekt, otevřete APIs & Services → Library, vyhledejte {service} a klikněte na Enable / Povolit. Po aktivaci chvíli počkejte a požadavek zopakujte.', code, 'service_disabled')
    if code == 403 and reasons & {'ACCESS_TOKEN_SCOPE_INSUFFICIENT', 'insufficientPermissions'}:
        return ServiceError('Přihlášení nemá potřebné oprávnění. Přihlaste Google účet znovu a povolte aplikaci čtení dat Search Console.', code, 'insufficient_scope')
    if code in (403, 429) and (code == 429 or reasons & {'rateLimitExceeded', 'userRateLimitExceeded', 'dailyLimitExceeded', 'RATE_LIMIT_EXCEEDED', 'QUOTA_EXCEEDED'}):
        message = 'Google omezil počet požadavků. Zkuste to později a ověřte kvótu projektu v Google Cloud.'
        if not is_search:
            message += ' Pro PageSpeed můžete nastavit vlastní API klíč.'
        return ServiceError(message, code, 'quota')
    if url == TOKEN_URL and 'invalid_grant' in reasons:
        return ServiceError('Uložené přihlášení vypršelo nebo bylo odvoláno. Klikněte na Přihlásit Google účet a připojte účet znovu.', code, 'login_expired')
    messages = {400: 'Google odmítl požadavek. Ověřte nastavení klienta, URL a období; případně se znovu přihlaste.',
                401: 'Přihlášení vypršelo nebo bylo odvoláno. Přihlaste se znovu.',
                403: ('Google odmítl přístup k Search Console (HTTP 403). Ověřte zapnuté Search Console API ve stejném projektu a oprávnění přihlášeného účtu k vybranému webu.' if is_search else 'Chybí oprávnění, zapnuté API nebo platný klíč. Ověřte nastavení v Google Cloud.')}
    return ServiceError(messages.get(code, f'Google API vrátilo HTTP {code}. Zkuste to později.'), code)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None  # Never forward a bearer token or key to a redirected host.


def request_json(url, *, data=None, token='', form=False, timeout=30):
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    body = None
    if data is not None:
        body = (urlencode(data) if form else json.dumps(data)).encode('utf-8')
        headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
    try:
        with build_opener(NoRedirect()).open(Request(url, data=body, headers=headers), timeout=timeout) as response:
            payload = response.read(20 * 1024 * 1024 + 1)
        if len(payload) > 20 * 1024 * 1024:
            raise ServiceError('Odpověď Google API je příliš velká.')
        result = json.loads(payload)
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except HTTPError as exc:
        # Server messages can echo credentials or queried URLs. Show a controlled
        # explanation instead, and never include Request/full URL in exceptions.
        try:
            payload = exc.read(65536)
        except OSError:
            payload = b''
        finally:
            exc.close()
        raise api_error(payload, exc.code, url) from None
    except TimeoutError:
        raise ServiceError('Vypršel časový limit Google API. Zkuste akci později.', reason='timeout') from None
    except (OSError, URLError) as exc:
        reason = 'timeout' if isinstance(getattr(exc, 'reason', None), TimeoutError) else 'network'
        raise ServiceError('Google API není dostupné nebo vypršel časový limit. Ověřte připojení.', reason=reason) from None
    except (ValueError, UnicodeError):
        raise ServiceError('Google API nevrátilo platná JSON data.', reason='invalid_response') from None


class Blob(ctypes.Structure):
    _fields_ = [('size', ctypes.c_ulong), ('data', ctypes.POINTER(ctypes.c_ubyte))]


def protect(data, decrypt=False):
    if os.name != 'nt':
        raise ServiceError('Uložení přihlášení vyžaduje Windows DPAPI.')
    buffer = ctypes.create_string_buffer(data)
    incoming = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    outgoing = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(Blob)]
    fn.restype = ctypes.c_int
    if not fn(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise ServiceError('Windows nedokázal otevřít nebo uložit přihlášení pro tento uživatelský účet.')
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        kernel.LocalFree(outgoing.data)


class Vault:
    def __init__(self, path=None):
        self.path = Path(path) if path else default_database().parent / 'google-secrets.dat'

    def read(self):
        if not self.path.exists():
            return {}
        try:
            return json.loads(protect(self.path.read_bytes(), decrypt=True))
        except (ValueError, OSError):
            raise ServiceError('Uložené nastavení Google nelze přečíst.') from None

    def write(self, data):
        encrypted = protect(json.dumps(data).encode('utf-8'))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(self.path.name + '.' + secrets.token_hex(6) + '.tmp')
        try:
            temp.write_bytes(encrypted)
            os.replace(temp, self.path)
        finally:
            if temp.exists():
                temp.unlink()

    def update(self, **values):
        with VAULT_LOCK:
            data = self.read()
            data.update(values)
            self.write(data)

    def replace_tokens(self, expected, client, tokens):
        with VAULT_LOCK:
            data = self.read()
            if data.get('tokens') != expected or data.get('client') != client:
                raise ServiceError('Přihlášení se mezitím změnilo nebo bylo odpojeno. Zkuste požadavek znovu.')
            data['tokens'] = tokens
            self.write(data)


def load_client(path):
    if Path(path).stat().st_size > 65536:
        raise ServiceError('Soubor klienta je příliš velký.')
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8-sig'))['installed']
        if not data.get('client_id', '').endswith('.apps.googleusercontent.com'):
            raise ValueError()
        return {key: data.get(key, '') for key in ('client_id', 'client_secret')}
    except (ValueError, KeyError, TypeError):
        raise ServiceError('Vyberte JSON OAuth klienta typu Desktop app stažený z Google Cloud.') from None


def token_data(result, old=None):
    scopes = result.get('scope', SCOPE).split()
    if SCOPE not in scopes and 'https://www.googleapis.com/auth/webmasters' not in scopes:
        raise ServiceError('Nebylo uděleno oprávnění ke čtení Search Console.')
    if not result.get('access_token'):
        raise ServiceError('Google nevrátil přístupový token.')
    return {'access_token': result['access_token'], 'refresh_token': result.get('refresh_token') or (old or {}).get('refresh_token', ''),
            'expires_at': time.time() + float(result.get('expires_in', 3600)), 'scope': SCOPE}


def authorize(client, cancel, opener=webbrowser.open, transport=request_json, timeout=180):
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).rstrip(b'=').decode('ascii')
    outcome = {}

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Callback URLs contain single-use authorization codes.

        def do_GET(self):
            parts = urlsplit(self.path)
            values = parse_qs(parts.query)
            valid = (parts.path == '/oauth/callback' and
                     secrets.compare_digest(values.get('state', [''])[0], state))
            if valid:
                outcome.update(code=values.get('code', [''])[0], error=values.get('error', [''])[0])
            body = ('Přihlášení bylo předáno aplikaci. Toto okno můžete zavřít.' if valid else 'Neplatný návrat přihlášení.').encode('utf-8')
            self.send_response(200 if valid else 400)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with HTTPServer(('127.0.0.1', 0), Callback) as server:
        server.timeout = .25
        redirect = f'http://127.0.0.1:{server.server_port}/oauth/callback'
        auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
            'client_id': client['client_id'], 'redirect_uri': redirect, 'response_type': 'code',
            'scope': SCOPE, 'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256',
            'access_type': 'offline', 'prompt': 'consent'})
        if not opener(auth_url):
            raise ServiceError('Nepodařilo se otevřít výchozí prohlížeč pro přihlášení.')
        deadline = time.monotonic() + timeout
        while not outcome and not cancel.is_set() and time.monotonic() < deadline:
            server.handle_request()
    if cancel.is_set():
        raise ServiceError('Přihlášení bylo zastaveno.')
    if not outcome:
        raise ServiceError('Přihlášení nebylo dokončeno do 3 minut. Zkuste to znovu.')
    if outcome.get('error') or not outcome.get('code'):
        raise ServiceError('Přístup nebyl udělen. Přihlášení můžete zkusit znovu.')
    return token_data(transport(TOKEN_URL, data={**client, 'code': outcome['code'], 'code_verifier': verifier,
                                               'redirect_uri': redirect, 'grant_type': 'authorization_code'}, form=True))


def property_contains(property_url, url):
    try:
        url = normalize_url(url)
        if property_url.startswith('sc-domain:'):
            host = urlsplit(url).hostname or ''
            domain = property_url[10:].lower().rstrip('.')
            return bool(domain) and (host == domain or host.endswith('.' + domain))
        prefix = normalize_url(property_url)
        return url.startswith(prefix)
    except ValueError:
        return False


def validate_dates(start, end):
    try:
        a, b = date.fromisoformat(start), date.fromisoformat(end)
        if a > b or (b - a).days > 486 or b > date.today():
            raise ValueError()
    except ValueError:
        raise ServiceError('Zadejte platné období RRRR-MM-DD, nejvýše 16 měsíců a bez budoucích dat.') from None


class SearchConsole:
    def __init__(self, vault, transport=request_json):
        self.vault, self.transport = vault, transport

    def token(self, refresh=False):
        data = self.vault.read()
        tokens = data.get('tokens') or {}
        if tokens.get('access_token') and tokens.get('expires_at', 0) > time.time() + 60 and not refresh:
            return tokens['access_token']
        if not tokens.get('refresh_token') or not data.get('client'):
            raise ServiceError('Nejprve se přihlaste ke Google Search Console.')
        result = self.transport(TOKEN_URL, data={**data['client'], 'refresh_token': tokens['refresh_token'], 'grant_type': 'refresh_token'}, form=True)
        refreshed = token_data(result, tokens)
        self.vault.replace_tokens(tokens, data['client'], refreshed)
        return refreshed['access_token']

    def call(self, url, data=None):
        try:
            return self.transport(url, token=self.token(), data=data)
        except ServiceError as exc:
            if exc.status != 401:
                raise
        return self.transport(url, token=self.token(refresh=True), data=data)

    def sites(self):
        return [row['siteUrl'] for row in self.call(SITES_URL).get('siteEntry', [])
                if row.get('permissionLevel') in ('siteOwner', 'siteFullUser', 'siteRestrictedUser')]

    def query(self, property_url, start, end, cancel, page=None, max_rows=50000):
        validate_dates(start, end)
        if page and not property_contains(property_url, page):
            raise ServiceError('Stránka nepatří do vybrané služby Search Console.')
        rows = []
        truncated = False
        while len(rows) < max_rows:
            if cancel.is_set():
                raise ServiceError('Načítání Search Console bylo zastaveno. Neúplný výsledek nebyl uložen.')
            limit = min(25000, max_rows - len(rows))
            body = {'startDate': start, 'endDate': end, 'dimensions': ['query'] if page else ['page'],
                    'type': 'web', 'dataState': 'final', 'aggregationType': 'auto', 'rowLimit': limit, 'startRow': len(rows)}
            if page:
                body['dimensionFilterGroups'] = [{'filters': [{'dimension': 'page', 'operator': 'equals', 'expression': page}]}]
            result = self.call(SITES_URL + '/' + quote(property_url, safe='') + '/searchAnalytics/query', body)
            batch = result.get('rows', [])
            rows.extend(batch)
            if len(batch) < limit:
                break
            truncated = len(rows) >= max_rows
        if cancel.is_set():
            raise ServiceError('Načítání bylo zastaveno.')
        return {'property': property_url, 'start': start, 'end': end, 'page': page, 'rows': rows,
                'truncated': truncated, 'created': datetime.now().astimezone().isoformat(timespec='seconds'),
                'note': 'Webové vyhledávání, dokončená data, dny v časovém pásmu Pacific Time. API vrací nejvýše dostupné horní řádky, nikoli všechna data. Anonymizované dotazy mohou chybět.'}


def pagespeed(url, strategy, api_key='', transport=request_json):
    url = normalize_url(url)
    if strategy not in ('mobile', 'desktop'):
        raise ServiceError('Neplatný typ zařízení.')
    params = {'url': url, 'strategy': strategy, 'category': 'performance', 'locale': 'cs'}
    if api_key:
        params['key'] = api_key
    data = transport(PSI_URL + '?' + urlencode(params), timeout=90)
    lighthouse = data.get('lighthouseResult') or {}
    if lighthouse.get('runtimeError') or not lighthouse.get('audits'):
        raise ServiceError('PageSpeed nemohl stránku změřit. Ověřte veřejnou dostupnost URL a zkuste to znovu.')
    audits = lighthouse['audits']
    lab = []
    for key, name in [('first-contentful-paint', 'FCP'), ('largest-contentful-paint', 'LCP'),
                      ('speed-index', 'Speed Index'), ('total-blocking-time', 'TBT'), ('cumulative-layout-shift', 'CLS')]:
        row = audits.get(key) or {}
        lab.append({'name': name, 'value': row.get('displayValue', 'Neověřeno'), 'numeric': row.get('numericValue'), 'unit': row.get('numericUnit')})
    suggestions = [{'title': row.get('title', key), 'description': row.get('description', ''), 'value': row.get('displayValue', '')}
                   for key, row in audits.items() if isinstance(row.get('score'), (float, int)) and row['score'] < .9
                   and row.get('scoreDisplayMode') not in ('notApplicable', 'manual') and key not in ('screenshot-thumbnails', 'final-screenshot')]
    # URL and origin CrUX are separate datasets. Never silently substitute origin
    # data for the URL, and never manufacture INP from laboratory TBT.
    fields = []
    for scope, key in [('URL', 'loadingExperience'), ('Původ (origin)', 'originLoadingExperience')]:
        source = data.get(key) or {}
        metrics = source.get('metrics') or {}
        if metrics:
            fields.append({'scope': scope, 'id': source.get('id', ''), 'overall': source.get('overall_category', ''), 'metrics': metrics})
    score = (lighthouse.get('categories', {}).get('performance') or {}).get('score')
    return {'url': url, 'strategy': strategy, 'created': lighthouse.get('fetchTime') or datetime.now().astimezone().isoformat(timespec='seconds'),
            'final_url': lighthouse.get('finalDisplayedUrl') or lighthouse.get('finalUrl', url),
            'score': round(score * 100) if isinstance(score, (int, float)) else None,
            'lab': lab, 'field': fields, 'suggestions': suggestions,
            'environment': lighthouse.get('configSettings', {}), 'version': lighthouse.get('lighthouseVersion', ''),
            'warnings': lighthouse.get('runWarnings', []),
            'field_note': 'Skuteční návštěvníci: CrUX, agregované období obvykle 28 dní. URL a původ jsou uvedeny odděleně. Google dostupnost CrUX v PageSpeed postupně omezuje; chybějící data nejsou úspěšný test.'}


def match_findings(report, url):
    """Exact URL/canonical match only; never merge www, protocols or query strings."""
    matches = []
    for page in report.pages:
        if url in (page.location, page.canonical, page.redirects[-1] if page.redirects else ''):
            matches.extend((page, f) for f in page.findings if f.status in ('Chyba', 'Doporučení'))
    return matches


def opportunity(row, min_impressions=100, max_ctr=.02):
    return row.get('impressions', 0) >= min_impressions and row.get('ctr', 0) < max_ctr
