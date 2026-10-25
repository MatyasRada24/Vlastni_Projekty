"""Page-by-page evidence comparison and project trends, using saved data only."""
import tkinter as tk
from tkinter import ttk

from .evolution import page_changes, trend_rows
from .theme import ACCENT, DANGER, INK, MUTED, SURFACE, WARNING
from .workspace import date_label, fill_text, table, text_area, window


class PageComparisonWindow:
    def __init__(self, app, previous, current, url=None):
        self.app, self.previous, self.current = app, previous, current
        self.win, body = window(app, 'Stránka před a po')
        body.columnconfigure(0, weight=1)
        body.rowconfigure(3, weight=1)
        body.rowconfigure(4, weight=2)
        ttk.Label(body, text='Co se na stránce změnilo', style='Title.TLabel').grid(row=0, column=0, sticky='w')
        self.note = ttk.Label(body, style='Canvas.TLabel', wraplength=app.px(1000))
        self.note.grid(row=1, column=0, sticky='ew', pady=app.px((6, 12)))
        urls = sorted({p.location for p in current.pages} | {p.location for p in previous.pages} if previous else {p.location for p in current.pages})
        self.choice = ttk.Combobox(body, values=urls, state='readonly')
        self.choice.grid(row=2, column=0, sticky='ew', pady=app.px((0, 10)))
        self.choice.bind('<<ComboboxSelected>>', self.select_page)
        frame, self.tree = table(body, [('field', 'Údaj', app.px(160)), ('state', 'Změna', app.px(100)),
                                      ('before', 'Před', app.px(300)), ('after', 'Po', app.px(300))], 7)
        frame.grid(row=3, column=0, sticky='nsew')
        self.tree.tag_configure('changed', foreground=ACCENT)
        self.tree.tag_configure('unknown', foreground=WARNING)
        self.tree.bind('<<TreeviewSelect>>', self.select_field)
        detail = ttk.Frame(body, style='Canvas.TFrame')
        detail.grid(row=4, column=0, sticky='nsew', pady=app.px((12, 0)))
        detail.columnconfigure((0, 1), weight=1, uniform='values')
        detail.rowconfigure(1, weight=1)
        self.values = []
        for index, caption in enumerate(('Před', 'Po')):
            report = previous if index == 0 else current
            ttk.Label(detail, text=caption + ' · ' + (date_label(report.created) if report else 'Bez předchozího auditu'),
                      style='Canvas.TLabel').grid(row=0, column=index, sticky='w')
            frame, text = text_area(detail, 5)
            frame.grid(row=1, column=index, sticky='nsew', padx=app.px((0, 8) if index == 0 else (8, 0)))
            self.values.append(text)
        if urls:
            self.choice.set(url if url in urls else urls[0])
            self.select_page()

    def select_page(self, event=None):
        self.rows = page_changes(self.previous, self.current, self.choice.get())
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(self.rows):
            values = [row['field'], row['state'], self.display(row['before']), self.display(row['after'])]
            self.tree.insert('', 'end', iid=str(index), values=values,
                             tags=('changed' if row['state'] == 'Změněno' else 'unknown' if row['state'] == 'Neověřeno' else 'plain',))
        self.note.configure(text='Porovnává se přesně stejná URL. Změna hodnoty sama nepotvrzuje opravu. '
                            'Neověřeno znamená chybějící stránku, údaj nebo nesrovnatelný režim vykreslení. '
                            'Prázdná hodnota je odlišena od nezměřeného údaje.')
        self.tree.selection_set('0')
        self.select_field()

    @staticmethod
    def display(value):
        return 'Neověřeno / údaj chybí' if value is None else value if value else '(prázdné)'

    def select_field(self, event=None):
        if self.tree.selection():
            row = self.rows[int(self.tree.selection()[0])]
            for text, key in zip(self.values, ('before', 'after')):
                fill_text(text, row['field'] + '\n\n' + self.display(row[key]))


