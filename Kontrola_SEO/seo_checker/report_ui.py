"""Page inspection, audit summary and configurable report export."""
import tkinter as tk
import webbrowser
from tkinter import ttk, filedialog, messagebox

from .engine import STATUSES
from .export import PRESETS, SECTIONS, save_report
from .planning import compare_reports
from .reporting import audit_summary, summary_text, page_sections, browser_url
from .theme import MUTED, ACCENT_SOFT, INK
from .evolution import search_snapshot
from .workspace import window, table, text_area, fill_text


class PageWindow:
    def __init__(self, app, page=None):
        self.app, self.report = app, app.report
        self.win, body = window(app, 'Detail stránky')
        body.columnconfigure(0, weight=1)
        body.rowconfigure(3, weight=1)
        ttk.Label(body, text='Detail stránky', style='Title.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(body, text='Údaje z vybrané kontroly. Otevření detailu web znovu nestahuje.', style='Canvas.TLabel').grid(row=1, column=0, sticky='w', pady=app.px((4, 12)))
        row = ttk.Frame(body, style='Canvas.TFrame')
        row.grid(row=2, column=0, sticky='ew', pady=app.px((0, 12)))
        self.choice = ttk.Combobox(row, values=[p.location for p in self.report.pages], state='readonly')
        self.choice.pack(side='left', fill='x', expand=True)
        self.choice.bind('<<ComboboxSelected>>', self.select)
        self.open_button = ttk.Button(row, text='Otevřít v prohlížeči ↗', command=self.open_browser)
        self.open_button.pack(side='left', padx=app.px((8, 0)))
        ttk.Button(row, text='Před a po', command=self.compare_page).pack(side='left', padx=app.px((8, 0)))
        area = ttk.Frame(body, style='Canvas.TFrame')
        area.grid(row=3, column=0, sticky='nsew')
        area.columnconfigure(0, weight=1)
        area.rowconfigure(1, weight=1)
        navigation = ttk.Frame(area, style='Canvas.TFrame')
        navigation.grid(row=0, column=0, sticky='w', pady=app.px((0, 10)))
        tabs = self.tabs = ttk.Notebook(area, style='Flat.TNotebook')
        tabs.grid(row=1, column=0, sticky='nsew')
        self.tab_choice = tk.IntVar(value=0)
        for index, caption in enumerate(('Přehled', 'Nadpisy', 'Odkazy', 'Všechny nálezy')):
            ttk.Radiobutton(navigation, text=caption, variable=self.tab_choice, value=index, style='Segment.TRadiobutton', command=lambda i=index: tabs.select(i)).pack(side='left', padx=app.px((0, 5)))
        tabs.bind('<<NotebookTabChanged>>', lambda event: self.tab_choice.set(tabs.index(tabs.select())))
        self.fields = {}
        for name in ('Přehled', 'Nadpisy', 'Odkazy'):
            frame, text = text_area(tabs)
            tabs.add(frame, text=name)
            self.fields[name] = text
        findings = ttk.Frame(tabs, padding=app.px(10))
        tabs.add(findings, text='Všechny nálezy')
        findings.columnconfigure(0, weight=1)
        findings.rowconfigure(0, weight=3)
        findings.rowconfigure(1, weight=2)
        frame, self.tree = table(findings, [('status', 'Stav', app.px(120)), ('name', 'Kontrola', app.px(500))], 5)
        frame.grid(row=0, column=0, sticky='nsew')
        self.tree.bind('<<TreeviewSelect>>', self.select_finding)
        frame, self.detail = text_area(findings, 4)
        frame.grid(row=1, column=0, sticky='nsew', pady=app.px((10, 0)))
        if self.report.pages:
            self.choice.current(self.report.pages.index(page) if page in self.report.pages else 0)
            self.select()
        else:
            self.open_button.configure(state='disabled')
            fill_text(self.fields['Přehled'], 'Kontrola neobsahuje žádné zpracované stránky.')

    def select(self, event=None):
        self.page = self.report.pages[self.choice.current()]
        self.open_button.configure(state='normal' if self.report.mode == 'URL' and browser_url(self.page.location) else 'disabled')
        for name, text in page_sections(self.page, self.report.mode).items():
            fill_text(self.fields[name], text)
            widget = self.fields[name]
            widget.tag_configure('section', font=('Segoe UI Semibold', 11), foreground=INK)
            labels = ('Titulek', 'Meta popis', 'Canonical v HTML', 'Vyhodnocený cíl canonical', 'Indexovatelnost', 'HTTP', 'Přesměrování', 'Režim analýzy')
            for index, line in enumerate(text.splitlines(), 1):
                if line in labels:
                    widget.tag_add('section', f'{index}.0', f'{index}.end')
        self.tree.delete(*self.tree.get_children())
        self.findings = sorted(self.page.findings, key=lambda f: STATUSES.index(f.status))
        for index, finding in enumerate(self.findings):
            self.tree.insert('', 'end', iid=str(index), values=(finding.status, finding.name), tags=('alternate' if index % 2 else 'plain',))
        if self.findings:
            self.tree.selection_set('0')
            self.select_finding()
        else:
            fill_text(self.detail, 'U této stránky nejsou zaznamenané nálezy.')

    def select_finding(self, event=None):
        selection = self.tree.selection()
        if selection:
            finding = self.findings[int(selection[0])]
            fill_text(self.detail, f'{finding.status} · {finding.name}\n\n{finding.detail}\n\nDoporučený krok\n{finding.advice or "Bez dalšího doporučení."}')

    def compare_page(self):
        from .evolution_ui import PageComparisonWindow
        previous = self.app.store.previous(self.app.audit_id) if self.app.store and self.app.audit_id else None
        self.comparison = PageComparisonWindow(self.app, previous, self.report, self.choice.get())

    def open_browser(self):
        if self.report.mode == 'URL' and browser_url(self.page.location):
            webbrowser.open(self.page.location)


class SummaryWindow:
    def __init__(self, app):
        self.report = app.report
        self.win, body = window(app, 'Shrnutí auditu')
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)
        ttk.Label(body, text='Co kontrola zjistila', style='Title.TLabel').grid(row=0, column=0, sticky='w')
        summary = audit_summary(self.report)
        ttk.Label(body, text=summary['scope'], background=ACCENT_SOFT if self.report.complete else '#fff4e0', foreground=INK, padding=app.px(10)).grid(row=1, column=0, sticky='ew', pady=app.px(12))
        frame, self.detail = text_area(body)
        frame.grid(row=2, column=0, sticky='nsew')
        states = app.store.states(app.project_id) if app.store and app.project_id else {}
        measurements = app.store.measurements(app.audit_id) if app.store and app.audit_id else []
        fill_text(self.detail, summary_text(self.report, states, search_snapshot(measurements)))
        row = ttk.Frame(body, style='Canvas.TFrame')
        row.grid(row=3, column=0, sticky='ew', pady=app.px((12, 0)))
        ttk.Button(row, text='Otevřít plán oprav', style='Primary.TButton', command=app.open_plan).pack(side='left')
        ttk.Button(row, text='Prohlédnout stránky', command=app.open_pages).pack(side='left', padx=app.px(8))
        ttk.Button(row, text='Exportovat report', command=app.export).pack(side='right')


