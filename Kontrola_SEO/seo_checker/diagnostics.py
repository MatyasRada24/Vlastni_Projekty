"""Error categories and deliberately allowlisted, credential-free support details."""
import socket
import sqlite3
from datetime import datetime
from urllib.error import URLError

from . import __version__


def diagnose(error, action='audit'):
    code = getattr(error, 'status', 0)
    code = code if isinstance(code, int) and 100 <= code <= 599 else 0
    reason = getattr(error, 'reason', '')
    if code == 429 or reason == 'quota':
        category, step = 'Kvóta služby', 'Počkejte a ověřte kvótu projektu. U PageSpeed zkontrolujte nastavení vlastního API klíče.'
    elif code == 401 or reason == 'login_expired':
        category, step = 'Přihlášení vypršelo', 'Přihlaste znovu Google účet v Připojení služeb.'
    elif reason == 'service_disabled':
        category, step = 'API není zapnuté', 'V Google Cloud zapněte požadované API ve stejném projektu jako použité připojení.'
    elif reason == 'insufficient_scope' or code == 403 or reason == 'no_sites':
        category, step = 'Chybějící oprávnění', 'Ověřte přístup účtu k webu a oprávnění aplikace. U PageSpeed zkontrolujte omezení klíče.'
    elif isinstance(error, (TimeoutError, socket.timeout)) or reason == 'timeout':
        category, step = 'Vypršel časový limit', 'Zkontrolujte dostupnost služby a zkuste akci zopakovat později.'
    elif isinstance(error, (ConnectionError, URLError)) or reason == 'network':
        category, step = 'Síťové spojení selhalo', 'Ověřte internet, DNS, proxy nebo firewall. Samotná chyba nepotvrzuje odpojení Google účtu.'
    elif isinstance(error, (sqlite3.Error, PermissionError)) or reason == 'storage':
        category, step = 'Zápis nebo čtení dat selhalo', 'Ověřte volné místo a oprávnění k datové složce. Dostupné výsledky exportujte.'
    elif isinstance(error, ValueError) or code == 400 or reason in ('audit_required', 'account_required'):
        category, step = 'Nastavení nebo zadání', 'Zkontrolujte zadanou adresu, soubor, období a nastavení požadované služby.'
    elif code >= 500 or reason == 'invalid_response':
        category, step = 'Služba neodpověděla správně', 'Zkuste akci později. Pokud se chyba opakuje, zkopírujte diagnostiku.'
    else:
        category, step = 'Neočekávaná chyba aplikace', 'Zkopírujte diagnostiku a popište poslední provedený krok. Potom aplikaci znovu otevřete.'
    safe_action = action if action in ('audit', 'speed', 'speed-test', 'search', 'sites', 'sites-test', 'queries', 'auth', 'storage', 'settings', 'input', 'repair') else 'application'
    safe_type = type(error).__name__ if type(error).__name__ in (
        'ServiceError', 'ValueError', 'RuntimeError', 'TypeError', 'AttributeError', 'KeyError', 'OSError',
        'PermissionError', 'TimeoutError', 'URLError', 'OperationalError', 'IntegrityError', 'ConnectionError') else 'Error'
    # Never serialize exception text, stack locals, URLs, file paths, request bodies,
    # vault contents, or arbitrary server reason strings into copied diagnostics.
    technical = (f'Kontrola SEO {__version__}\nČas: {datetime.now().astimezone().isoformat(timespec="seconds")}\n'
                 f'Akce: {safe_action}\nKategorie: {category}\nTyp: {safe_type}\nHTTP: {code or "neuvedeno"}\n'
                 f'Další krok: {step}\nDiagnostika neobsahuje adresy webů, místní cesty, hesla, tokeny ani API klíče.')
    return {'category': category, 'step': step, 'technical': technical}


def copy_diagnostic(root, diagnostic):
    if diagnostic:
        root.clipboard_clear()
        root.clipboard_append(diagnostic['technical'])