class TrendsWindow:
    def __init__(self, app, project_id):
        self.app = app
        self.rows = trend_rows(app.store, project_id)
        self.speeds = app.store.speed_history(project_id)
        self.win, body = window(app, 'Vývoj webu')
        body.columnconfigure(0, weight=1)
        body.rowconfigure(3, weight=1)
        body.rowconfigure(4, weight=1)
        ttk.Label(body, text='Vývoj webu v čase', style='Title.TLabel').grid(row=0, column=0, sticky='w')
        controls = ttk.Frame(body, style='Canvas.TFrame')
        controls.grid(row=1, column=0, sticky='ew', pady=app.px(12))
        self.metric = ttk.Combobox(controls, state='readonly', values=['Chyby a doporučení', 'Otevřené opravy', 'Rychlost Lighthouse'], width=24)
        self.metric.current(0)
        self.metric.pack(side='left')
        self.metric.bind('<<ComboboxSelected>>', self.refresh)
        self.speed_keys = sorted({(r['url'], r['strategy']) for r in self.speeds})
        self.speed_choice = ttk.Combobox(controls, state='readonly', values=[f'{u} · {d}' for u, d in self.speed_keys])
        self.speed_choice.pack(side='left', fill='x', expand=True, padx=app.px((10, 0)))
        if self.speed_keys:
            self.speed_choice.current(0)
        self.speed_choice.bind('<<ComboboxSelected>>', self.refresh)
        self.note = ttk.Label(body, style='Canvas.TLabel', wraplength=app.px(1000))
        self.note.grid(row=2, column=0, sticky='ew', pady=app.px((0, 10)))
        self.canvas = tk.Canvas(body, background=SURFACE, highlightthickness=0, height=app.px(230))
        self.canvas.grid(row=3, column=0, sticky='nsew')
        self.canvas.bind('<Configure>', lambda event: self.draw())
        frame, self.table = table(body, [('time', 'Čas / audit', app.px(210)), ('value', 'Hodnota', app.px(160)), ('scope', 'Rozsah a srovnatelnost', app.px(500))], 5)
        frame.grid(row=4, column=0, sticky='nsew', pady=app.px((12, 0)))
        self.refresh()

    def refresh(self, event=None):
        self.points = []
        self.table.delete(*self.table.get_children())
        metric = self.metric.current()
        self.speed_choice.configure(state='readonly' if metric == 2 and self.speed_keys else 'disabled')
        if metric == 2:
            key = self.speed_keys[self.speed_choice.current()] if self.speed_keys else None
            rows = [r for r in self.speeds if (r['url'], r['strategy']) == key][-30:]
            self.note.configure(text='Laboratorní skóre 0–100, vyšší je lepší. Porovnává se stejná URL a zařízení. Změna verze Lighthouse nebo prostředí přeruší spojnici; výsledek není návštěvnost ani pořadí v Googlu.')
            previous = None
            for row in rows:
                compatible = previous and row.get('version') == previous.get('version') and row.get('environment') == previous.get('environment')
                self.points.append(([row.get('score')], bool(compatible), date_label(row['created'])))
                self.table.insert('', 'end', values=(date_label(row['created']), row.get('score', '—'),
                                  f"{row['strategy']} · Lighthouse {row.get('version', '—')} · " + ('Stejné prostředí' if compatible else 'První bod nebo změna prostředí')))
                previous = row
            self.colors, self.legend = [ACCENT], 'Skóre Lighthouse / 100'
        else:
            self.note.configure(text='Posledních 30 auditů; body jsou v pořadí kontrol. Oranžové značky a přerušené spojnice upozorňují na nesrovnatelný rozsah nebo způsob kontroly. ' +
                ('Otevřené opravy = jednotlivé nálezy se stavem Otevřené uloženým u auditu. Ruční stav neprokazuje opravu; u starších auditů může chybět.' if metric == 1 else 'Pokles počtu chyb sám nepotvrzuje opravu.'))
            for row in self.rows:
                values = [row['open']] if metric == 1 else [row['errors'], row['warnings']]
                self.points.append((values, row['comparable'], f"#{row['id']}"))
                scope = f"{row['pages']} stránek · " + ('Dokončený rozsah' if row['complete'] else 'Částečná kontrola')
                scope += ' · ' + ('; '.join(row['scope_warnings']) or 'První nebo srovnatelná kontrola')
                if metric == 1:
                    scope += ' · Stav práce: ' + (date_label(row['state_updated']) if row['state_updated'] else 'Bez historického záznamu')
                self.table.insert('', 'end', values=(f"#{row['id']} · {date_label(row['created'])}",
                                  ' / '.join(str(v) if v is not None else 'Bez dat' for v in values), scope))
            self.colors = [ACCENT] if metric == 1 else [DANGER, WARNING]
            self.legend = 'Otevřené nálezy' if metric == 1 else 'Červená: chyby   ·   Okrová: doporučení'
        self.draw()

    def draw(self):
        if not hasattr(self, 'points'):
            return
        c, px = self.canvas, self.app.px
        c.delete('all')
        width, height = max(c.winfo_width(), px(300)), max(c.winfo_height(), px(180))
        c.create_text(px(16), px(16), text=self.legend, anchor='nw', fill=INK, font=('Segoe UI', 10))
        if not self.points or all(v is None for values, _, _ in self.points for v in values):
            c.create_text(width/2, height/2, text='Zatím nejsou uložená data pro tento graf.', fill=MUTED, font=('Segoe UI', 11))
            return
        top, bottom, left, right = px(48), height-px(42), px(48), width-px(30)
        maximum = 100 if self.metric.current() == 2 else max(1, max(v for values, _, _ in self.points for v in values if v is not None))
        for fraction in (0, .5, 1):
            y = bottom - (bottom-top)*fraction
            c.create_line(left, y, right, y, fill='#e2e6f0')
            c.create_text(left-px(8), y, text=f'{maximum*fraction:g}', anchor='e', fill=MUTED)
        for series, color in enumerate(self.colors):
            previous = None
            for index, (values, compatible, label) in enumerate(self.points):
                x = left + (right-left)*index/max(1, len(self.points)-1)
                value = values[series]
                if value is None:
                    previous = None
                    continue
                y = bottom - (bottom-top)*value/maximum
                if previous and compatible:
                    c.create_line(*previous, x, y, fill=color, width=px(2))
                c.create_oval(x-px(4), y-px(4), x+px(4), y+px(4), fill=color, outline=WARNING if index and not compatible else color, width=px(2))
                previous = (x, y)
                if series == 0 and (index in (0, len(self.points)-1) or len(self.points) <= 7):
                    c.create_text(x, bottom+px(16), text=label.rsplit(' ', 1)[0] if self.metric.current() == 2 else label,
                                  anchor='w' if index == 0 else 'e' if index == len(self.points)-1 else 'center', fill=MUTED)
