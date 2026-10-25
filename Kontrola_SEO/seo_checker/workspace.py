"""Repair-plan and project-history windows using the existing desktop theme."""
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from datetime import datetime

from .dpi import work_area
from .planning import WORK_STATES, build_plan, compare_reports, comparison_scope, issue_key
from .repairs import repair_instructions
from .evolution import search_snapshot, traffic_text
from .theme import BG, INK, MUTED, SURFACE, SOFT, ACCENT, ACCENT_SOFT, STATUS_COLORS, readable


def window(app, title):
    win = tk.Toplevel(app.root)
    win.dpi_scale = app.root.dpi_scale
    win.title(title + " · Kontrola SEO")
    width, height = work_area(app.root)
    win.geometry(f"{min(app.px(1150), width-30)}x{min(app.px(740), height-60)}")
    win.minsize(min(app.px(850), width-30), min(app.px(640), height-60))
    win.configure(bg=BG)
    win.columnconfigure(0, weight=1)
    win.rowconfigure(1, weight=1)
    bar = ttk.Frame(win, padding=app.px((20, 10)))
    bar.grid(row=0, column=0, sticky='ew')
    win.back_button = ttk.Button(bar, text='←  Zpět na přehled', style='Quiet.TButton', command=lambda: win.event_generate('<<BackToOverview>>'))
    win.back_button.pack(side='left')
    ttk.Label(bar, text='Kontrola SEO  /  ' + title, foreground=MUTED).pack(side='right')
    win.bind('<<BackToOverview>>', lambda event: win.destroy())
    win.bind('<Escape>', lambda event: win.event_generate('<<BackToOverview>>'))
    win.bind('<Destroy>', lambda event: app.main_section.set(0)
             if event.widget is win and not app.closing else None, add='+')
    frame = ttk.Frame(win, style='Canvas.TFrame', padding=app.px(20))
    frame.grid(row=1, column=0, sticky="nsew")
    return win, frame


def table(parent, columns, heights=7):
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings", selectmode="browse", height=heights)
    for key, label, width in columns:
        tree.heading(key, text=label, anchor="w")
        tree.column(key, width=width, minwidth=50, anchor="w")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)
    tree.grid(row=0, column=0, sticky='nsew')
    scrollbar = ttk.Scrollbar(frame, command=tree.yview)
    scrollbar.grid(row=0, column=1, sticky='ns')
    tree.configure(yscrollcommand=scrollbar.set)
    horizontal = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
    horizontal.grid(row=1, column=0, sticky='ew')
    def horizontal_view(first, last):
        horizontal.set(first, last)
        if float(first) <= 0 and float(last) >= 1:
            horizontal.grid_remove()
        else:
            horizontal.grid()
    tree.configure(xscrollcommand=horizontal_view)
    tree.tag_configure('alternate', background=SOFT)
    for tag, color in [('P1', '#d1343a'), ('P2', '#b4690e'), ('P3', MUTED), ('Odstraněné', ACCENT), ('Nové', '#d1343a')]:
        tree.tag_configure(tag, foreground=color)
    return frame, tree


def text_area(parent, height=7):
    frame = ttk.Frame(parent)
    scale = getattr(parent.winfo_toplevel(), 'dpi_scale', 1)
    text = tk.Text(frame, height=height, width=1, wrap="word", font=("Segoe UI", 10), bg=SOFT, fg=INK, relief="flat", padx=round(14*scale), pady=round(12*scale), spacing3=round(4*scale), borderwidth=0, highlightthickness=0)
    text.pack(side="left", fill="both", expand=True)
    scroll = ttk.Scrollbar(frame, command=text.yview)
    scroll.pack(side="right", fill="y")
    text.configure(yscrollcommand=scroll.set, state="disabled")
    text.tag_configure('lead', font=('Segoe UI Semibold', 12), spacing3=round(10*scale))
    text.tag_configure('advice', foreground=ACCENT)
    return frame, text


def fill_text(widget, value):
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.insert("end", readable(value))
    widget.tag_add('lead', '1.0', '1.end')
    for index, line in enumerate(readable(value).splitlines(), 1):
        if line.startswith(('Proč priorita', 'Příklad opravy', 'Postup a ověření', 'Nálezy a podklady')):
            widget.tag_add('lead', f'{index}.0', f'{index}.end')
        if line.startswith(('Oprava:', 'Doporučený krok', 'DOPORUČENÍ')):
            widget.tag_add('advice', f'{index}.0', f'{index}.end')
    widget.configure(state="disabled")


