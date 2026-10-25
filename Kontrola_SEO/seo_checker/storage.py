"""Local, transactional project history. Audit snapshots are immutable."""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from .engine import Report, normalize_url
from .planning import WORK_STATES, compare_reports, issues


def default_database():
    root = Path(os.environ.get("SEO_CHECKER_DATA_DIR") or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "KontrolaSEO")
    return root / "projects.sqlite3"


class Store:
    def __init__(self, path=None):
        self.path = str(path if path is not None else default_database())
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY, identity TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL, source TEXT NOT NULL, mode TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audits (
                id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
                created TEXT NOT NULL, report TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS audits_project ON audits(project_id,id);
            CREATE TABLE IF NOT EXISTS issue_states (
                project_id INTEGER NOT NULL REFERENCES projects(id), issue_key TEXT NOT NULL,
                state TEXT NOT NULL, updated TEXT NOT NULL, audit_id INTEGER NOT NULL REFERENCES audits(id),
                PRIMARY KEY(project_id,issue_key)
            );
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY, audit_id INTEGER NOT NULL REFERENCES audits(id),
                kind TEXT NOT NULL, created TEXT NOT NULL, payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS measurements_audit ON measurements(audit_id,id);
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS repair_checks (
                id INTEGER PRIMARY KEY, audit_id INTEGER NOT NULL REFERENCES audits(id),
                created TEXT NOT NULL, payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS repair_checks_audit ON repair_checks(audit_id,id);
            CREATE TABLE IF NOT EXISTS audit_work_states (
                audit_id INTEGER PRIMARY KEY REFERENCES audits(id), updated TEXT NOT NULL, payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_draft (
                id INTEGER PRIMARY KEY CHECK(id=1), updated TEXT NOT NULL, payload TEXT NOT NULL
            );
        ''')

    def get_setting(self, key):
        row = self.db.execute('SELECT payload FROM settings WHERE key=?', (key,)).fetchone()
        if row:
            try:
                value = json.loads(row['payload'])
                return value if isinstance(value, dict) else {}
            except (ValueError, TypeError):
                pass
        return {}

    def set_setting(self, key, value):
        with self.db:
            self.db.execute('INSERT INTO settings(key,payload) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload',
                            (key, json.dumps(value, ensure_ascii=False)))

    def project_identity(self, report):
        if report.mode == "URL":
            parts = urlsplit(normalize_url(report.source))
            # Separate ports but keep HTTP->HTTPS upgrades in the same project.
            host = parts.hostname + (f":{parts.port}" if parts.port else "")
            return "url:" + host, host
        path = Path(report.source).resolve()
        return "files:" + os.path.normcase(str(path)), path.name or str(path)

    def save(self, report):
        identity, name = self.project_identity(report)
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO projects(identity,name,source,mode) VALUES(?,?,?,?)", (identity, name, report.source, report.mode))
            project_id = self.db.execute("SELECT id FROM projects WHERE identity=?", (identity,)).fetchone()[0]
            self.db.execute("UPDATE projects SET source=?,mode=? WHERE id=?", (report.source, report.mode, project_id))
            audit_id = self.db.execute("INSERT INTO audits(project_id,created,report) VALUES(?,?,?)", (project_id, report.created, json.dumps(report.to_dict(), ensure_ascii=False))).lastrowid
            # Manual 'resolved' does not hide a problem that a later audit finds again.
            for key in issues(report):
                self.db.execute("UPDATE issue_states SET state='Otevřené',audit_id=?,updated=? WHERE project_id=? AND issue_key=? AND state='Vyřešené'", (audit_id, report.created, project_id, key))
            self.record_audit_states(audit_id, self.states(project_id))
        return project_id, audit_id

    def projects(self):
        return self.db.execute("SELECT p.*,COUNT(a.id) AS audit_count,MAX(a.created) AS last_audit FROM projects p LEFT JOIN audits a ON a.project_id=p.id GROUP BY p.id ORDER BY MAX(a.id) DESC").fetchall()

    def audits(self, project_id):
        return self.db.execute("SELECT id,created FROM audits WHERE project_id=? ORDER BY id DESC", (project_id,)).fetchall()

    def load(self, audit_id):
        row = self.db.execute("SELECT * FROM audits WHERE id=?", (audit_id,)).fetchone()
        if row is None:
            raise ValueError("Uložená kontrola nebyla nalezena.")
        return row["project_id"], Report.from_dict(json.loads(row["report"]))

    def previous(self, audit_id):
        row = self.db.execute("SELECT older.id FROM audits older JOIN audits current ON current.project_id=older.project_id WHERE current.id=? AND older.id<current.id ORDER BY older.id DESC LIMIT 1", (audit_id,)).fetchone()
        return self.load(row[0])[1] if row else None

    def states(self, project_id):
        return {row["issue_key"]: row["state"] for row in self.db.execute("SELECT issue_key,state FROM issue_states WHERE project_id=?", (project_id,))}

    def set_states(self, project_id, audit_id, keys, state):
        if state not in WORK_STATES:
            raise ValueError("Neplatný stav úkolu.")
        actual_project, report = self.load(audit_id)
        if actual_project != project_id:
            raise ValueError("Kontrola nepatří do zvoleného projektu.")
        valid = issues(report)
        if any(key not in valid for key in keys):
            raise ValueError("Nález není součástí této kontroly.")
        updated = datetime.now().astimezone().isoformat(timespec="seconds")
        with self.db:
            for key in keys:
                self.db.execute("INSERT INTO issue_states VALUES(?,?,?,?,?) ON CONFLICT(project_id,issue_key) DO UPDATE SET state=excluded.state,updated=excluded.updated,audit_id=excluded.audit_id", (project_id, key, state, updated, audit_id))
            self.record_audit_states(audit_id, self.states(project_id))

    def record_audit_states(self, audit_id, states):
        self.db.execute('INSERT INTO audit_work_states VALUES(?,?,?) ON CONFLICT(audit_id) DO UPDATE SET updated=excluded.updated,payload=excluded.payload',
                        (audit_id, datetime.now().astimezone().isoformat(timespec='seconds'), json.dumps(states, ensure_ascii=False)))

    def audit_states(self, audit_id):
        row = self.db.execute('SELECT updated,payload FROM audit_work_states WHERE audit_id=?', (audit_id,)).fetchone()
        return {'updated': row['updated'], 'states': json.loads(row['payload'])} if row else None

    def save_draft(self, payload):
        with self.db:
            self.db.execute('INSERT INTO audit_draft VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET updated=excluded.updated,payload=excluded.payload',
                            (datetime.now().astimezone().isoformat(timespec='seconds'), json.dumps(payload, ensure_ascii=False)))

    def draft(self):
        row = self.db.execute('SELECT payload FROM audit_draft WHERE id=1').fetchone()
        return json.loads(row['payload']) if row else None

    def clear_draft(self):
        with self.db:
            self.db.execute('DELETE FROM audit_draft WHERE id=1')

    def speed_history(self, project_id):
        rows = self.db.execute('SELECT m.created,m.payload FROM measurements m JOIN audits a ON a.id=m.audit_id WHERE a.project_id=? AND m.kind LIKE ? ORDER BY m.id DESC LIMIT 200',
                               (project_id, 'pagespeed:%')).fetchall()
        return [json.loads(row['payload']) for row in reversed(rows)]

    def rename(self, project_id, name):
        name = name.strip()
        if not name:
            raise ValueError("Název projektu nesmí být prázdný.")
        with self.db:
            self.db.execute("UPDATE projects SET name=? WHERE id=?", (name, project_id))

    def close(self):
        self.db.close()

    def save_measurement(self, audit_id, kind, payload):
        self.load(audit_id)
        with self.db:
            self.db.execute('INSERT INTO measurements(audit_id,kind,created,payload) VALUES(?,?,?,?)',
                            (audit_id, kind, datetime.now().astimezone().isoformat(timespec='seconds'), json.dumps(payload, ensure_ascii=False)))

    def measurements(self, audit_id):
        latest = {}
        for row in self.db.execute('SELECT kind,created,payload FROM measurements WHERE audit_id=? ORDER BY id', (audit_id,)):
            latest[row['kind']] = {'kind': row['kind'], 'saved': row['created'], 'data': json.loads(row['payload'])}
        return list(latest.values())

    def save_repair_check(self, audit_id, payload):
        _, report = self.load(audit_id)
        valid = issues(report)
        if not payload.get('results') or any(row['key'] not in valid for row in payload['results']):
            raise ValueError('Ověřovaný nález není součástí původního auditu.')
        with self.db:
            self.db.execute('INSERT INTO repair_checks(audit_id,created,payload) VALUES(?,?,?)',
                            (audit_id, payload['created'], json.dumps(payload, ensure_ascii=False)))

    def repair_checks(self, audit_id):
        latest = {}
        for row in self.db.execute('SELECT created,payload FROM repair_checks WHERE audit_id=? ORDER BY id DESC', (audit_id,)):
            payload = json.loads(row['payload'])
            for result in payload['results']:
                latest.setdefault(result['key'], dict(result, created=row['created']))
        return latest