class ExportWindow:
    def __init__(self, app):
        self.app, self.report = app, app.report
        # Capture the chosen audit so another window cannot silently change the export.
        self.states = app.store.states(app.project_id) if app.store and app.project_id else {}
        self.previous = app.store.previous(app.audit_id) if app.store and app.audit_id else None
        self.measurements = app.store.measurements(app.audit_id) if app.store and app.audit_id else []
        self.win, body = window(app, 'Export reportu')
        body.columnconfigure(0, weight=1)
        ttk.Label(body, text='Report pro další práci', style='Title.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(body, text='Vyberte obsah. Rozsah kontroly a její omezení jsou vždy součástí reportu.', style='Canvas.TLabel').grid(row=1, column=0, sticky='w', pady=app.px((4, 16)))
        form = ttk.Frame(body, padding=app.px(18))
        form.grid(row=2, column=0, sticky='ew')
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text='Název reportu').grid(row=0, column=0, sticky='w', padx=app.px((0, 14)))
        self.title = tk.StringVar(value='Kontrola SEO')
        ttk.Entry(form, textvariable=self.title).grid(row=0, column=1, sticky='ew')
        ttk.Label(form, text='Předvolba').grid(row=1, column=0, sticky='w', pady=app.px(12))
        self.preset = ttk.Combobox(form, values=list(PRESETS), state='readonly')
        self.preset.grid(row=1, column=1, sticky='ew', pady=app.px(12))
        self.preset.set('Pro klienta')
        self.preset.bind('<<ComboboxSelected>>', self.apply_preset)
        self.sections = {}
        for index, (key, caption) in enumerate(SECTIONS.items(), 2):
            value = self.sections[key] = tk.BooleanVar(value=key in PRESETS['Pro klienta'])
            ttk.Checkbutton(form, text=caption, variable=value).grid(row=index, column=0, columnspan=2, sticky='w', pady=app.px(5))
        ttk.Label(form, text='Formát').grid(row=7, column=0, sticky='w', pady=app.px((14, 0)))
        self.format = ttk.Combobox(form, values=['HTML – report pro čtení a tisk do PDF', 'JSON – strukturovaná data'], state='readonly')
        self.format.current(0)
        self.format.grid(row=7, column=1, sticky='ew', pady=app.px((14, 0)))
        self.notice = ttk.Label(body, text='Měření Google mohou obsahovat neveřejné údaje a vyhledávací dotazy. Zařaďte je jen pro zamýšleného příjemce.', style='Canvas.TLabel', wraplength=app.px(800))
        self.notice.grid(row=3, column=0, sticky='ew', pady=app.px(12))
        self.save_button = ttk.Button(body, text='Uložit report…', style='Primary.TButton', command=self.save)
        self.save_button.grid(row=4, column=0, sticky='e')

    def apply_preset(self, event=None):
        for key, value in self.sections.items():
            value.set(key in PRESETS[self.preset.get()])

    def save(self):
        selected = {key for key, value in self.sections.items() if value.get()}
        if not selected:
            self.notice.configure(text='Vyberte alespoň jednu část reportu.')
            return
        extension = '.html' if self.format.current() == 0 else '.json'
        path = filedialog.asksaveasfilename(parent=self.win, title='Uložit SEO report', defaultextension=extension, initialfile='SEO-report'+extension,
                                          filetypes=[('HTML report', '*.html')] if extension == '.html' else [('JSON data', '*.json')])
        if not path:
            return
        try:
            comparison = compare_reports(self.previous, self.report) if self.previous else None
            save_report(self.report, path, states=self.states, comparison=comparison, measurements=self.measurements,
                        sections=selected, title=self.title.get().strip() or 'Kontrola SEO')
            self.app.status.set(f'Report uložen: {path}')
            self.win.destroy()
        except (OSError, ValueError) as exc:
            messagebox.showerror('Report se nepodařilo uložit', str(exc), parent=self.win)