def date_label(value):
    try:
        return datetime.fromisoformat(value).strftime("%d. %m. %Y %H:%M:%S")
    except ValueError:
        return value


class PlanWindow:
    def __init__(self, app):
        self.app = app
        self.report = app.report
        self.project_id, self.audit_id = app.project_id, app.audit_id
        self.win, body = window(app, "Plán oprav")
        self.recheck_busy = False
        self.latest_checks = app.store.repair_checks(self.audit_id) if app.store and self.audit_id else {}
        self.win.bind('<Destroy>', self.on_destroy, add='+')
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)
        ttk.Label(body, text="Plán oprav", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.plan_summary = ttk.Label(body, text="Vyberte problém. Vpravo najdete doporučení a stav práce.", style="Canvas.TLabel")
        self.plan_summary.grid(row=1, column=0, sticky="ew", pady=app.px((4, 16)))
        panes = ttk.Panedwindow(body, orient='horizontal')
        panes.grid(row=2, column=0, sticky='nsew')
        left = ttk.Frame(panes, padding=app.px(14))
        right = ttk.Frame(panes, padding=app.px(16))
        panes.add(left, weight=1)
        panes.add(right, weight=1)
        panes.bind('<Map>', lambda event: panes.sashpos(0, panes.winfo_width() // 2))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        ttk.Label(left, text='P1  Nejdříve     P2  Potom     P3  Další zlepšení', foreground=MUTED).grid(row=0, column=0, sticky='w', pady=app.px((0, 12)))
        frame, self.tree = table(left, [("priority", "Priorita", app.px(65)), ("name", "Problém", app.px(235)), ("pages", "Stránek", app.px(65)), ('traffic', 'Prokliky / zobrazení', app.px(145)), ("state", "Stav práce", app.px(140))], 8)
        for column, minimum in [('priority', 65), ('name', 150), ('pages', 65), ('traffic', 145), ('state', 110)]:
            self.tree.column(column, minwidth=app.px(minimum))
        frame.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.select)
        verify_actions = ttk.Frame(left)
        verify_actions.grid(row=2, column=0, sticky='ew', pady=app.px((12, 6)))
        self.verify_button = ttk.Button(verify_actions, text='Ověřit dotčené stránky', style='Primary.TButton', command=self.recheck)
        self.verify_button.pack(side='left')
        self.verify_stop = ttk.Button(verify_actions, text='Zastavit', command=self.stop_recheck, state='disabled')
        self.verify_stop.pack(side='right')
        self.recheck_status = ttk.Label(left, text='Vyberte skupinu nebo jednotlivý nález. Ověření nepřepisuje původní audit.', foreground=MUTED, wraplength=app.px(420))
        self.recheck_status.grid(row=3, column=0, sticky='ew')
        left.bind('<Configure>', lambda event: self.recheck_status.configure(wraplength=max(180, event.width-app.px(28))))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        self.task_title = ttk.Label(right, text='Vyberte problém', style='Section.TLabel', wraplength=app.px(330))
        self.task_title.grid(row=0, column=0, sticky='ew', pady=app.px((0, 8)))
        self.task_meta = ttk.Label(right, foreground=MUTED, wraplength=app.px(330))
        self.task_meta.grid(row=1, column=0, sticky='ew', pady=app.px((0, 12)))
        right.bind('<Configure>', lambda event: [label.configure(wraplength=max(180, event.width-app.px(32))) for label in (self.task_title, self.task_meta)])
        detail_panel = ttk.Frame(right)
        detail_panel.grid(row=2, column=0, sticky='nsew')
        detail_panel.columnconfigure(0, weight=1)
        detail_panel.rowconfigure(1, weight=1)
        navigation = ttk.Frame(detail_panel)
        navigation.grid(row=0, column=0, sticky='w', pady=app.px((0, 8)))
        self.repair_tabs = ttk.Notebook(detail_panel, style='Flat.TNotebook')
        self.repair_tabs.grid(row=1, column=0, sticky='nsew')
        self.repair_tab = tk.IntVar(value=0)
        for index, label in enumerate(('Postup opravy', 'Výsledek ověření')):
            ttk.Radiobutton(navigation, text=label, variable=self.repair_tab, value=index,
                            style='Segment.TRadiobutton', command=lambda i=index: self.repair_tabs.select(i)).pack(side='left')
        frame, self.detail = text_area(self.repair_tabs, 7)
        self.repair_tabs.add(frame, text='Postup opravy')
        frame, self.verification_detail = text_area(self.repair_tabs, 7)
        self.repair_tabs.add(frame, text='Výsledek ověření')
        self.repair_tabs.bind('<<NotebookTabChanged>>', lambda event: self.repair_tab.set(self.repair_tabs.index(self.repair_tabs.select())))
        ttk.Label(right, text='Výběr nálezů pro stav i ověření', foreground=MUTED).grid(row=3, column=0, sticky='w', pady=app.px((14, 5)))
        self.selection = tk.StringVar(value="")
        self.occurrence = ttk.Combobox(right, textvariable=self.selection, state="readonly", width=20)
        self.occurrence.grid(row=4, column=0, sticky="ew")
        self.occurrence.bind('<<ComboboxSelected>>', self.select_occurrence)
        actions = ttk.Frame(right)
        actions.grid(row=5, column=0, sticky="ew", pady=app.px((8, 0)))
        self.state = tk.StringVar(value=WORK_STATES[0])
        ttk.Combobox(actions, textvariable=self.state, values=WORK_STATES, state="readonly", width=12).pack(side="left", fill='x', expand=True)
        self.save_button = ttk.Button(actions, text="Uložit stav", style='Primary.TButton', command=self.save)
        self.save_button.pack(side="left", padx=app.px((8, 0)))
        self.notice = ttk.Label(body, text="Priority platí pro skupinu podle nejzávažnějšího nálezu. Ruční stav a výsledek ověření se zobrazují odděleně.", style='Canvas.TLabel', wraplength=app.px(1000))
        self.notice.grid(row=3, column=0, sticky="ew", pady=app.px((12, 0)))
        self.refresh()

    def refresh(self):
        selected = self.tree.selection()
        code = self.tasks[int(selected[0])].code if selected and hasattr(self, "tasks") else None
        states = self.app.store.states(self.project_id) if self.app.store and self.project_id else {}
        measurements = self.app.store.measurements(self.audit_id) if self.app.store and self.audit_id else []
        self.tasks = build_plan(self.report, states, search_snapshot(measurements))
        self.tree.delete(*self.tree.get_children())
        chosen = "0"
        for index, task in enumerate(self.tasks):
            traffic = f"{task.traffic['clicks']:,.0f} / {task.traffic['impressions']:,.0f}" if task.traffic and task.traffic['matched'] else 'Bez dat'
            self.tree.insert("", "end", iid=str(index), values=(f"P{task.priority}", task.name, len(task.pages), traffic, task.state_summary), tags=(f'P{task.priority}', 'alternate' if index % 2 else 'plain'))
            if task.code == code:
                chosen = str(index)
        latest = self.app.store.audits(self.project_id)[0]["id"] if self.app.store and self.project_id else None
        self.save_button.configure(state="normal" if self.tasks and latest == self.audit_id and not self.recheck_busy else "disabled")
        self.verify_button.configure(state='normal' if self.tasks and self.audit_id and not self.recheck_busy else 'disabled')
        self.plan_summary.configure(text=f'{len(self.tasks)} skupin · P1–P3 podle závažnosti; uvnitř priority rozhodují prokliky a zobrazení, pak počet stránek.')
        if latest != self.audit_id:
            self.notice.configure(text="Stavy lze měnit u nejnovější uložené kontroly projektu. Tato kontrola je historická nebo neuložená.")
        if self.tasks:
            self.tree.selection_set(chosen)
            self.select()
        else:
            self.task_title.configure(text='Žádné opravy k naplánování')
            fill_text(self.detail, "V tomto auditu nebyly nalezeny chyby ani doporučení. Neověřené kontroly najdete v hlavním okně.")

    def select(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        task = self.tasks[int(selected[0])]
        labels = [f"Celá skupina ({len(task.occurrences)} nálezů)"]
        labels.extend(f"{index+1}. {page.location}" + (f" → {finding.target}" if finding.target else "") for index, (page, finding) in enumerate(task.occurrences))
        self.occurrence.configure(values=labels)
        self.occurrence.current(0)
        self.task_title.configure(text=task.name)
        self.task_meta.configure(text=f'P{task.priority} · Dotčených stránek: {len(task.pages)}\nNáročnost: {task.effort} (odhad)')
        if task.traffic and task.traffic['matched']:
            self.task_meta.configure(text=self.task_meta.cget('text') +
                f"\nSearch Console: {task.traffic['clicks']:,.0f} prokliků / {task.traffic['impressions']:,.0f} zobrazení\n"
                f"Období: {task.traffic['start']} až {task.traffic['end']}")
        self.select_occurrence()

    def select_occurrence(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        task = self.tasks[int(selected[0])]
        index = self.occurrence.current()
        if index > 0:
            page, finding = task.occurrences[index-1]
            text = repair_instructions(task, page) + '\n\nNález: ' + page.location + '\n\n' + finding.detail + '\n\nOprava: ' + finding.advice
            text += '\n\nNávštěvnost celé skupiny\n' + traffic_text(task.traffic)
            if page.inbound:
                text += '\n\nOdkazuje sem:\n' + '\n'.join(page.inbound)
            occurrences = [(page, finding)]
        else:
            text = task.description()
            occurrences = task.occurrences
        fill_text(self.detail, text)
        states = {task.states.get(issue_key(page, finding), 'Otevřené') for page, finding in occurrences}
        self.state.set(next(iter(states)) if len(states) == 1 else 'Otevřené')
        self.verify_button.configure(text=f'Ověřit stránky ({len({p.location for p, f in occurrences})})')
        self.show_verification()

    def selected_occurrences(self):
        selected = self.tree.selection()
        if not selected:
            return []
        task = self.tasks[int(selected[0])]
        index = self.occurrence.current()
        return [task.occurrences[index-1]] if index > 0 else list(task.occurrences)

    def show_verification(self):
        occurrences = self.selected_occurrences()
        rows = [(page, finding, self.latest_checks.get(issue_key(page, finding))) for page, finding in occurrences]
        counts = {state: sum(bool(row) and row['status'] == state for _, _, row in rows)
                  for state in ('Opraveno', 'Přetrvává', 'Neověřeno')}
        untested = sum(row is None for _, _, row in rows)
        lines = ['Ověření původních nálezů',
                 ' · '.join(f'{state}: {count}' for state, count in counts.items()) + f' · Zatím neověřeno: {untested}',
                 '\nVýsledek platí k uvedenému času. Nejde o nový audit celého webu. Ruční stav práce se nemění.']
        for page, finding, row in rows:
            lines.extend(['', page.location, finding.name])
            if row:
                lines.extend([row['status'] + ' · ' + date_label(row['created']), row['detail'], *row.get('evidence', [])])
            else:
                lines.append('Zatím neověřeno. Po nasazení opravy klikněte na Ověřit stránky.')
        fill_text(self.verification_detail, '\n'.join(lines))

    def recheck(self):
        if self.app.running:
            self.recheck_status.configure(text='Nejprve dokončete nebo zastavte probíhající kontrolu.')
            return
        occurrences = self.selected_occurrences()
        if not occurrences:
            return
        try:
            if not self.app.start_recheck(self, occurrences):
                return
            self.recheck_busy = True
            self.verify_button.configure(state='disabled')
            self.save_button.configure(state='disabled')
            self.verify_stop.configure(state='normal')
            self.recheck_status.configure(text='Ověřuji vybrané stránky. Původní audit zůstává v přehledu.')
            self.repair_tabs.select(1)
        except Exception as exc:
            self.recheck_status.configure(text=str(exc))

    def stop_recheck(self):
        if self.app.recheck_view is self:
            self.app.stop()
            self.verify_stop.configure(state='disabled')
            self.recheck_status.configure(text='Zastavuji ověření; čekám na dokončení požadavku.')

    def recheck_finished(self, data, message):
        self.recheck_busy = False
        self.verify_stop.configure(state='disabled')
        self.verify_button.configure(state='normal' if self.tasks else 'disabled')
        latest = self.app.store.audits(self.project_id)[0]['id'] if self.app.store and self.project_id else None
        self.save_button.configure(state='normal' if self.tasks and latest == self.audit_id else 'disabled')
        if data:
            self.latest_checks = self.app.store.repair_checks(self.audit_id)
        self.recheck_status.configure(text=message)
        self.show_verification()
        if not data:
            previous = self.verification_detail.get('1.0', 'end').strip()
            fill_text(self.verification_detail, message + '\n\nNíže jsou předchozí uložené výsledky, nikoli výsledek tohoto pokusu.\n\n' + previous)

    def on_destroy(self, event):
        if event.widget is self.win and self.app.recheck_view is self:
            self.app.cancel.set()

    def save(self):
        selected = self.tree.selection()
        if not selected or not self.app.store:
            return
        task = self.tasks[int(selected[0])]
        index = self.occurrence.current()
        occurrences = task.occurrences if index <= 0 else [task.occurrences[index-1]]
        try:
            latest = self.app.store.audits(self.project_id)[0]["id"]
            if latest != self.audit_id:
                raise ValueError("Mezitím vznikl nový audit. Otevřete plán oprav z nejnovější kontroly.")
            self.app.store.set_states(self.project_id, self.audit_id, [issue_key(p, f) for p, f in occurrences], self.state.get())
            self.notice.configure(text=f"Uloženo: {self.state.get()} · {len(occurrences)} nálezů. Záměrné nálezy zůstávají součástí technického auditu.")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Stav se nepodařilo uložit", str(exc), parent=self.win)


class HistoryWindow:
    def __init__(self, app):
        self.app = app
        self.win, body = window(app, "Projekty a historie")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)
        ttk.Label(body, text="Projekty a historie", style='Title.TLabel').grid(row=0, column=0, sticky="w")
        ttk.Label(body, text='Kontrolujte vývoj webu a porovnávejte jednotlivé audity.', style='Canvas.TLabel').grid(row=1, column=0, sticky='w', pady=app.px((4, 14)))
        content = ttk.Frame(body, style='Canvas.TFrame')
        content.grid(row=2, column=0, sticky='nsew')
        content.columnconfigure(0, weight=0, minsize=app.px(210))
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)
        left = tk.Frame(content, background=SURFACE, padx=app.px(14), pady=app.px(14))
        left.grid(row=0, column=0, sticky="nsew", padx=app.px((0, 12)))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        ttk.Label(left, text='Projekty', style='Section.TLabel').grid(row=0, column=0, sticky='w', pady=app.px((0, 10)))
        frame, self.projects = table(left, [("name", "Web", app.px(145)), ("count", "Auditů", app.px(58))], 12)
        frame.grid(row=1, column=0, sticky="nsew")
        ttk.Button(left, text="Přejmenovat projekt", style='Quiet.TButton', command=self.rename).grid(row=2, column=0, sticky="ew", pady=app.px((12, 0)))
        self.projects.bind("<<TreeviewSelect>>", self.select_project)
        right = tk.Frame(content, background=SURFACE, padx=app.px(16), pady=app.px(14))
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(4, weight=1, minsize=app.px(170))
        audit_heading = ttk.Frame(right)
        audit_heading.grid(row=0, column=0, sticky='ew', pady=app.px((0, 8)))
        audit_heading.columnconfigure(0, weight=1)
        self.project_heading = ttk.Label(audit_heading, text='Vyberte projekt', style='Section.TLabel')
        self.project_heading.grid(row=0, column=0, sticky='w')
        self.audit_count = ttk.Label(audit_heading, text='', foreground=MUTED)
        self.audit_count.grid(row=0, column=1, sticky='e')
        ttk.Button(audit_heading, text='Vývoj webu', command=self.open_trends).grid(row=0, column=2, padx=app.px((8, 0)))
        selector = ttk.Frame(right)
        selector.grid(row=1, column=0, sticky='ew')
        selector.columnconfigure(1, weight=1)
        ttk.Label(selector, text='Kontrola', foreground=MUTED).grid(row=0, column=0, padx=app.px((0, 12)))
        self.audit_picker = ttk.Combobox(selector, state='readonly', width=23)
        self.audit_picker.grid(row=0, column=1, sticky='ew')
        self.audit_picker.bind('<<ComboboxSelected>>', self.select_audit)
        bar = ttk.Frame(right)
        bar.grid(row=2, column=0, sticky="ew", pady=app.px((9, 10)))
        self.open_button = ttk.Button(bar, text="Otevřít kontrolu", style='Primary.TButton', command=self.open_audit, state='disabled')
        self.open_button.pack(side="left")
        ttk.Label(bar, text="Porovnat s", foreground=MUTED).pack(side="left", padx=app.px((16, 8)))
        self.baseline = ttk.Combobox(bar, state="readonly", width=23)
        self.baseline.pack(side="left", fill="x", expand=True)
        self.baseline.bind("<<ComboboxSelected>>", self.compare)
        overview = ttk.Frame(right, padding=app.px((10, 8)), style='Summary.TFrame')
        overview.grid(row=3, column=0, sticky='ew', pady=app.px((0, 10)))
        overview.columnconfigure(0, weight=1)
        self.summary = ttk.Label(overview, text="Vyberte projekt a kontrolu.", style='Summary.TLabel', foreground=INK, wraplength=app.px(450))
        self.summary.grid(row=0, column=0, columnspan=5, sticky='ew')
        self.scope_notice = ttk.Label(overview, style='Summary.TLabel', wraplength=app.px(650))
        self.scope_notice.grid(row=1, column=0, columnspan=5, sticky='ew', pady=app.px((3, 6)))
        self.delta_counts = {}
        self.change_filter = tk.StringVar(value='Všechny změny')
        for column, (category, caption, color) in enumerate((('Nové', 'Nové', '#d1343a'), ('Odstraněné', 'Ověřené opravy', ACCENT), ('Přetrvávající', 'Přetrvávající', '#b4690e'), ('Neověřené', 'Neověřené', MUTED), ('Poprvé kontrolované', 'První ověření', MUTED))):
            overview.columnconfigure(column, weight=1, uniform='delta')
            metric = ttk.Frame(overview, padding=app.px((3, 3)), style='Summary.TFrame')
            metric.grid(row=2, column=column, sticky='ew')
            value = ttk.Label(metric, text='—', style='Summary.TLabel', foreground=color, font=('Segoe UI Semibold', 16))
            value.pack(anchor='w')
            label = ttk.Label(metric, text=caption, style='Summary.TLabel', foreground=MUTED, font=('Segoe UI', 9))
            label.pack(anchor='w')
            for widget in (metric, value, label):
                widget.configure(cursor='hand2')
                widget.bind('<Button-1>', lambda event, key=category: self.filter_changes(key))
            self.delta_counts[category] = value
        right.bind('<Configure>', lambda event: [label.configure(wraplength=max(app.px(250), event.width-app.px(54))) for label in (self.summary, self.scope_notice)])
        main = ttk.Frame(right)
        main.grid(row=4, column=0, sticky='nsew')
        main.columnconfigure(0, weight=3, minsize=app.px(240), uniform='comparison')
        main.columnconfigure(1, weight=2, minsize=app.px(180), uniform='comparison')
        main.rowconfigure(0, weight=1)
        changes_panel = ttk.Frame(main)
        changes_panel.grid(row=0, column=0, sticky='nsew', padx=app.px((0, 12)))
        changes_panel.columnconfigure(0, weight=1)
        changes_panel.rowconfigure(1, weight=1)
        filters = ttk.Frame(changes_panel)
        filters.grid(row=0, column=0, sticky='ew', pady=app.px((0, 6)))
        self.filter_box = ttk.Combobox(filters, textvariable=self.change_filter, state='readonly', width=22,
            values=['Všechny změny', 'Nové', 'Odstraněné', 'Přetrvávající', 'Neověřené', 'Poprvé kontrolované'])
        self.filter_box.pack(side='left')
        self.filter_box.bind('<<ComboboxSelected>>', lambda event: self.render_changes())
        ttk.Button(filters, text='Rozsah', style='Quiet.TButton', command=self.show_scope).pack(side='right')
        ttk.Button(filters, text='Stránka před a po', style='Quiet.TButton', command=self.compare_page).pack(side='right')
        frame, self.changes = table(changes_panel, [("change", "Změna", app.px(130)), ("name", "Nález", app.px(210)), ("page", "Stránka", app.px(270))], 8)
        frame.grid(row=1, column=0, sticky="nsew")
        self.changes.bind("<<TreeviewSelect>>", self.select_change)
        detail_panel = ttk.Frame(main, padding=app.px(12))
        detail_panel.grid(row=0, column=1, sticky='nsew')
        detail_panel.columnconfigure(0, weight=1)
        detail_panel.rowconfigure(1, weight=1)
        ttk.Label(detail_panel, text='Detail změny', style='Section.TLabel').grid(row=0, column=0, sticky='w', pady=app.px((0, 6)))
        frame, self.detail = text_area(detail_panel, 8)
        frame.grid(row=1, column=0, sticky='nsew')
        ttk.Label(body, text="Neověřené = poslední kontrola nepotvrdila, zda byl nález opraven.", style='Canvas.TLabel', wraplength=app.px(1000)).grid(row=3, column=0, sticky="ew", pady=app.px((10, 0)))
        self.load_projects()

    def load_projects(self):
        self.projects.delete(*self.projects.get_children())
        for project in self.app.store.projects():
            self.projects.insert("", "end", iid=str(project["id"]), values=(project["name"], project["audit_count"]))
        ids = self.projects.get_children()
        if ids:
            chosen = str(self.app.project_id) if str(self.app.project_id) in ids else ids[0]
            self.projects.selection_set(chosen)
            self.select_project()
        else:
            self.project_heading.configure(text='Zatím bez projektů')
            self.audit_count.configure(text='')
            self.audit_rows = []
            self.audit_picker.configure(values=[], state='disabled')
            self.audit_picker.set('')
            self.open_button.configure(state='disabled')
            self.baseline.configure(values=[''])
            self.baseline.set('')
            self.changes.delete(*self.changes.get_children())
            self.summary.configure(text='Spusťte první kontrolu webu a projekt se uloží automaticky.')
            for value in self.delta_counts.values():
                value.configure(text='—')
            fill_text(self.detail, 'Historie se zobrazí po první uložené kontrole.')

    def open_trends(self):
        from .evolution_ui import TrendsWindow
        if self.projects.selection():
            self.trends = TrendsWindow(self.app, int(self.projects.selection()[0]))

    def compare_page(self):
        from .evolution_ui import PageComparisonWindow
        if not getattr(self, 'report', None):
            return
        old = self.app.store.load(self.baselines[self.baseline.current()]['id'])[1] if self.baselines else None
        selection = self.changes.selection()
        url = self.change_rows[int(selection[0])][1].location if selection else None
        self.page_comparison = PageComparisonWindow(self.app, old, self.report, url)

    def select_project(self, event=None):
        selected = self.projects.selection()
        if not selected:
            return
        self.audit_rows = self.app.store.audits(int(selected[0]))
        project_name = self.projects.item(selected[0], 'values')[0]
        self.project_heading.configure(text=project_name)
        self.audit_count.configure(text=f'{len(self.audit_rows)} uložených kontrol')
        self.audit_picker.configure(values=[f"#{row['id']} · {date_label(row['created'])}" for row in self.audit_rows],
                                    state='readonly' if self.audit_rows else 'disabled')
        if self.audit_rows:
            self.audit_picker.current(0)
            self.select_audit()
        else:
            self.audit_picker.set('')
            self.audit_id = None
            self.report = None
            self.open_button.configure(state='disabled')
            self.baseline.configure(values=[''])
            self.baseline.set('')
            self.changes.delete(*self.changes.get_children())
            self.summary.configure(text='Pro tento projekt zatím nejsou uložené kontroly.')
            for value in self.delta_counts.values():
                value.configure(text='—')
            fill_text(self.detail, 'Spusťte kontrolu tohoto webu a její výsledek se uloží sem.')

    def select_audit(self, event=None):
        index = self.audit_picker.current()
        if index < 0 or not self.audit_rows:
            return
        self.audit_id = self.audit_rows[index]['id']
        self.open_button.configure(state='normal')
        self.project_id, self.report = self.app.store.load(self.audit_id)
        self.baselines = [row for row in self.audit_rows if row["id"] < self.audit_id]
        labels = [f"#{row['id']} · {date_label(row['created'])}" for row in self.baselines]
        self.baseline.configure(values=labels or ["První kontrola projektu"], state='readonly' if labels else 'disabled')
        self.baseline.current(0)
        self.compare()

    def compare(self, event=None):
        old = self.app.store.load(self.baselines[self.baseline.current()]["id"])[1] if self.baselines else None
        self.delta = compare_reports(old, self.report)
        self.scope = comparison_scope(old, self.report)
        counts = self.report.counts()
        previous = old.counts() if old else None
        self.summary.configure(text=(f"Chyby: {previous['Chyba']} → {counts['Chyba']} · Doporučení: {previous['Doporučení']} → {counts['Doporučení']}" if previous else
                                     f"Chyby: {counts['Chyba']} · Doporučení: {counts['Doporučení']}") + '\n' + self.scope['summary'])
        warnings = self.scope['warnings']
        self.scope_notice.configure(text=('⚠ Rozsah nebo způsob kontroly se liší. Pokles počtu nálezů sám o sobě neprokazuje opravu. Podrobnosti: Rozsah.' if warnings else
                                          'Ověřené opravy = dřívější problém byl znovu prověřen a nebyl nalezen.' if old else
                                          'Nálezy první kontroly nejsou nově vzniklé chyby.'), foreground='#b4690e' if warnings else MUTED)
        for category, value in self.delta.items():
            self.delta_counts[category].configure(text=str(len(value)))
        self.render_changes()

    def filter_changes(self, category):
        self.change_filter.set(category)
        self.render_changes()

    def render_changes(self):
        if not hasattr(self, 'delta'):
            return
        self.change_rows = []
        self.changes.delete(*self.changes.get_children())
        for category in ('Nové', 'Odstraněné', 'Přetrvávající', 'Neověřené', 'Poprvé kontrolované'):
            if self.change_filter.get() not in ('Všechny změny', category):
                continue
            occurrences = self.delta[category]
            for page, finding in occurrences:
                key = str(len(self.change_rows))
                self.change_rows.append((category, page, finding))
                self.changes.insert("", "end", iid=key, values=(category, finding.name, page.location), tags=(category, 'alternate' if int(key) % 2 else 'plain'))
        fill_text(self.detail, 'Vyberte změnu\nZobrazí se její vysvětlení a adresa stránky.' if self.change_rows else
                  'Žádné nálezy v tomto filtru\nVyberte Všechny změny pro celý přehled.')
        if self.change_rows:
            self.changes.selection_set('0')
            self.select_change()

    def show_scope(self):
        if not hasattr(self, 'scope'):
            return
        scope = self.scope
        lines = [scope['summary'], *scope['warnings'],
                 '\nOdstraněné znamená ověřenou opravu. Neověřené není potvrzení opravy.',
                 f'\nAktuální kontrola: {len(self.report.pages)} z {self.report.discovered} objevených URL; '
                 + ('dokončený zadaný rozsah.' if self.report.complete else 'částečný rozsah.')]
        for key, title in (('added', 'URL navíc'), ('omitted', 'URL z minulé kontroly, které nyní chybí')):
            lines.extend(['\n' + title + f' ({len(scope[key])})', *scope[key]])
        fill_text(self.detail, '\n'.join(lines))

    def select_change(self, event=None):
        selected = self.changes.selection()
        if selected:
            category, page, finding = self.change_rows[int(selected[0])]
            explanation = {'Odstraněné': 'Ověřená oprava: nová kontrola už tento problém nepotvrdila. Níže je původní nález.',
                           'Neověřené': 'Nález nyní nelze ověřit. Chybějící výsledek není důkaz opravy. Níže je původní nález.',
                           'Poprvé kontrolované': 'Chybí srovnatelné předchozí ověření. Problém mohl existovat už dříve.',
                           'Nové': 'Při minulém srovnatelném ověření tento problém nebyl nalezen.',
                           'Přetrvávající': 'Stejný problém byl nalezen v obou kontrolách.'}[category]
            fill_text(self.detail, f"{category} · {finding.name}\n{explanation}\n\n{page.location}\n\n{finding.detail}\n\n{finding.advice}")

    def open_audit(self):
        if self.audit_picker.current() < 0:
            return
        if self.app.running:
            messagebox.showinfo("Probíhá kontrola", "Nejprve dokončete nebo zastavte aktuální kontrolu.", parent=self.win)
            return
        self.app.load_audit(self.audit_id)
        self.win.destroy()

    def rename(self):
        selected = self.projects.selection()
        if not selected:
            return
        name = simpledialog.askstring("Název projektu", "Nový název:", parent=self.win, initialvalue=self.projects.item(selected[0], "values")[0])
        if name is not None:
            try:
                self.app.store.rename(int(selected[0]), name)
                self.load_projects()
            except Exception as exc:
                messagebox.showerror("Přejmenování selhalo", str(exc), parent=self.win)
