"""Asynchronous PageSpeed and Search Console workspace for a saved audit."""
import json
import queue
import threading
import time
import tkinter as tk
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from tkinter import filedialog, ttk

from .google_services import (SearchConsole, ServiceError, Vault, authorize, load_client,
                              match_findings, opportunity, pagespeed, property_contains, validate_dates)
from .reporting import browser_url
from .theme import MUTED, INK, ACCENT, ACCENT_SOFT, BG, SOFT, SURFACE
from .workspace import date_label, fill_text, table, text_area, window
from .diagnostics import diagnose, copy_diagnostic


class InsightsWindow:
    def __init__(self, app, vault=None):
        self.app, self.report, self.audit_id = app, app.report, app.audit_id
        self.vault = vault or Vault()
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.busy = False
        self.closed = False
        self.page_rows = []
        self.gsc = None
        self.controls = []
        self.google_verified = False
        self.api_check = None
        self.speed_check = None
        self.login_problem = False
        self.activity_after = None
        self.saved = app.store.measurements(self.audit_id) if app.store and self.audit_id else []
        self.win, body = window(app, 'Rychlost a Google')
        self.win.protocol('WM_DELETE_WINDOW', self.close)
        self.win.bind('<<BackToOverview>>', lambda event: self.close())
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)
        header = ttk.Frame(body, style='Canvas.TFrame')
        header.grid(row=0, column=0, sticky='ew', pady=app.px((0, 14)))
        ttk.Label(header, text='Rychlost a Google', style='Title.TLabel').pack(side='left')
        ttk.Label(header, text=f'Kontrola #{self.audit_id}' if self.audit_id else 'Search Console · samostatné zobrazení', style='Canvas.TLabel').pack(side='right')
        indicators = ttk.Frame(body, style='Canvas.TFrame')
        indicators.grid(row=1, column=0, sticky='ew', pady=app.px((0, 12)))
        self.indicators = {}
        for column, (key, caption) in enumerate((('account', 'GOOGLE ÚČET'), ('search', 'SEARCH CONSOLE'), ('speed', 'PAGESPEED'))):
            indicators.columnconfigure(column, weight=1, uniform='services')
            card = ttk.Frame(indicators, padding=app.px((12, 9)))
            card.grid(row=0, column=column, sticky='nsew', padx=app.px((0, 8 if column < 2 else 0)))
            ttk.Label(card, text=caption, foreground=MUTED, font=('Segoe UI Semibold', 8)).pack(anchor='w')
            title = ttk.Label(card, font=('Segoe UI Semibold', 11))
            title.pack(anchor='w', pady=app.px((3, 2)))
            copy = ttk.Label(card, foreground=MUTED, font=('Segoe UI', 9), wraplength=app.px(280))
            copy.pack(anchor='w', fill='x')
            card.bind('<Configure>', lambda event, label=copy: label.configure(wraplength=max(100, event.width-app.px(24))))
            self.indicators[key] = (title, copy)
        tab_area = ttk.Frame(body, style='Canvas.TFrame')
        tab_area.grid(row=2, column=0, sticky='nsew')
        tab_area.columnconfigure(0, weight=1)
        tab_area.rowconfigure(2, weight=1)
        navigation = ttk.Frame(tab_area, style='Canvas.TFrame')
        navigation.grid(row=0, column=0, sticky='w', pady=app.px((0, 12)))
        tabs = self.tabs = ttk.Notebook(tab_area, style='Flat.TNotebook')
        tabs.grid(row=2, column=0, sticky='nsew')
        self.tab_choice = tk.IntVar(value=0)
        for index, caption in enumerate(('Rychlost webu', 'Search Console', 'Připojení služeb')):
            ttk.Radiobutton(navigation, text=caption, variable=self.tab_choice, value=index, style='Segment.TRadiobutton', command=lambda i=index: tabs.select(i)).pack(side='left', padx=app.px((0, 6)))
        tabs.bind('<<NotebookTabChanged>>', lambda event: self.tab_choice.set(tabs.index(tabs.select())))
        self.error_box = ttk.Frame(tab_area, padding=app.px(12))
        self.error_box.grid(row=1, column=0, sticky='ew', pady=app.px((0, 10)))
        self.error_box.columnconfigure(0, weight=1)
        self.error_text = ttk.Label(self.error_box, foreground='#c42b31', wraplength=app.px(850), justify='left')
        self.error_text.grid(row=0, column=0, sticky='ew')
        self.error_box.bind('<Configure>', lambda event: self.error_text.configure(wraplength=max(200, event.width-app.px(24))))
        actions = ttk.Frame(self.error_box)
        actions.grid(row=1, column=0, sticky='w', pady=app.px((8, 0)))
        self.error_settings = ttk.Button(actions, text='Nastavit připojení', command=lambda: self.show_settings('search'))
        self.error_settings.pack(side='left')
        self.error_browser = ttk.Button(actions, text='PageSpeed v prohlížeči ↗', command=self.open_speed_browser)
        self.error_browser.pack(side='left', padx=app.px(8))
        ttk.Button(actions, text='Zavřít hlášení', style='Quiet.TButton', command=self.error_box.grid_remove).pack(side='left')
        ttk.Button(actions, text='Kopírovat diagnostiku', style='Quiet.TButton',
                   command=lambda: copy_diagnostic(self.win, getattr(self, 'last_diagnostic', None))).pack(side='left')
        self.error_box.grid_remove()
        speed = ttk.Frame(tabs, padding=app.px(16))
        search = ttk.Frame(tabs, padding=app.px(16))
        settings = ttk.Frame(tabs, padding=app.px(16))
        tabs.add(speed, text='PageSpeed')
        tabs.add(search, text='Search Console')
        tabs.add(settings, text='Připojení')
        self.build_speed(speed)
        self.build_search(search)
        self.build_settings(self.scrollable_settings(settings))
        self.status = tk.StringVar(value='Vyberte měření. Výsledky se ukládají k otevřenému auditu.')
        ttk.Label(body, textvariable=self.status, style='Canvas.TLabel', wraplength=app.px(1040)).grid(row=3, column=0, sticky='ew', pady=app.px((10, 0)))
        activity = ttk.Frame(body, style='Canvas.TFrame')
        activity.grid(row=4, column=0, sticky='ew', pady=app.px((6, 0)))
        activity.columnconfigure(0, weight=1)
        self.activity = ttk.Label(activity, text='● Připraveno', style='Canvas.TLabel', font=('Segoe UI Semibold', 10))
        self.activity.grid(row=0, column=0, sticky='w')
        self.button(activity, 'Ověřit Search Console', self.fetch_sites).grid(row=0, column=1, sticky='e')
        self.loading = ttk.Progressbar(body, mode='indeterminate')
        self.loading.grid(row=5, column=0, sticky='ew', pady=app.px(6))
        self.loading.grid_remove()
        self.stop_button = ttk.Button(body, text='Zastavit načítání', command=self.stop, state='disabled')
        self.stop_button.grid(row=6, column=0, sticky='e')
        self.stop_button.grid_remove()
        for item in self.saved:
            if item['kind'] == 'search-console':
                self.show_search(item['data'])
        self.show_cached_speed()
        self.refresh_connection()
        self.win.after(100, self.poll)

    def button(self, parent, text, command, **kwargs):
        button = ttk.Button(parent, text=text, command=command, **kwargs)
        self.controls.append((button, 'normal'))
        return button

    def tracked(self, widget, state='normal'):
        self.controls.append((widget, state))
        return widget

    def label(self, parent, text, row):
        label = ttk.Label(parent, text=text, foreground=MUTED, width=1, wraplength=self.app.px(1000))
        label.grid(row=row, column=0, sticky='ew', pady=(0, 10))
        label.bind('<Configure>', lambda event: label.configure(wraplength=max(100, event.width)))

    def scrollable_settings(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        canvas = self.settings_canvas = tk.Canvas(parent, bg=SURFACE, highlightthickness=0, width=1, height=1)
        canvas.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(parent, command=canvas.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        canvas.configure(yscrollcommand=scroll.set)
        content = ttk.Frame(canvas)
        item = canvas.create_window(0, 0, window=content, anchor='nw')
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(item, width=event.width))
        content.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        def wheel(event):
            if content.winfo_height() > canvas.winfo_height():
                canvas.yview_scroll(-int(event.delta / 120), 'units')
                return 'break'
        def bind_children(widget):
            widget.bind('<MouseWheel>', wheel, add='+')
            for child in widget.winfo_children():
                bind_children(child)
        self.win.after_idle(lambda: bind_children(content) if not self.closed else None)
        return content

    def empty_panel(self, parent, title, text, action, command):
        frame = ttk.Frame(parent)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        content = ttk.Frame(frame, padding=self.app.px(8))
        content.grid(row=1, column=0)
        title_label = ttk.Label(content, text=title, font=('Segoe UI Semibold', 16), anchor='center')
        title_label.pack(pady=self.app.px((0, 10)))
        copy = ttk.Label(content, text=text, foreground=MUTED, justify='center', wraplength=self.app.px(480))
        copy.pack(pady=self.app.px((0, 8)))
        button = self.button(content, action, command, style='Primary.TButton')
        button.pack()
        return frame, title_label, copy, button

    def build_speed(self, body):
        body.columnconfigure(0, weight=1)
        body.rowconfigure(4, weight=1)
        intro = ttk.Frame(body, style='Canvas.TFrame')
        intro.grid(row=0, column=0, sticky='ew', pady=self.app.px((0, 10)))
        ttk.Label(intro, text='PageSpeed Insights', style='Section.TLabel').pack(side='left')
        ttk.Label(intro, text='Laboratorní měření rychlosti a doporučení Lighthouse.', style='Canvas.TLabel').pack(side='left', padx=self.app.px(12))
        urls = [p.location for p in self.report.pages] if self.report and self.report.mode == 'URL' else []
        self.speed_controls = ttk.Frame(body, padding=self.app.px((12, 10)), style='Summary.TFrame')
        self.speed_controls.grid(row=1, column=0, sticky='ew')
        self.speed_controls.columnconfigure(0, weight=1)
        ttk.Label(self.speed_controls, text='Stránka z aktuální kontroly', style='Summary.TLabel', font=('Segoe UI Semibold', 9)).grid(row=0, column=0, sticky='w', padx=self.app.px((0, 12)))
        ttk.Label(self.speed_controls, text='Zařízení', style='Summary.TLabel', font=('Segoe UI Semibold', 9)).grid(row=0, column=1, sticky='w', padx=self.app.px((0, 8)))
        self.speed_url = self.tracked(ttk.Combobox(self.speed_controls, values=urls, state='readonly'), 'readonly')
        self.speed_url.grid(row=1, column=0, sticky='ew', padx=self.app.px((0, 12)), pady=self.app.px((4, 0)))
        if urls:
            self.speed_url.current(0)
        self.speed_device = self.tracked(ttk.Combobox(self.speed_controls, values=['Mobil', 'Počítač'], state='readonly', width=12), 'readonly')
        self.speed_device.current(0)
        self.speed_device.grid(row=1, column=1, sticky='w', padx=self.app.px((0, 12)), pady=self.app.px((4, 0)))
        self.measure_button = self.button(self.speed_controls, 'Změřit rychlost', self.measure, style='Primary.TButton')
        self.measure_button.grid(row=1, column=2, sticky='ew', padx=self.app.px((0, 8)), pady=self.app.px((4, 0)))
        self.browser_button = self.button(self.speed_controls, 'Otevřít PageSpeed ↗', self.open_speed_browser, style='Quiet.TButton')
        self.browser_button.grid(row=1, column=3, sticky='ew', pady=self.app.px((4, 0)))
        self.speed_url.bind('<<ComboboxSelected>>', lambda _: self.show_cached_speed())
        self.speed_device.bind('<<ComboboxSelected>>', lambda _: self.show_cached_speed())
        self.speed_metrics = ttk.Frame(body, style='Canvas.TFrame')
        self.speed_metrics.grid(row=2, column=0, sticky='ew', pady=self.app.px((12, 8)))
        self.speed_values = {}
        for index, (key, label, hint) in enumerate([
                ('score', 'Výkon', 'Skóre Lighthouse z 100'),
                ('LCP', 'Načtení hlavního obsahu', 'LCP · laboratorní měření'),
                ('CLS', 'Stabilita rozložení', 'CLS · laboratorní měření')]):
            self.speed_metrics.columnconfigure(index, weight=1, uniform='metrics')
            cell = tk.Frame(self.speed_metrics, bg=SOFT, padx=self.app.px(13), pady=self.app.px(10))
            cell.grid(row=0, column=index, sticky='nsew', padx=self.app.px((0, 8 if index < 2 else 0)))
            tk.Label(cell, text=label, bg=SOFT, fg=INK, font=('Segoe UI Semibold', 10)).pack(anchor='w')
            value = tk.Label(cell, text='—', bg=SOFT, fg=ACCENT, font=('Segoe UI Semibold', 22))
            value.pack(anchor='w', pady=self.app.px((4, 0)))
            tk.Label(cell, text=hint, bg=SOFT, fg=MUTED, font=('Segoe UI', 9)).pack(anchor='w')
            self.speed_values[key] = value
        self.speed_summary = ttk.Label(body, text='Zatím bez měření.', foreground=MUTED)
        self.speed_summary.grid(row=3, column=0, sticky='ew', pady=self.app.px((0, 8)))
        self.speed_results = ttk.Frame(body)
        self.speed_results.grid(row=4, column=0, sticky='nsew')
        self.speed_results.columnconfigure(0, weight=3, minsize=self.app.px(300))
        self.speed_results.columnconfigure(1, weight=2, minsize=self.app.px(230))
        self.speed_results.rowconfigure(1, weight=1)
        ttk.Label(self.speed_results, text='Podrobnosti měření', style='Section.TLabel').grid(row=0, column=0, sticky='w', pady=self.app.px((0, 6)))
        ttk.Label(self.speed_results, text='Doporučení Lighthouse', style='Section.TLabel').grid(row=0, column=1, sticky='w', pady=self.app.px((0, 6)), padx=self.app.px((12, 0)))
        frame, self.speed_detail = text_area(self.speed_results, 10)
        frame.grid(row=1, column=0, sticky='nsew', padx=self.app.px((0, 12)))
        frame, self.speed_recommendations = text_area(self.speed_results, 10)
        frame.grid(row=1, column=1, sticky='nsew')
        self.speed_empty, self.speed_empty_title, self.speed_empty_copy, self.speed_empty_button = self.empty_panel(body, 'Měření se zobrazí tady',
            'Vyberte stránku a zařízení a spusťte měření. Google změří rychlost a připraví konkrétní doporučení.' if urls else 'Nejprve spusťte nebo otevřete kontrolu webové adresy. Pak zde vyberete stránku a změříte její rychlost.',
            'Změřit první stránku' if urls else 'Zpět na přehled', self.measure if urls else self.close)
        self.speed_empty.grid(row=4, column=0, sticky='nsew')
        if urls:
            self.speed_empty_button.pack_forget()
        else:
            self.speed_controls.grid_remove()
            self.speed_metrics.grid_remove()
            self.speed_summary.grid_remove()

    def build_search(self, body):
        body.columnconfigure(0, weight=1)
        body.rowconfigure(3, weight=1)
        body.rowconfigure(5, weight=1)
        body.rowconfigure(6, weight=3)
        self.label(body, ('Nálezy jsou propojeny podle přesné URL, cíle přesměrování nebo canonical.' if self.has_audit() else 'Samostatné zobrazení: můžete načíst stránky a vyhledávací dotazy. Data se neukládají k auditu a nejsou propojena s nálezy.') + ' Stránky jsou seřazené podle zobrazení. Nízké CTR samo o sobě není SEO chyba.', 0)
        row = ttk.Frame(body)
        row.grid(row=1, column=0, sticky='ew')
        self.property = self.tracked(ttk.Combobox(row, state='readonly', width=28), 'readonly')
        self.property.pack(side='left', fill='x', expand=True)
        self.start = tk.StringVar(value=(date.today() - timedelta(days=30)).isoformat())
        self.end = tk.StringVar(value=(date.today() - timedelta(days=3)).isoformat())
        for caption, variable in [('Od', self.start), ('Do', self.end)]:
            ttk.Label(row, text=caption).pack(side='left', padx=6)
            self.tracked(ttk.Entry(row, textvariable=variable, width=11)).pack(side='left')
        self.button(row, 'Načíst data', self.fetch_search, style='Primary.TButton').pack(side='left', padx=(8, 0))
        self.only_opportunities = tk.BooleanVar(value=False)
        row = ttk.Frame(body)
        row.grid(row=2, column=0, sticky='ew', pady=8)
        ttk.Checkbutton(row, text='Příležitosti: ≥ 100 zobrazení, CTR < 2 %', variable=self.only_opportunities, command=self.refresh_pages).pack(side='left')
        self.search_summary = ttk.Label(row, foreground=MUTED)
        self.search_summary.pack(side='right')
        frame, self.pages = table(body, [('url', 'Stránka', 340), ('clicks', 'Prokliky', 80), ('impressions', 'Zobrazení', 85),
                                         ('ctr', 'CTR', 75), ('position', 'Pozice', 70), ('issues', 'Nálezy', 65)], 2)
        frame.grid(row=3, column=0, sticky='nsew')
        self.pages.bind('<<TreeviewSelect>>', self.select_page)
        row = ttk.Frame(body)
        row.grid(row=4, column=0, sticky='ew', pady=8)
        self.button(row, 'Načíst dotazy vybrané stránky', self.fetch_queries).pack(side='left')
        ttk.Label(row, text='Max. 1 000 dostupných dotazů; pozice je průměrná.', foreground=MUTED).pack(side='left', padx=10)
        frame, self.queries = table(body, [('query', 'Vyhledávací dotaz', 400), ('clicks', 'Prokliky', 90), ('impressions', 'Zobrazení', 90), ('ctr', 'CTR', 80), ('position', 'Pozice', 80)], 1)
        frame.grid(row=5, column=0, sticky='nsew')
        frame, self.search_detail = text_area(body, 5)
        frame.grid(row=6, column=0, sticky='nsew', pady=(8, 0))
        self.search_empty, self.search_empty_title, self.search_empty_copy, self.search_empty_button = self.empty_panel(body,
            'Propojte nálezy s návštěvností', 'Připojte Google účet s přístupem k vašemu webu. Uvidíte prokliky, zobrazení a dotazy u konkrétních stránek.',
            'Nastavit připojení', lambda: self.tabs.select(2))
        self.search_empty.grid(row=3, column=0, rowspan=4, sticky='nsew')

    def build_settings(self, body):
        body.columnconfigure(0, weight=1)
        ttk.Label(body, text='Připojte služby ve třech krocích', style='Section.TLabel').grid(row=0, column=0, sticky='w')
        self.label(body, 'Search Console používá Google účet. PageSpeed používá API klíč. Každou službu ověříte samostatně.', 1)
        navigation = ttk.Frame(body)
        navigation.grid(row=2, column=0, sticky='w', pady=self.app.px((2, 12)))
        self.setup_service = tk.StringVar(value='search')
        self.setup_panels = {}
        self.setup_index = {key: tk.IntVar(value=1) for key in ('search', 'speed')}
        self.step_panels = {'search': {}, 'speed': {}}
        for service, caption in (('search', 'Search Console'), ('speed', 'PageSpeed')):
            ttk.Radiobutton(navigation, text=caption, variable=self.setup_service, value=service,
                            style='Segment.TRadiobutton', command=self.select_setup_service).pack(side='left', padx=(0, 6))
            panel = ttk.Frame(body)
            panel.columnconfigure(0, weight=1)
            self.setup_panels[service] = panel
            steps = ttk.Frame(panel)
            steps.grid(row=0, column=0, sticky='ew', pady=self.app.px((0, 12)))
            for number, title in enumerate(('Příprava', 'Přihlášení' if service == 'search' else 'API klíč', 'Ověření'), 1):
                ttk.Radiobutton(steps, text=f'{number}  {title}', variable=self.setup_index[service], value=number,
                                style='Segment.TRadiobutton', command=self.select_setup_step).pack(side='left', padx=(0, 6))
        self.setup_steps = {}

        def step(parent, number, key, title, copy):
            panel = ttk.Frame(parent, padding=self.app.px((12, 10)))
            service = next(key for key, value in self.setup_panels.items() if value is parent)
            self.step_panels[service][number] = panel
            panel.columnconfigure(0, weight=1)
            heading = ttk.Label(panel, text=f'{number}. {title}', font=('Segoe UI Semibold', 11))
            heading.grid(row=0, column=0, sticky='w')
            state = ttk.Label(panel, foreground=MUTED)
            state.grid(row=0, column=1, sticky='e', padx=self.app.px((8, 0)))
            self.setup_steps[key] = state
            self.label(panel, copy, 1)
            actions = ttk.Frame(panel)
            actions.grid(row=2, column=0, columnspan=2, sticky='ew')
            return panel, actions

        google = self.setup_panels['search']
        _, row = step(google, 1, 'client', 'Připravte přístup v Google Cloud',
                      'Zapněte Search Console API. Vytvořte OAuth klienta typu Desktop app a stáhněte JSON.')
        self.button(row, 'Zapnout API ↗', lambda: webbrowser.open('https://console.cloud.google.com/apis/library/searchconsole.googleapis.com')).pack(side='left')
        self.button(row, 'Vytvořit OAuth klienta ↗', lambda: webbrowser.open('https://console.cloud.google.com/auth/clients'), style='Quiet.TButton').pack(side='left', padx=6)
        self.button(row, 'Vybrat OAuth JSON…', self.choose_client).pack(side='right')
        _, row = step(google, 2, 'login', 'Přihlaste svůj Google účet',
                      'Použijte účet s přístupem k webu. V režimu Testing jej nejdřív přidejte v Audience → Test users.')
        self.button(row, 'Přihlásit Google účet', self.connect, style='Primary.TButton').pack(side='left')
        self.button(row, 'Testovací uživatelé ↗', lambda: webbrowser.open('https://console.cloud.google.com/auth/audience'), style='Quiet.TButton').pack(side='left', padx=6)
        self.button(row, 'Odpojit na tomto PC', self.disconnect, style='Quiet.TButton').pack(side='right')
        panel, row = step(google, 3, 'search', 'Ověřte přístup k webům',
                          'Ověření načte seznam dostupných webů. Data webu potom načtete na kartě Search Console.')
        self.button(row, 'Ověřit Search Console', lambda: self.fetch_sites(stay=True), style='Primary.TButton').pack(side='left')
        self.button(row, 'Přejít na data webu →', lambda: self.tabs.select(1), style='Quiet.TButton').pack(side='left', padx=6)
        self.connection = ttk.Label(panel, foreground=MUTED, wraplength=self.app.px(650))
        self.connection.grid(row=3, column=0, columnspan=2, sticky='ew', pady=self.app.px((8, 0)))
        panel.bind('<Configure>', lambda event: self.connection.configure(wraplength=max(200, event.width-self.app.px(24))))

        speed = self.setup_panels['speed']
        _, row = step(speed, 1, 'speed-api', 'Zapněte PageSpeed Insights API',
                      'Ve stejném projektu vytvořte API klíč a omezte jej na PageSpeed Insights API.')
        self.button(row, 'Zapnout PageSpeed API ↗', lambda: webbrowser.open('https://console.cloud.google.com/apis/library/pagespeedonline.googleapis.com')).pack(side='left')
        self.button(row, 'Vytvořit API klíč ↗', lambda: webbrowser.open('https://console.cloud.google.com/apis/credentials'), style='Quiet.TButton').pack(side='left', padx=6)
        panel, row = step(speed, 2, 'key', 'Uložte klíč do aplikace',
                          'Vlastní klíč přidělí požadavky vašemu projektu. I s klíčem platí kvóta Googlu.')
        self.api_key = tk.StringVar()
        self.api_entry = self.tracked(ttk.Entry(row, textvariable=self.api_key, show='•', width=24))
        self.api_entry.pack(side='left', fill='x', expand=True)
        self.button(row, 'Uložit klíč', self.save_key, style='Primary.TButton').pack(side='left', padx=8)
        self.button(row, 'Smazat', self.clear_key, style='Quiet.TButton').pack(side='left')
        self.key_status = ttk.Label(panel, foreground=MUTED, wraplength=self.app.px(650))
        self.key_status.grid(row=3, column=0, columnspan=2, sticky='ew', pady=self.app.px((8, 0)))
        panel.bind('<Configure>', lambda event: self.key_status.configure(wraplength=max(200, event.width-self.app.px(24))))
        panel, row = step(speed, 3, 'speed', 'Ověřte skutečným měřením',
                          'Zadejte veřejnou URL. Odešle se Googlu pro mobilní měření; zabere až 90 sekund a čerpá kvótu. Test se neukládá k auditu.')
        self.verify_url = tk.StringVar(value=self.report.source if self.has_audit() else '')
        self.tracked(ttk.Entry(row, textvariable=self.verify_url, width=24)).pack(side='left', fill='x', expand=True)
        self.button(row, 'Ověřit PageSpeed', self.verify_speed, style='Primary.TButton').pack(side='left', padx=self.app.px((8, 0)))
        self.speed_test_result = ttk.Label(panel, text='Zatím neověřeno. Použije se uložený klíč.', foreground=MUTED, wraplength=self.app.px(650))
        self.speed_test_result.grid(row=3, column=0, columnspan=2, sticky='ew', pady=self.app.px((8, 0)))
        panel.bind('<Configure>', lambda event: self.speed_test_result.configure(wraplength=max(200, event.width-self.app.px(24))))
        self.label(body, 'Přihlášení i klíč se pamatují šifrovaně pro váš účet Windows. Při příštím spuštění nejdřív ověřte připojení.', 4)
        self.select_setup_service()
        try:
            data = self.vault.read()
            self.api_key.set(data.get('api_key', ''))
            self.setup_index['search'].set(3 if data.get('tokens') else 2 if data.get('client') else 1)
            self.setup_index['speed'].set(3 if data.get('api_key') else 1)
            self.select_setup_step()
        except Exception as exc:
            self.connection.configure(text=str(exc))

    def select_setup_service(self):
        for key, panel in self.setup_panels.items():
            if key == self.setup_service.get():
                panel.grid(row=3, column=0, sticky='ew')
            else:
                panel.grid_remove()
        self.select_setup_step()
        self.settings_canvas.yview_moveto(0)

    def select_setup_step(self):
        for service, panels in self.step_panels.items():
            for number, panel in panels.items():
                if number == self.setup_index[service].get():
                    panel.grid(row=1, column=0, sticky='ew', pady=self.app.px((0, 12)))
                else:
                    panel.grid_remove()
        self.settings_canvas.yview_moveto(0)

    def refresh_setup(self, data):
        states = {
            'client': ('✓ JSON uložen', ACCENT) if data.get('client') else ('Čeká na JSON', MUTED),
            'login': ('! Přihlaste se znovu', '#c42b31') if self.login_problem else
                     ('✓ Účet ověřen', ACCENT) if self.google_verified else
                     ('Přihlášení uložené', '#b4690e') if data.get('tokens') else ('Čeká na přihlášení', MUTED),
            'search': (self.api_check[0], self.api_check[2]) if self.api_check else ('Čeká na ověření', MUTED),
            'key': ('✓ Klíč uložen', ACCENT) if data.get('api_key') else ('Volitelné', MUTED),
            'speed': (self.speed_check[0], self.speed_check[2]) if self.speed_check else ('Čeká na měření', MUTED),
        }
        for key, (text, color) in states.items():
            self.setup_steps[key].configure(text=text, foreground=color)

    def show_settings(self, service):
        self.tabs.select(2)
        self.setup_service.set(service)
        if service == 'speed':
            self.setup_index['speed'].set(2)
        self.select_setup_service()
        self.win.update_idletasks()
        if service == 'speed':
            self.api_entry.focus_set()

    def verify_speed(self):
        def action():
            url = self.verify_url.get().strip()
            if not browser_url(url):
                raise ServiceError('Zadejte veřejnou URL začínající https:// nebo http://.')
            data = self.vault.read()
            if self.api_key.get().strip() != data.get('api_key', ''):
                raise ServiceError('Nejprve klikněte na Uložit klíč. Test používá uložený klíč.')
            self.speed_test_result.configure(text='Probíhá mobilní měření…', foreground=MUTED)
            self.verification_url = url
            self.run('speed-test', lambda: pagespeed(url, 'mobile', data.get('api_key', '')))
        self.guard(action, 'speed')

    def open_speed_browser(self, url=None):
        url = self.speed_url.get() if url is None else url
        if not browser_url(url):
            self.show_error(ServiceError('Vyberte platnou HTTP/HTTPS adresu z URL auditu.'), 'speed')
            return
        destination = 'https://pagespeed.web.dev/analysis?' + urlencode({'url': url, 'form_factor': 'mobile' if self.speed_device.get() == 'Mobil' else 'desktop'})
        if webbrowser.open(destination):
            self.status.set('PageSpeed otevřen v prohlížeči. Výsledek z prohlížeče se automaticky neukládá do této aplikace.')
        else:
            self.show_error(ServiceError('Výchozí prohlížeč se nepodařilo otevřít.'), 'speed')

    def require_connection(self):
        data = self.vault.read()
        if not data.get('client'):
            raise ServiceError('Search Console není nastavená. V Připojení služeb vyberte OAuth JSON typu Desktop app a přihlaste Google účet s přístupem k webu.', reason='account_required')
        if not data.get('tokens'):
            raise ServiceError('Search Console není přihlášená. V Připojení služeb klikněte na Přihlásit Google účet.', reason='account_required')

    def refresh_connection(self):
        try:
            data = self.vault.read()
            self.connection.configure(text='Přihlášení je uložené. Přístup k Search Console ověřte tlačítkem Načíst weby.' if data.get('tokens') else 'Účet není připojen.')
            if self.api_check:
                self.connection.configure(text=self.api_check[0] + ' · ' + self.api_check[1], foreground=self.api_check[2])
            else:
                self.connection.configure(foreground=MUTED)
            self.refresh_setup(data)
            has_key = bool(data.get('api_key'))
            if not data.get('tokens'):
                self.set_indicator('account', '○ Nejste přihlášen', 'Připojte účet v Připojení služeb.', MUTED)
            elif self.login_problem:
                self.set_indicator('account', '! Obnovte přihlášení', 'Google odmítl uložené přihlášení.', '#c42b31')
            elif self.google_verified:
                self.set_indicator('account', '✓ Přihlášen', 'Přístup pouze ke čtení.', ACCENT)
            else:
                self.set_indicator('account', '● Přihlášení uložené', 'Aktuální přístup ověří Ověřit Search Console.', '#b4690e')
            if self.api_check:
                self.set_indicator('search', *self.api_check)
            else:
                self.set_indicator('search', '○ Přístup neověřen', 'Klikněte na Ověřit Search Console.', MUTED)
            if self.speed_check:
                self.set_indicator('speed', *self.speed_check)
            else:
                key = 'pagespeed:' + ('mobile' if self.speed_device.get() == 'Mobil' else 'desktop') + ':' + self.speed_url.get()
                cached = next((item for item in self.saved if item['kind'] == key), None)
                if cached:
                    self.set_indicator('speed', '○ Uložené měření', date_label(cached['saved']) + ' · dostupnost nyní neověřena.', MUTED)
                else:
                    self.set_indicator('speed', '● Klíč nastaven' if has_key else '○ Bez API klíče', 'Dostupnost ověří nové měření.', '#b4690e' if has_key else MUTED)
            self.key_status.configure(text='Klíč uložen. Platnost ověří až požadavek na Google.' if has_key else 'Klíč není nastaven. Měření bez klíče může Google odmítnout (HTTP 429).')
            if self.report and self.report.mode == 'URL' and not has_key:
                self.speed_empty_copy.configure(text='Bez API klíče může Google měření odmítnout. Klíč přidejte v Připojení služeb, nebo nahoře otevřete PageSpeed v prohlížeči.')
            elif self.report and self.report.mode == 'URL':
                self.speed_empty_copy.configure(text='Vyberte stránku a zařízení. Měření se uloží k auditu a může trvat až 90 sekund.')
            if not self.gsc:
                if data.get('tokens'):
                    self.search_empty_title.configure(text='Načtěte dostupné weby')
                    self.search_empty_copy.configure(text='Přihlášení je uložené. Ověřte přístup a vyberte web pro načtení dat.')
                    self.search_empty_button.configure(text='Načíst weby', command=self.fetch_sites)
                else:
                    self.search_empty_title.configure(text='Search Console není připojená')
                    self.search_empty_copy.configure(text='Data o proklicích a dotazech vyžadují přihlášení vlastníka nebo oprávněného uživatele webu. Připojte účet v nastavení.')
                    self.search_empty_button.configure(text='Nastavit připojení', command=lambda: self.show_settings('search'))
        except Exception as exc:
            self.show_error(exc, 'settings')

    def set_indicator(self, key, title, copy, color):
        heading, detail = self.indicators[key]
        heading.configure(text=title, foreground=color)
        detail.configure(text=copy)

    def verified_search(self, count=None):
        self.google_verified = True
        self.login_problem = False
        stamp = datetime.now().strftime('%H:%M:%S')
        self.api_check = ('✓ API funguje', f'Ověřeno v {stamp}' + (f' · Webů: {count}' if count is not None else ''), ACCENT)
        self.refresh_connection()

    def tick_activity(self):
        if self.closed or not self.busy:
            return
        elapsed = int(time.monotonic() - self.operation_started)
        title = 'Zastavuji požadavek' if self.cancel.is_set() else {'auth': 'Čekám na přihlášení v prohlížeči', 'sites': 'Ověřuji přístup a načítám weby', 'sites-test': 'Ověřuji Search Console', 'speed-test': 'Ověřuji PageSpeed měřením', 'speed': 'Měřím rychlost webu', 'search': 'Načítám data Search Console', 'queries': 'Načítám vyhledávací dotazy'}.get(self.active_kind, 'Pracuji')
        self.activity.configure(text=f'● {title} · {elapsed} s', foreground='#4f46e5')
        self.activity_after = self.win.after(500, self.tick_activity)

    def show_error(self, error, kind):
        self.last_diagnostic = diagnose(error, kind)
        verification = kind == 'speed-test'
        if kind == 'speed-test':
            self.speed_test_result.configure(text=str(error), foreground='#c42b31')
            kind = 'speed'
        elif kind == 'sites-test':
            kind = 'sites'
        self.error_settings.pack(side='left')
        self.error_text.configure(foreground='#c42b31')
        if kind == 'input':
            self.activity.configure(text='! Zkontrolujte zadání', foreground='#b4690e')
            self.error_text.configure(text='Načítání nebylo spuštěno\n' + str(error), foreground='#b4690e')
            self.error_browser.pack_forget()
            if getattr(error, 'reason', '') == 'audit_required':
                self.error_settings.configure(text='Zpět na přehled', command=self.close)
            elif getattr(error, 'reason', '') == 'account_required':
                self.error_settings.configure(text='Otevřít připojení služeb', command=lambda: self.show_settings('search'))
            else:
                self.error_settings.pack_forget()
            self.error_box.grid()
            self.status.set('Upravte zadání podle hlášení. Stav připojení se nezměnil.')
            return
        code = getattr(error, 'status', 0)
        message = str(error)
        self.activity.configure(text='! Akce se nezdařila', foreground='#c42b31')
        stamp = datetime.now().strftime('%H:%M:%S')
        if kind == 'speed':
            self.speed_check = ('! Měření se nezdařilo', f'Poslední pokus v {stamp} · podrobnosti v hlášení.', '#c42b31')
            self.set_indicator('speed', *self.speed_check)
        elif kind in ('search', 'sites', 'queries', 'auth') and getattr(error, 'reason', '') != 'no_sites':
            self.api_check = ('! Přístup se nepodařilo ověřit', f'Poslední pokus v {stamp} · podrobnosti v hlášení.', '#c42b31')
            self.set_indicator('search', *self.api_check)
            if code == 401 or getattr(error, 'reason', '') == 'login_expired':
                self.login_problem = True
                self.set_indicator('account', '! Obnovte přihlášení', 'Klikněte na Přihlásit Google účet.', '#c42b31')
        if kind == 'speed':
            title = 'Rychlost nebyla změřena'
            if code == 429:
                message = 'Google odmítl požadavek kvůli kvótě (HTTP 429). V Připojení služeb nastavte vlastní PageSpeed API klíč. Pokud už klíč máte, ověřte kvótu jeho projektu nebo měření opakujte později. Můžete také otevřít PageSpeed v prohlížeči.'
            elif code in (400, 403):
                message += ' Pro PageSpeed ověřte API klíč a zapnuté PageSpeed Insights API.'
            self.error_browser.pack(side='left', padx=self.app.px(8))
            self.error_browser.configure(command=(lambda url=self.verification_url: self.open_speed_browser(url)) if verification else self.open_speed_browser)
            self.error_settings.configure(text='Nastavit PageSpeed klíč', command=lambda: self.show_settings('speed'))
        else:
            title = 'Search Console se nepodařilo načíst' if kind in ('search', 'sites', 'queries', 'auth') else 'Akce se nepodařila'
            self.error_browser.pack_forget()
            self.error_settings.configure(text='Otevřít připojení služeb', command=lambda: self.show_settings('search'))
            if getattr(error, 'reason', '') == 'service_disabled':
                self.error_settings.configure(text='Zapnout Search Console API ↗', command=lambda: webbrowser.open('https://console.cloud.google.com/apis/library/searchconsole.googleapis.com'))
                self.connection.configure(text='Přihlášení je uložené, ale Search Console API není zapnuté v Google Cloud.')
        self.status.set(title + '. Podrobnosti a další krok jsou v hlášení nad kartou.')
        self.error_text.configure(text=title + ' · ' + self.last_diagnostic['category'] + '\n' + message + '\n' + self.last_diagnostic['step'])
        self.error_box.grid()
        try:
            self.refresh_setup(self.vault.read())
        except Exception:
            pass  # Keep the original error visible even when the vault cannot be read.

    def require_audit(self):
        if not self.report or self.report.mode != 'URL' or not self.audit_id or not self.app.store:
            raise ServiceError('Pro měření PageSpeed nejprve spusťte a uložte kontrolu URL, nebo ji otevřete z historie. Poté znovu otevřete Rychlost a Google.', reason='audit_required')

    def has_audit(self):
        return bool(self.report and self.report.mode == 'URL' and self.audit_id and self.app.store)

    def result_scope(self):
        return '' if self.has_audit() else ' Samostatné zobrazení: data se neukládají k auditu a nejsou propojena s nálezy.'

    def run(self, kind, callback):
        if self.busy:
            return
        self.error_box.grid_remove()
        self.active_kind = kind
        self.busy = True
        if self.activity_after:
            self.win.after_cancel(self.activity_after)
            self.activity_after = None
        self.operation_started = time.monotonic()
        self.cancel = threading.Event()
        self.tick_activity()
        self.status.set({'auth': 'Dokončete přihlášení v otevřeném prohlížeči.', 'speed': 'Měřím rychlost stránky. Může to trvat až 90 sekund.', 'search': 'Načítám výkon stránek…', 'queries': 'Načítám vyhledávací dotazy…', 'sites': 'Načítám dostupné weby…'}.get(kind, 'Načítám…'))
        self.loading.grid()
        self.loading.start(12)
        self.stop_button.grid()
        for widget, _ in self.controls:
            widget.configure(state='disabled')
        self.stop_button.configure(state='normal')
        def worker():
            try:
                self.events.put((kind, callback()))
            except Exception as exc:
                self.events.put(('error', exc))
        threading.Thread(target=worker, daemon=True).start()

    def guard(self, callback, kind='settings'):
        try:
            callback()
        except Exception as exc:
            self.show_error(exc, 'input' if kind in ('search', 'speed', 'queries') else kind)

    def choose_client(self):
        path = filedialog.askopenfilename(parent=self.win, title='OAuth klient typu Desktop app', filetypes=[('JSON', '*.json')])
        if path:
            self.guard(lambda: self.install_client(path))

    def install_client(self, path):
        self.vault.update(client=load_client(path), tokens=None)
        self.google_verified, self.api_check, self.login_problem = False, None, False
        self.connection.configure(text='OAuth klient je uložený. Přihlaste Google účet.')
        self.refresh_connection()
        self.setup_index['search'].set(2)
        self.select_setup_step()
        self.property.configure(values=[])
        self.property.set('')

    def connect(self):
        def start():
            client = self.vault.read().get('client')
            if not client:
                raise ServiceError('Nejprve vyberte JSON OAuth klienta typu Desktop app.')
            self.run('auth', lambda: authorize(client, self.cancel))
        self.guard(start, 'search')

    def disconnect(self):
        def action():
            self.vault.update(tokens=None)
            self.google_verified, self.api_check, self.login_problem = False, None, False
            self.connection.configure(text='Účet byl odpojen na tomto počítači.')
            self.property.configure(values=[])
            self.property.set('')
            self.status.set('Místní přihlášení odstraněno. Uložená měření zůstávají v historii.')
            self.refresh_connection()
        self.guard(action)

    def fetch_sites(self, stay=False):
        def action():
            self.require_connection()
            self.run('sites-test' if stay else 'sites', lambda: SearchConsole(self.vault).sites())
        self.guard(action, 'search')

    def save_key(self):
        def action():
            self.vault.update(api_key=self.api_key.get().strip())
            self.speed_check = None
            self.speed_test_result.configure(text='Klíč se změnil. Ověřte jej novým měřením.', foreground=MUTED)
            self.status.set('API klíč byl uložen. Pokračujte krokem 3: Ověřit PageSpeed.' if self.api_key.get().strip() else 'API klíč byl odstraněn.')
            self.error_box.grid_remove()
            self.refresh_connection()
            self.setup_index['speed'].set(3)
            self.select_setup_step()
        self.guard(action)

    def clear_key(self):
        self.api_key.set('')
        self.save_key()

    def measure(self):
        def action():
            self.require_audit()
            url = self.speed_url.get()
            strategy = 'mobile' if self.speed_device.get() == 'Mobil' else 'desktop'
            key = self.vault.read().get('api_key', '')
            self.run('speed', lambda: pagespeed(url, strategy, key))
        self.guard(action, 'speed')

    def fetch_search(self):
        def action():
            self.require_connection()
            property_url, start, end = self.property.get(), self.start.get(), self.end.get()
            if not property_url:
                self.fetch_sites()
                return
            if self.has_audit() and not property_contains(property_url, self.report.source):
                raise ServiceError('Vyberte službu Search Console, která obsahuje URL otevřeného auditu.')
            validate_dates(start, end)
            self.run('search', lambda: SearchConsole(self.vault).query(property_url, start, end, self.cancel))
        self.guard(action, 'search')

    def fetch_queries(self):
        if not self.gsc or not self.pages.selection():
            self.status.set('Nejprve načtěte stránky a vyberte řádek.')
            return
        url = self.page_rows[int(self.pages.selection()[0])]['keys'][0]
        data = self.gsc
        self.run('queries', lambda: SearchConsole(self.vault).query(data['property'], data['start'], data['end'], self.cancel, page=url, max_rows=1000))

    def save_result(self, kind, data):
        if not self.has_audit():
            return
        self.app.store.save_measurement(self.audit_id, kind, data)
        self.saved = self.app.store.measurements(self.audit_id)

    def poll(self):
        if self.closed or not self.win.winfo_exists():
            return
        try:
            kind, data = self.events.get_nowait()
        except queue.Empty:
            self.win.after(100, self.poll)
            return
        self.busy = False
        if self.activity_after:
            self.win.after_cancel(self.activity_after)
            self.activity_after = None
        elapsed = int(time.monotonic() - self.operation_started)
        self.activity.configure(text=f'✓ Hotovo · {elapsed} s', foreground=ACCENT)
        self.loading.stop()
        self.loading.grid_remove()
        for widget, state in self.controls:
            widget.configure(state=state)
        self.stop_button.configure(state='disabled')
        self.stop_button.grid_remove()
        try:
            if self.cancel.is_set():
                self.activity.configure(text='○ Operace zastavena', foreground=MUTED)
                self.status.set('Operace zastavena; výsledek nebyl uložen.')
                if self.active_kind == 'speed-test':
                    self.speed_test_result.configure(text='Test zastaven. Připojení nebylo znovu ověřeno.', foreground=MUTED)
            elif kind == 'error':
                self.show_error(data, getattr(self, 'active_kind', 'settings'))
            elif kind == 'auth':
                self.vault.update(tokens=data)
                self.google_verified, self.api_check, self.login_problem = True, None, False
                self.connection.configure(text='Google účet připojen; oprávnění pouze ke čtení.')
                self.refresh_connection()
                self.setup_index['search'].set(3)
                self.select_setup_step()
                self.fetch_sites(stay=self.tabs.index(self.tabs.select()) == 2)
            elif kind in ('sites', 'sites-test'):
                self.verified_search(len(data))
                self.connection.configure(text=f'Přístup k Search Console ověřen. Dostupných webů: {len(data)}.')
                relevant = [p for p in data if self.report and property_contains(p, self.report.source)]
                self.property.configure(values=relevant or data)
                self.property.set((relevant or data or [''])[0])
                if not self.gsc and data:
                    self.search_empty_title.configure(text='Váš web je připravený')
                    self.search_empty_copy.configure(text='Nahoře vyberte web a období.' + (' Načtené stránky propojíme s nálezy z otevřené kontroly.' if self.has_audit() else self.result_scope()))
                    self.search_empty_button.configure(text='Načíst data webu', command=self.fetch_search)
                if kind == 'sites':
                    self.tabs.select(1)
                self.status.set(f'Dostupných webů: {len(data)}. Zvolte období na kartě Search Console.')
                if not data:
                    self.show_error(ServiceError('Přihlášený účet nemá dostupný web. Přidejte nebo ověřte svůj web v Google Search Console, případně použijte účet s přístupem k webu.', reason='no_sites'), 'sites')
            elif kind == 'speed-test':
                self.speed_check = ('✓ Měření funguje', 'Ověřeno v ' + datetime.now().strftime('%H:%M:%S'), ACCENT)
                self.refresh_connection()
                score = data['score'] if data['score'] is not None else '—'
                self.speed_test_result.configure(text=f"✓ PageSpeed odpověděl · {data['url']} · Výkon: {score} / 100. Test není uložen v historii.", foreground=ACCENT)
                self.status.set('PageSpeed je ověřen. Výsledek testu platí pro zadanou URL a tento okamžik.')
            elif kind == 'speed':
                self.speed_check = ('✓ Měření funguje', 'Ověřeno v ' + datetime.now().strftime('%H:%M:%S'), ACCENT)
                self.refresh_connection()
                self.save_result('pagespeed:' + data['strategy'] + ':' + data['url'], data)
                self.show_speed(data)
                self.status.set('Měření PageSpeed uloženo k auditu. Je součástí exportu.')
            elif kind == 'search':
                self.verified_search()
                self.save_result('search-console', data)
                self.show_search(data)
                self.status.set(data['note'] + (' Dosažen limit 50 000 řádků.' if data['truncated'] else '') + self.result_scope())
            elif kind == 'queries':
                self.verified_search()
                self.save_result('search-queries:' + data['page'], data)
                if self.pages.selection() and self.page_rows[int(self.pages.selection()[0])]['keys'][0] == data['page']:
                    self.show_queries(data)
                self.status.set(f'Dotazy pro {data["page"]} · {data["start"]} až {data["end"]}. ' + ('Dosažen limit 1 000.' if data['truncated'] else 'Dostupné řádky API; anonymizované dotazy mohou chybět.') + self.result_scope())
        except Exception as exc:
            self.show_error(ServiceError('Výsledek se nepodařilo uložit nebo zobrazit: ' + str(exc), reason='storage'), 'storage')
        self.win.after(100, self.poll)

    def show_cached_speed(self):
        strategy = 'mobile' if self.speed_device.get() == 'Mobil' else 'desktop'
        key = 'pagespeed:' + strategy + ':' + self.speed_url.get()
        item = next((item for item in self.saved if item['kind'] == key), None)
        if item:
            self.show_speed(item['data'])
            if not self.speed_check:
                self.set_indicator('speed', '○ Uložené měření', date_label(item['saved']) + ' · dostupnost nyní neověřena.', MUTED)
        else:
            self.speed_empty.grid()
            self.speed_results.grid_remove()
            for value in self.speed_values.values():
                value.configure(text='—')
            self.speed_summary.configure(text='Laboratorní měření · Zatím bez výsledku')
            fill_text(self.speed_detail, 'Po spuštění se zde zobrazí adresa po přesměrování, výsledky Lighthouse a dostupná data od skutečných návštěvníků.')
            fill_text(self.speed_recommendations, 'Po dokončení měření se zde zobrazí konkrétní tipy na zlepšení rychlosti.')
        self.refresh_connection()

    def show_speed(self, data):
        self.speed_empty.grid_remove()
        self.speed_results.grid()
        score = data['score']
        score_color = ACCENT if isinstance(score, (int, float)) and score >= 90 else '#b4690e' if isinstance(score, (int, float)) and score >= 50 else '#d1343a' if isinstance(score, (int, float)) else MUTED
        self.speed_values['score'].configure(text=f'{score} / 100' if score is not None else '—', foreground=score_color)
        for metric in data['lab']:
            if metric['name'] in self.speed_values:
                self.speed_values[metric['name']].configure(text=metric['value'])
        self.speed_summary.configure(text=f'{"Mobil" if data["strategy"] == "mobile" else "Počítač"} · {date_label(data["created"])} · Laboratorní měření Lighthouse')
        lines = ['Adresa po přesměrování', data['final_url'], '', 'Laboratorní metriky']
        lines.extend(f'{metric["name"]}: {metric["value"]}' for metric in data['lab'])
        lines.extend(['', 'TBT je laboratorní údaj a nenahrazuje INP. Skóre Lighthouse není SEO skóre ani potvrzení splnění Core Web Vitals.', '', 'Data skutečných návštěvníků'])
        if not data['field']:
            lines.append('Pro tuto URL nebo celý web nejsou v CrUX dostupná data. Nelze z toho usuzovat, že jsou výsledky dobré nebo špatné.')
        for item in data['field']:
            lines.extend([f'{item["scope"]}: {item["overall"] or "bez souhrnného hodnocení"}', item['id']])
            for key, metric in item['metrics'].items():
                # PSI encodes CLS percentile in hundredths; preserve the raw value
                # and label its scale, rather than presenting it as a CLS ratio.
                unit = ' (CLS × 100)' if key == 'CUMULATIVE_LAYOUT_SHIFT_SCORE' else ' ms' if key.endswith('_MS') or key == 'INTERACTION_TO_NEXT_PAINT' else ''
                lines.append(f'{key}: 75. percentil {metric.get("percentile", "—")}{unit} · {metric.get("category", "Neověřeno")}')
        lines.extend(['', data['field_note']])
        fill_text(self.speed_detail, '\n'.join(lines))
        recommendations = []
        for item in data['suggestions']:
            recommendations.extend([item['title'] + (f' · {item["value"]}' if item.get('value') else ''), item['description'], ''])
        if not recommendations:
            recommendations = ['Lighthouse nenašel doporučení s nízkým skóre. Projděte také metriky a ověřte zkušenost na skutečných zařízeních.']
        if data['warnings']:
            recommendations.extend(['Upozornění', *[str(item) for item in data['warnings']]])
        fill_text(self.speed_recommendations, '\n'.join(recommendations))

    def show_search(self, data):
        self.search_empty.grid_remove()
        self.gsc = data
        self.property.configure(values=[data['property']])
        self.property.set(data['property'])
        self.start.set(data['start'])
        self.end.set(data['end'])
        self.refresh_pages()

    @staticmethod
    def metrics(row):
        return (f'{row.get("clicks", 0):,.0f}', f'{row.get("impressions", 0):,.0f}',
                f'{row.get("ctr", 0)*100:.2f} %', f'{row.get("position", 0):.1f}')

    def refresh_pages(self):
        self.pages.delete(*self.pages.get_children())
        self.queries.delete(*self.queries.get_children())
        if not self.gsc:
            return
        self.page_rows = sorted([r for r in self.gsc['rows'] if not self.only_opportunities.get() or opportunity(r)], key=lambda r: -r.get('impressions', 0))
        for i, row in enumerate(self.page_rows):
            url = row['keys'][0]
            count = len(match_findings(self.report, url)) if self.has_audit() else '—'
            self.pages.insert('', 'end', iid=str(i), values=(url, *self.metrics(row), count))
        self.search_summary.configure(text=f'{len(self.page_rows)} stránek · {self.gsc["start"]} – {self.gsc["end"]}' + ('' if self.has_audit() else ' · Bez auditu'))
        fill_text(self.search_detail, self.gsc['note'] + (' Dosažen limit 50 000 řádků.' if self.gsc['truncated'] else '') + ('\nPro tento výběr nejsou dostupná data.' if not self.page_rows else ''))

    def select_page(self, event=None):
        if not self.pages.selection():
            return
        row = self.page_rows[int(self.pages.selection()[0])]
        url = row['keys'][0]
        findings = match_findings(self.report, url) if self.has_audit() else []
        lines = [url, 'NÁLEZY Z AUDITU #' + str(self.audit_id) if self.has_audit() else 'Samostatné zobrazení Search Console. Pro propojení s nálezy otevřete nebo spusťte kontrolu URL.']
        lines.extend(f'{f.status}: {f.name} · {p.location}\n{f.advice}' for p, f in findings)
        if not findings and self.has_audit():
            lines.append('Žádné spárované chyby/doporučení. URL mohla být mimo rozsah auditu.')
        if opportunity(row):
            lines.append('Příležitost podle nastaveného filtru. Posuďte dotazy, průměrnou pozici, záměr hledání a titulek; nízké CTR samo o sobě neprokazuje chybu.')
        fill_text(self.search_detail, '\n\n'.join(lines))
        self.queries.delete(*self.queries.get_children())
        item = next((x for x in self.saved if x['kind'] == 'search-queries:' + url and x['data']['start'] == self.gsc['start'] and x['data']['end'] == self.gsc['end'] and x['data']['property'] == self.gsc['property']), None)
        if item:
            self.show_queries(item['data'])

    def show_queries(self, data):
        self.queries.delete(*self.queries.get_children())
        for row in data['rows']:
            self.queries.insert('', 'end', values=(row['keys'][0], *self.metrics(row)))

    def stop(self):
        self.cancel.set()
        self.status.set('Zastavuji. Probíhající požadavek může čekat na síťový timeout (PageSpeed až 90 s).')
        self.stop_button.configure(state='disabled')

    def close(self):
        self.closed = True
        if self.activity_after:
            self.win.after_cancel(self.activity_after)
        self.cancel.set()
        self.win.destroy()
