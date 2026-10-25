"""Stable issue identities, transparent priority rules and conservative audit comparison."""
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field

from .engine import Finding, Page, Report
from .repairs import recipe, repair_instructions
from .evolution import traffic_evidence, traffic_text

ISSUE_STATUSES = {"Chyba", "Doporučení"}
WORK_STATES = ("Otevřené", "Vyřešené", "Záměrné")


def issue_key(page, finding):
    raw = json.dumps([page.location, finding.rule, finding.target], ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issues(report):
    return {issue_key(page, finding): (page, finding)
            for page in report.pages for finding in page.findings if finding.status in ISSUE_STATUSES}


def priority(finding):
    if finding.rule in {"link.broken", "HTTP odpověď", "redirect.loop", "redirect.invalid", "redirect.limit", "canonical.target"} and finding.status == "Chyba":
        return 1, "Dostupnost nebo cesta k preferované stránce je narušená.", "Střední"
    if finding.rule in {"Pokyny k indexaci", "Průchod Googlebot podle robots.txt", "sitemap.indexability", "canonical.noindex", "Titulek stránky"}:
        return 2, "Ovlivňuje přístup vyhledávače nebo identifikaci stránky; nejprve ověřte záměr.", "Nízká až střední"
    if finding.status == "Chyba" or finding.rule in {"redirect.chain", "Duplicitní titulek", "Duplicitní meta popis", "Textový obsah"}:
        return 2, "Technický nebo obsahový problém vyžaduje posouzení a opravu.", "Střední"
    return 3, "Jde o doporučení ke zlepšení s nižší technickou naléhavostí.", "Nízká až střední"


@dataclass
class Task:
    code: str
    name: str
    priority: int
    reason: str
    effort: str
    occurrences: list = field(default_factory=list)
    states: dict = field(default_factory=dict)
    traffic: dict | None = None

    @property
    def pages(self):
        return sorted({p.location for p, f in self.occurrences})

    @property
    def state_summary(self):
        counts = defaultdict(int)
        for page, finding in self.occurrences:
            counts[self.states.get(issue_key(page, finding), "Otevřené")] += 1
        return ", ".join(f"{state}: {counts[state]}" for state in WORK_STATES if counts[state])

    def description(self):
        lines = [repair_instructions(self, self.occurrences[0][0] if self.occurrences else None),
                 '\nNávštěvnost a pořadí oprav', traffic_text(self.traffic),
                 '\nNálezy a podklady', f'{len(self.pages)} stránek · {len(self.occurrences)} nálezů', self.state_summary]
        if len(self.pages) >= 3:
            lines.append("Problém se opakuje na více stránkách. Prověřte společnou šablonu; společná příčina zatím není potvrzená.")
        for page, finding in self.occurrences:
            lines.extend(["", page.location, finding.detail])
            if finding.advice:
                lines.append("Oprava: " + finding.advice)
            if page.inbound:
                lines.append("Odkazuje sem:\n" + "\n".join(page.inbound))
            if page.sitemap_sources:
                lines.append("Sitemapy:\n" + "\n".join(page.sitemap_sources))
        return "\n".join(lines)


def build_plan(report, states=None, search=None):
    groups = {}
    for page, finding in issues(report).values():
        rank, reason, effort = priority(finding)
        reason = recipe(finding.rule)[0] + ' ' + reason
        key = finding.rule
        if key not in groups:
            groups[key] = Task(key, finding.name, rank, reason, effort, states=states or {})
        task = groups[key]
        if rank < task.priority:
            task.priority, task.reason, task.effort = rank, reason, effort
        task.occurrences.append((page, finding))
    for task in groups.values():
        task.traffic = traffic_evidence(report, [p for p, _ in task.occurrences], search)
    return sorted(groups.values(), key=lambda task: (task.priority,
                  -(task.traffic or {}).get('clicks', 0), -(task.traffic or {}).get('impressions', 0),
                  -len(task.pages), task.name))


def compare_reports(previous: Report | None, current: Report):
    categories = {name: [] for name in ("Nové", "Přetrvávající", "Odstraněné", "Neověřené", "Poprvé kontrolované")}
    if previous is None:
        categories["Poprvé kontrolované"] = list(issues(current).values())
        return categories
    before, after = issues(previous), issues(current)
    old_pages = {page.location: page for page in previous.pages}
    new_pages = {page.location: page for page in current.pages}
    for key, occurrence in after.items():
        page, finding = occurrence
        if key in before:
            category = "Přetrvávající"
        else:
            old_page = old_pages.get(page.location)
            category = "Nové" if old_page and finding.check_key in old_page.checked_rules else "Poprvé kontrolované"
            if old_page and old_page.html_checked:
                if finding.rule == "link.broken" and finding.target not in old_page.links:
                    category = "Nové"
                if finding.rule == "canonical.target" and finding.target != old_page.canonical:
                    category = "Nové"
            if old_page and (old_page.analysis_mode != page.analysis_mode or page.analysis_mode == 'render_failed'):
                category = 'Poprvé kontrolované'
        categories[category].append(occurrence)
    for key, occurrence in before.items():
        if key in after:
            continue
        page, finding = occurrence
        new_page = new_pages.get(page.location)
        confirmed = new_page is not None and finding.check_key in new_page.checked_rules
        if new_page and new_page.html_checked and new_page.links_complete and finding.rule == "link.broken" and finding.target not in new_page.links:
            confirmed = True  # The broken link was removed from the source HTML.
        if new_page and new_page.html_checked and finding.rule == "canonical.target" and new_page.canonical != finding.target:
            confirmed = True  # The old canonical target is no longer used.
        if finding.rule.startswith("Duplicitní"):
            confirmed = confirmed and current.complete and previous.complete and set(old_pages) <= set(new_pages)
        if new_page and any(f.check_key == finding.check_key and f.status == "Neověřeno" for f in new_page.findings):
            confirmed = False
        if new_page and (page.analysis_mode != new_page.analysis_mode or new_page.analysis_mode == 'render_failed'):
            confirmed = False
        categories["Odstraněné" if confirmed else "Neověřené"].append(occurrence)
    return categories


def comparison_scope(previous: Report | None, current: Report):
    """Describe coverage without mistaking a smaller crawl for an improvement."""
    new = {page.location: page for page in current.pages}
    old = {page.location: page for page in previous.pages} if previous else {}
    shared = old.keys() & new.keys()
    warnings = []
    if previous:
        if old.keys() != new.keys():
            warnings.append(f'Rozsah URL se liší: {len(new.keys() - old.keys())} navíc, '
                            f'{len(old.keys() - new.keys())} z minulé kontroly chybí.')
        if not previous.complete or not current.complete:
            warnings.append('Alespoň jedna kontrola je částečná.')
        modes = sum(old[url].analysis_mode != new[url].analysis_mode or
                    new[url].analysis_mode == 'render_failed' for url in shared)
        checks = sum(set(old[url].checked_rules) != set(new[url].checked_rules) for url in shared)
        if modes:
            warnings.append(f'U {modes} společných URL se liší vykreslení nebo selhal JavaScript.')
        if checks:
            warnings.append(f'U {checks} společných URL se liší dokončené kontroly.')
    return {
        'before': len(old), 'after': len(new), 'shared': len(shared),
        'added': sorted(new.keys() - old.keys()), 'omitted': sorted(old.keys() - new.keys()),
        'warnings': warnings,
        'summary': ('První kontrola: zatím není s čím porovnávat.' if previous is None else
                    f'Rozsah: {len(old)} → {len(new)} URL · Společných: {len(shared)}'),
    }
