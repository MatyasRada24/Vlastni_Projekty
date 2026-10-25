"""Presentation of the desktop audit; audit and threading stay in Application."""
import tkinter as tk
from tkinter import ttk

from .engine import STATUSES
from .theme import (ACCENT, ACCENT_DARK, ACCENT_SOFT, BG, CONTROL, INK, LINE, MUTED, SIDEBAR, SIDEBAR_ACTIVE, SIDEBAR_TEXT,
                    STATUS_COLORS, STATUS_SOFT, SURFACE, SOFT, ROW_HEIGHT, Surface, mark, status_icon, status_image)


class DesktopLayout:
    def setup_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), foreground=INK, background=SURFACE)
        style.configure("TFrame", background=SURFACE)
        style.configure("TLabel", background=SURFACE, foreground=INK)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("TButton", padding=self.px((14, 7)), relief="flat", borderwidth=self.px(1),
                        background=CONTROL, foreground=INK, bordercolor=CONTROL, lightcolor=CONTROL, darkcolor=CONTROL,
                        focuscolor=ACCENT, focusthickness=self.px(1), font=("Segoe UI Semibold", 10))
        style.map("TButton", background=[("disabled", SOFT), ("pressed", "#d9ddee"), ("active", "#e3e6f4")],
                  foreground=[("disabled", "#a3a9be")],
                  bordercolor=[("disabled", SOFT), ("focus", ACCENT), ("active", "#d9ddee")],
                  lightcolor=[("disabled", SOFT), ("active", "#e3e6f4")], darkcolor=[("disabled", SOFT), ("active", "#e3e6f4")])
        style.configure("Primary.TButton", background=ACCENT, foreground="white", bordercolor=ACCENT,
                        lightcolor=ACCENT, darkcolor=ACCENT, focuscolor="white", padding=self.px((22, 9)))
        style.map("Primary.TButton", background=[("disabled", "#d6d8f2"), ("pressed", ACCENT_DARK), ("active", "#4338ca")],
                  foreground=[("disabled", "#8a8fbf"), ("!disabled", "white")],
                  bordercolor=[("disabled", "#d6d8f2"), ("focus", ACCENT_DARK), ("!focus", ACCENT)],
                  lightcolor=[("disabled", "#d6d8f2"), ("active", "#4338ca")], darkcolor=[("disabled", "#d6d8f2"), ("active", "#4338ca")])
        style.configure('Quiet.TButton', background=SURFACE, foreground=ACCENT, bordercolor=SURFACE,
                        lightcolor=SURFACE, darkcolor=SURFACE, borderwidth=0, padding=self.px((10, 7)))
        style.map('Quiet.TButton', background=[('disabled', SURFACE), ('pressed', '#e2e5fb'), ('active', ACCENT_SOFT)],
                  foreground=[('disabled', '#a3a9be'), ('active', ACCENT_DARK)],
                  bordercolor=[('disabled', SURFACE), ('focus', ACCENT), ('active', ACCENT_SOFT)],
                  lightcolor=[('disabled', SURFACE), ('active', ACCENT_SOFT)], darkcolor=[('disabled', SURFACE), ('active', ACCENT_SOFT)])
        style.configure('Scope.TButton', background=BG, foreground=ACCENT, bordercolor=BG, lightcolor=BG, darkcolor=BG, borderwidth=0)
        style.map('Scope.TButton', background=[('disabled', BG), ('active', ACCENT_SOFT)], bordercolor=[('disabled', BG), ('active', ACCENT_SOFT)],
                  lightcolor=[('disabled', BG), ('active', ACCENT_SOFT)], darkcolor=[('disabled', BG), ('active', ACCENT_SOFT)],
                  foreground=[('disabled', '#a3a9be'), ('active', ACCENT_DARK)])
        style.layout('Side.TRadiobutton', style.layout('TButton'))
        style.configure('Side.TRadiobutton', background=SIDEBAR, foreground=SIDEBAR_TEXT, anchor='w',
                        borderwidth=0, relief='flat', padding=self.px((14, 10)), bordercolor=SIDEBAR,
                        lightcolor=SIDEBAR, darkcolor=SIDEBAR, font=('Segoe UI Semibold', 10), focuscolor=ACCENT)
        style.map('Side.TRadiobutton',
                  background=[('selected', SIDEBAR_ACTIVE), ('active', '#1d2440')],
                  lightcolor=[('selected', SIDEBAR_ACTIVE), ('active', '#1d2440')],
                  darkcolor=[('selected', SIDEBAR_ACTIVE), ('active', '#1d2440')],
                  bordercolor=[('focus', ACCENT), ('selected', SIDEBAR_ACTIVE), ('active', '#1d2440')],
                  foreground=[('disabled', '#4f5779'), ('selected', 'white'), ('active', 'white')])
        style.layout('Side.TButton', style.layout('TButton'))
        style.configure('Side.TButton', background=SIDEBAR, foreground=SIDEBAR_TEXT, anchor='w', borderwidth=0,
                        bordercolor=SIDEBAR, lightcolor=SIDEBAR, darkcolor=SIDEBAR, padding=self.px((14, 10)),
                        font=('Segoe UI Semibold', 10), focuscolor=ACCENT)
        style.map('Side.TButton', background=[('active', '#1d2440')], foreground=[('active', 'white')],
                  lightcolor=[('active', '#1d2440')], darkcolor=[('active', '#1d2440')], bordercolor=[('focus', ACCENT), ('active', '#1d2440')])
        style.configure('Canvas.TFrame', background=BG)
        style.configure('Canvas.TLabel', background=BG, foreground=MUTED)
        style.configure('Summary.TFrame', background=SOFT)
        style.configure('Summary.TLabel', background=SOFT)
        style.configure('Title.TLabel', font=('Segoe UI Semibold', 22), background=BG, foreground=INK)
        style.configure('Section.TLabel', font=('Segoe UI Semibold', 12))
        style.configure('TNotebook', background=BG, borderwidth=0, tabmargins=self.px((0, 0, 0, 10)))
        style.configure('TNotebook.Tab', background=BG, foreground=MUTED, padding=self.px((20, 8)), font=('Segoe UI Semibold', 10), borderwidth=0)
        style.map('TNotebook.Tab', background=[('selected', SURFACE), ('active', ACCENT_SOFT)], foreground=[('selected', ACCENT), ('active', INK)])
        style.layout('Flat.TNotebook.Tab', [])
        style.configure('Flat.TNotebook', background=SURFACE, borderwidth=0, bordercolor=SURFACE, lightcolor=SURFACE, darkcolor=SURFACE, tabmargins=0)
        style.configure('TLabelframe', background=SURFACE, bordercolor=LINE, relief='solid', borderwidth=1)
        style.configure('TLabelframe.Label', background=SURFACE, foreground=ACCENT, font=('Segoe UI Semibold', 11))
        style.layout("Segment.TRadiobutton", style.layout("TButton"))
        style.configure("Segment.TRadiobutton", padding=self.px((16, 7)), relief="flat", borderwidth=self.px(0),
                        background=CONTROL, foreground=MUTED, bordercolor=CONTROL, lightcolor=CONTROL, darkcolor=CONTROL,
                        font=("Segoe UI Semibold", 10), focuscolor=ACCENT)
        style.map("Segment.TRadiobutton", background=[("selected", ACCENT_SOFT), ("active", "#e5e8f4")],
                  lightcolor=[("selected", ACCENT_SOFT), ("active", "#e5e8f4")], darkcolor=[("selected", ACCENT_SOFT), ("active", "#e5e8f4")],
                  bordercolor=[("focus", ACCENT), ("selected", ACCENT_SOFT), ("active", "#e5e8f4")],
                  foreground=[("disabled", "#a3a9be"), ("selected", ACCENT), ("active", INK)])
        style.configure("TCheckbutton", background=SURFACE, foreground=INK, focuscolor=ACCENT,
                        indicatorbackground=SURFACE, indicatorforeground=ACCENT, indicatormargin=self.px((0, 0, 6, 0)))
        style.map("TCheckbutton", background=[("disabled", SURFACE), ("active", SURFACE)],
                  foreground=[("disabled", "#a3a9be")], indicatorbackground=[("disabled", SOFT), ("selected", ACCENT_SOFT)])
        for name in ("TEntry", "TCombobox", "TSpinbox"):
            style.configure(name, padding=self.px((8, 6)), fieldbackground=SURFACE, background=SURFACE,
                            bordercolor="#d4d9e7", lightcolor=SURFACE, darkcolor=SURFACE, arrowcolor=MUTED,
                            selectbackground=ACCENT_SOFT, selectforeground=INK, insertcolor=INK, borderwidth=self.px(1))
            style.map(name, bordercolor=[("focus", ACCENT), ("hover", "#b9c0d6")], lightcolor=[("focus", ACCENT)],
                      darkcolor=[("focus", ACCENT)], fieldbackground=[("readonly", SURFACE), ("disabled", SOFT)],
                      foreground=[("disabled", "#a3a9be"), ("readonly", INK)])
        style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, rowheight=self.px(ROW_HEIGHT),
                        borderwidth=self.px(0), relief="flat", font=("Segoe UI", 10))
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        style.layout('Treeview.Item', [('Treeitem.padding', {'sticky': 'nswe', 'children': [
            ('Treeitem.image', {'side': 'left', 'sticky': ''}), ('Treeitem.text', {'side': 'left', 'sticky': ''})]})])
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), foreground=MUTED,
                        background=SOFT, borderwidth=self.px(0), relief="flat", padding=self.px((8, 7)))
        style.map("Treeview.Heading", background=[("active", CONTROL)])
        style.map("Treeview", background=[("selected", ACCENT_SOFT)], foreground=[("selected", INK)])
        style.configure("Vertical.TScrollbar", background="#d3d8e6", troughcolor=SURFACE,
                        arrowcolor=MUTED, bordercolor=SURFACE, lightcolor="#d3d8e6", darkcolor="#d3d8e6", borderwidth=self.px(0), relief="flat", width=self.px(8))
        style.map("Vertical.TScrollbar", background=[("active", "#b9c0d6")])
        style.layout("Vertical.TScrollbar", [("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        style.configure('Horizontal.TScrollbar', background="#d3d8e6", troughcolor=SURFACE, borderwidth=0, arrowsize=self.px(10))
        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=ACCENT_SOFT, borderwidth=self.px(0), bordercolor=ACCENT_SOFT,
                        lightcolor=ACCENT, darkcolor=ACCENT, thickness=self.px(4))
        style.configure("TSeparator", background=LINE)

    def build(self):
        self._compact_layout = None
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.build_sidebar()

        outer = tk.Frame(self.root, bg=BG, padx=self.px(24), pady=self.px(16))
        outer.grid(row=0, column=1, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(5, weight=1)
        heading = tk.Frame(outer, bg=BG)
        heading.grid(row=0, column=0, sticky="ew", pady=self.px((0, 10)))
        tk.Label(heading, text="Kontrola webu", bg=BG, fg=INK, font=("Segoe UI Semibold", 19)).pack(side='left')
        tk.Label(heading, text='Zadejte web, spusťte kontrolu a projděte nálezy od těch nejdůležitějších.',
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(side='left', anchor='s', padx=self.px(14), pady=self.px((0, 5)))

        self.input_panel = Surface(outer, height=108, padding=16, radius=14, fit_height=True)
        self.input_panel.grid(row=1, column=0, sticky="ew", pady=self.px((0, 12)))
        inputs = self.input_panel.body
        modes = tk.Frame(inputs, bg=SURFACE)
        modes.pack(fill="x", pady=self.px((0, 10)))
        self.mode_question = tk.Label(modes, text='Co chcete zkontrolovat?', bg=SURFACE, fg=INK, font=('Segoe UI Semibold', 11))
        self.mode_question.pack(side='left', padx=self.px((0, 14)))
        segments = tk.Frame(modes, bg=CONTROL, padx=self.px(3), pady=self.px(3))
        self.mode_segments = segments
        segments.pack(side="left")
        self.mode_buttons = []
        for label, value in (("🌐  Webová adresa", "URL"), ("📁  Soubory webu", "Soubory")):
            button = ttk.Radiobutton(segments, text=label, variable=self.mode, value=value,
                                     style="Segment.TRadiobutton", command=self.switch_mode, takefocus=True)
            button.pack(side="left")
            self.mode_buttons.append(button)
        self.render_check = ttk.Checkbutton(modes, text='Včetně JavaScriptu', variable=self.rendering)
        self.limit_input = ttk.Spinbox(modes, from_=1, to=1000, width=5, textvariable=self.limit)
        self.limit_input.pack(side="right")
        ttk.Label(modes, text="Max. stránek", style="Muted.TLabel", font=("Segoe UI", 10)).pack(side="right", padx=self.px((8, 8)))
        ttk.Separator(modes, orient='vertical').pack(side='right', fill='y', padx=self.px(16), pady=self.px(4))
        self.render_check.pack(side='right')

        self.source_row = tk.Frame(inputs, bg=SURFACE)
        self.source_row.pack(fill="x")
        self.start_button = ttk.Button(self.source_row, text="Spustit kontrolu  →", style="Primary.TButton", command=self.start)
        self.start_button.pack(side="right", padx=self.px((12, 0)))
        self.stop_button = ttk.Button(self.source_row, text="■  Zastavit", command=self.stop, state="disabled")
        self.source_slot = tk.Frame(self.source_row, bg=SURFACE)
        self.source_slot.pack(side="left", fill="x", expand=True)
        self.url_frame = tk.Frame(self.source_slot, bg=SURFACE)
        self.url_frame.pack(fill="x")
        self.url_entry = ttk.Entry(self.url_frame, textvariable=self.url, font=("Segoe UI", 12))
        self.url_entry.pack(fill="x", expand=True, ipady=self.px(2))
        self.url_entry.bind("<Return>", lambda _: self.start())
        self.url_entry.focus_set()
        self.files_frame = tk.Frame(self.source_slot, bg=SURFACE)
        self.file_entry = ttk.Entry(self.files_frame, textvariable=self.path, font=("Segoe UI", 11))
        self.file_entry.pack(side="left", fill="x", expand=True, ipady=self.px(2))
        self.file_button = ttk.Button(self.files_frame, text="Vybrat soubor…", command=self.choose_file)
        self.file_button.pack(side="left", padx=self.px((8, 0)))
        self.folder_button = ttk.Button(self.files_frame, text="Vybrat složku…", command=self.choose_folder)
        self.folder_button.pack(side="left", padx=self.px((8, 0)))
        self.hint = ttk.Label(inputs, text="Například https://www.vasweb.cz  ·  Prochází stránky stejného webu.", style="Muted.TLabel", font=("Segoe UI", 9))
        # Local-file help is shown only in file mode; the URL field is self-explanatory.
        self.progress = ttk.Progressbar(inputs, mode="indeterminate")
        self.activity_label = ttk.Label(inputs, style='Muted.TLabel', wraplength=self.px(800))
        self.resume_bar = ttk.Frame(inputs)
        self.resume_button = ttk.Button(self.resume_bar, text='Pokračovat v kontrole', command=self.resume_audit)
        self.resume_button.pack(side='right', padx=self.px((10, 0)))
        self.resume_label = ttk.Label(self.resume_bar, style='Muted.TLabel', wraplength=self.px(650))
        self.resume_label.pack(side='left', fill='x', expand=True)
        inputs.bind('<Configure>', lambda event: (
            self.activity_label.configure(wraplength=max(self.px(200), event.width)),
            self.resume_label.configure(wraplength=max(self.px(200), event.width-self.px(230)))), add='+')

        self.error_banner = tk.Label(outer, bg="#fdecec", fg="#a4262c", padx=self.px(16), pady=self.px(11),
                                     font=("Segoe UI Semibold", 10), anchor="w", justify="left", wraplength=self.px(1000),
                                     highlightthickness=self.px(1), highlightbackground="#f6c8c9")
        # Error is inserted above the results without covering the form.
        self.error_banner.grid(row=2, column=0, sticky="ew", pady=self.px((0, 12)))
        self.error_banner.grid_remove()

        cards = tk.Frame(outer, bg=BG)
        cards.grid(row=3, column=0, sticky="ew")
        self.count_labels = {}
        self.stat_panels = {}
        captions = {"Chyba": ("Chyby", "Opravte nejdříve"), "Doporučení": ("Doporučení", "Prostor pro zlepšení"),
                    "Správně": ("V pořádku", "Splněné kontroly"), "Neověřeno": ("Neověřeno", "K ručnímu ověření")}
        for index, status in enumerate(STATUSES):
            cards.columnconfigure(index, weight=1, uniform="stats")
            card = Surface(cards, height=64, padding=12, radius=12, fit_height=True, background=BG)
            card.grid(row=0, column=index, sticky="ew", padx=self.px((0 if index == 0 else 6, 0 if index == 3 else 6)))
            label, caption = captions[status]
            icon = status_icon(card.body, status, size=34)
            icon.pack(side='left', padx=self.px((0, 12)))
            line = tk.Frame(card.body, bg=SURFACE)
            line.pack(side='left', fill='x', expand=True)
            caption_label = tk.Label(line, text=label, bg=SURFACE, fg=STATUS_COLORS[status], font=("Segoe UI Semibold", 10), pady=0)
            caption_label.pack(anchor='w')
            value = tk.Label(line, text="—", font=("Segoe UI Semibold", 20), fg=INK, bg=SURFACE, pady=0)
            value.pack(side='left', anchor='w')
            hint = tk.Label(line, text=caption, font=("Segoe UI", 9), fg=MUTED, bg=SURFACE, pady=0)
            hint.full_text = caption
            hint.pack(side='left', anchor='s', padx=self.px((8, 0)), pady=self.px((0, 6)))
            for widget in (card, card.body, caption_label, line, value, hint, icon):
                widget.configure(cursor='hand2')
                widget.bind('<Button-1>', lambda event, s=status: self.quick_filter(s))
            card.configure(takefocus=True)
            card.bind('<Return>', lambda event, s=status: self.quick_filter(s))
            card.bind('<space>', lambda event, s=status: self.quick_filter(s))
            card.bind('<FocusIn>', lambda event, c=card: c.itemconfigure('surface', outline=ACCENT, width=2))
            card.bind('<FocusOut>', lambda event, c=card: (c.itemconfigure('surface', width=1), self.highlight_filter()))
            self.count_labels[status] = value
            self.stat_panels[status] = (card, (caption_label, line, value, hint, icon))
        scope_row = tk.Frame(outer, bg=BG)
        scope_row.grid(row=4, column=0, sticky='ew', pady=self.px((4, 8)))
        tk.Label(scope_row, textvariable=self.scope_label, bg=BG, fg=MUTED, font=('Segoe UI', 9)).pack(side='left', padx=self.px((2, 0)))
        tk.Label(scope_row, text='Tip: kliknutím na kartu vyfiltrujete nálezy.', bg=BG, fg=MUTED, font=('Segoe UI', 9)).pack(side='right')
        self.scope_button = ttk.Button(scope_row, text='Zobrazit rozsah →', style='Scope.TButton', padding=self.px((8, 2)), command=self.open_summary, state='disabled')
        self.scope_button.pack(side='left', padx=self.px(6))

        self.workspace = tk.Frame(outer, bg=BG)
        self.workspace.grid(row=5, column=0, sticky="nsew")
        self.workspace.columnconfigure(0, weight=1)
        self.workspace.columnconfigure(1, weight=0)
        self.workspace.rowconfigure(0, weight=1)
        self.results_panel = Surface(self.workspace, padding=16, radius=14)
        self.results_panel.grid(row=0, column=0, sticky="nsew")
        results = self.results_panel.body
        results.columnconfigure(0, weight=1)
        results.rowconfigure(3, weight=1)
        result_header = tk.Frame(results, bg=SURFACE)
        result_header.grid(row=0, column=0, sticky="ew")
        self.results_heading = ttk.Label(result_header, text="Výsledky kontroly", font=("Segoe UI Semibold", 14))
        self.results_heading.pack(side="left")
        self.export_button = ttk.Button(result_header, text="⤓  Exportovat", command=self.export, state="disabled")
        self.export_button.pack(side="right")
        self.summary_button = ttk.Button(result_header, text='Shrnutí', style='Quiet.TButton', command=self.open_summary, state='disabled')
        self.summary_button.pack(side='right', padx=self.px((4, 8)))
        self.pages_button = ttk.Button(result_header, text='Stránky', style='Quiet.TButton', command=self.open_pages, state='disabled')
        self.pages_button.pack(side='right')
        self.subtitle_label = ttk.Label(results, textvariable=self.subtitle, style="Muted.TLabel", font=("Segoe UI", 10))
        # Reserve the second header line for an in-progress audit or a failed retry.
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=self.px((2, 6)))
        self.subtitle_label.grid_remove()
        results.bind("<Configure>", lambda event: self.subtitle_label.configure(wraplength=max(self.px(300), event.width)))
        filters = tk.Frame(results, bg=SURFACE)
        filters.grid(row=2, column=0, sticky="ew", pady=self.px((8, 8)))
        self.filters_row = filters
        filters.columnconfigure(0, weight=1)
        search_box = tk.Frame(filters, bg=SURFACE)
        self.search_box = search_box
        search_box.grid(row=0, column=0, sticky='ew', padx=self.px((0, 8)))
        self.search_entry = ttk.Entry(search_box, textvariable=self.search, width=14)
        self.search_entry.pack(side='left', fill='x', expand=True)
        search_icon = tk.Label(self.search_entry, text='⌕', bg=SURFACE, fg=MUTED, font=('Segoe UI Symbol', 11), cursor='xterm')
        search_icon.place(relx=1, rely=.5, x=-self.px(8), anchor='e')
        search_icon.bind('<Button-1>', lambda event: self.search_entry.focus_set())
        self.search_entry.bind('<KeyRelease>', self.refresh)
        self.root.bind('<Control-f>', lambda event: self.search_entry.focus_set())
        self.filter_input = ttk.Combobox(filters, textvariable=self.status_filter, values=("Všechny stavy",) + STATUSES, state="disabled", width=14, font=("Segoe UI", 10))
        self.filter_input.grid(row=0, column=1, padx=self.px((0, 8)))
        self.filter_input.bind("<<ComboboxSelected>>", self.refresh)
        self.page_input = ttk.Combobox(filters, textvariable=self.page_filter, values=("Všechny stránky",), state="disabled", width=16, font=("Segoe UI", 10))
        self.page_input.grid(row=0, column=2)
        self.page_input.bind("<<ComboboxSelected>>", self.refresh)
        self.reset_button = ttk.Button(filters, text='Zrušit filtry', style='Quiet.TButton', command=self.reset_filters)
        self.reset_button.grid(row=0, column=3, padx=self.px((6, 0)))
        list_footer = ttk.Frame(results)
        list_footer.grid(row=4, column=0, sticky='ew', pady=self.px((10, 0)))
        self.result_count = ttk.Label(list_footer, text='Výsledky se zobrazí po kontrole.', style='Muted.TLabel', font=('Segoe UI', 9))
        self.result_count.pack(side='left')
        ttk.Label(list_footer, text='Ctrl + F  hledat', style='Muted.TLabel', font=('Segoe UI', 9)).pack(side='right')

        self.table_frame = tk.Frame(results, bg=SURFACE, highlightthickness=self.px(1), highlightbackground=LINE, highlightcolor=LINE)
        self.table_frame.grid(row=3, column=0, sticky="nsew")
        self.table_frame.columnconfigure(0, weight=1)
        self.table_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(self.table_frame, columns=("status", "check", "page"), show="tree headings", selectmode="browse", height=5)
        self.tree.column('#0', width=self.px(30), minwidth=self.px(30), stretch=False)
        self.status_images = {status: status_image(self.root, status) for status in STATUSES}
        for key, label, width, minimum in (("status", "STAV", 110, 85), ("check", "NÁLEZ", 280, 140), ("page", "STRÁNKA", 180, 100)):
            self.tree.heading(key, text=label, anchor="w")
            self.tree.column(key, width=self.px(width), minwidth=self.px(minimum), stretch=key != 'status', anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind('<Configure>', self.resize_result_columns)
        scroll = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)
        for status, color in STATUS_COLORS.items():
            self.tree.tag_configure(status, foreground=INK)
        self.tree.tag_configure("alternate", background="#fafbfe")
        self.tree.bind("<<TreeviewSelect>>", self.show_detail)
        self.tree.bind("<ButtonRelease-1>", self.open_page_cell)
        self.tree.bind("<Return>", lambda event: self.open_pages())

        self.empty = tk.Frame(results, bg=SURFACE)
        self.empty.grid(row=3, column=0, sticky="nsew")
        center = tk.Frame(self.empty, bg=SURFACE)
        center.place(relx=.5, rely=.46, anchor="center")
        mark(center, 56).pack(pady=self.px((0, 16)))
        self.empty_title = tk.Label(center, text="Tady začíná lepší web", bg=SURFACE, fg=INK, font=("Segoe UI Semibold", 16))
        self.empty_title.pack()
        self.empty_copy = tk.Label(center, text="Zadejte adresu nebo vyberte soubory.\nUkážeme vám nálezy i doporučené opravy.", bg=SURFACE, fg=MUTED,
                                   font=("Segoe UI", 11), justify="center", wraplength=self.px(390))
        self.empty_copy.pack(pady=self.px((6, 0)))
        self.empty_steps = tk.Frame(center, bg=SURFACE)
        self.empty_steps.pack(pady=self.px((22, 0)))
        for number, text in enumerate(('Zadejte web', 'Spusťte kontrolu', 'Opravte nálezy'), 1):
            step = tk.Frame(self.empty_steps, bg=SURFACE)
            step.pack(side='left', padx=self.px(12))
            tk.Label(step, text=str(number), bg=ACCENT_SOFT, fg=ACCENT, font=('Segoe UI Semibold', 10),
                     width=2, padx=self.px(2)).pack(side='left', padx=self.px((0, 8)))
            tk.Label(step, text=text, bg=SURFACE, fg=INK, font=('Segoe UI', 10)).pack(side='left')

        self.inspector = Surface(self.workspace, color=SURFACE, width=330, padding=20, radius=14)
        self.inspector.grid(row=0, column=1, sticky="nsew", padx=self.px((12, 0)))
        self.inspector.grid_remove()
        inspector = self.inspector.body
        detail_header = ttk.Frame(inspector)
        detail_header.pack(fill='x', pady=self.px((0, 10)))
        self.detail_status = tk.Label(detail_header, text="Detail nálezu", bg=ACCENT_SOFT, fg=ACCENT, font=("Segoe UI Semibold", 9), padx=self.px(10), pady=self.px(3))
        self.detail_status.pack(side='left')
        ttk.Button(detail_header, text='✕', width=2, padding=self.px((2, 0)), style='Quiet.TButton', command=self.inspector.grid_remove).pack(side='right')
        actions = ttk.Frame(inspector)
        actions.pack(side='bottom', fill='x', pady=self.px((14, 0)))
        ttk.Separator(actions).pack(fill='x', pady=self.px((0, 12)))
        self.open_page_button = ttk.Button(actions, text='Otevřít stránku ↗', command=self.open_selected_page, state='disabled')
        self.open_page_button.pack(side='left')
        self.copy_button = ttk.Button(actions, text='Kopírovat URL', style='Quiet.TButton', command=self.copy_page, state='disabled')
        self.copy_button.pack(side='right')
        self.detail = tk.Text(inspector, height=8, width=1, wrap="word", background=SURFACE, foreground=INK,
                              relief="flat", bd=0, highlightthickness=self.px(0), padx=self.px(0), pady=self.px(0),
                              font=("Segoe UI", 10), spacing1=self.px(0), spacing3=self.px(3), cursor="arrow")
        self.detail.pack(side="left", fill="both", expand=True)
        detail_scroll = ttk.Scrollbar(inspector, command=self.detail.yview)
        detail_scroll.pack(side="right", fill="y")
        self.detail.configure(yscrollcommand=detail_scroll.set)
        self.detail.tag_configure("heading", font=("Segoe UI Semibold", 15), spacing3=self.px(6))
        self.detail.tag_configure("adviceheading", foreground=ACCENT, font=("Segoe UI Semibold", 11), spacing1=self.px(4), spacing3=self.px(4))
        self.detail.tag_configure("advice", foreground=INK, spacing3=self.px(8), lmargin1=self.px(10), lmargin2=self.px(10))
        self.detail.tag_configure('code', font=('Consolas', 10), background=SOFT, foreground="#3b4160",
                                  lmargin1=self.px(10), lmargin2=self.px(10), rmargin=self.px(8), spacing1=self.px(8), spacing3=self.px(8))
        self.detail.tag_configure("muted", foreground=MUTED, font=("Segoe UI", 9), spacing3=self.px(8))
        self.set_detail("Vyberte nález", "Tady uvidíte, co se našlo a jak to opravit.", "Po kontrole začněte chybami nebo otevřete Plán oprav.")

        footer = tk.Frame(outer, bg=BG)
        footer.grid(row=6, column=0, sticky="ew", pady=self.px((10, 0)))
        tk.Label(footer, text='●', bg=BG, fg=ACCENT, font=('Segoe UI', 8)).pack(side='left', padx=self.px((2, 6)))
        self.status_label = tk.Label(footer, textvariable=self.status, bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w", justify="left")
        self.status_label.pack(side='left', fill='x', expand=True)
        from .diagnostics import copy_diagnostic
        self.diagnostic_button = ttk.Button(footer, text='Kopírovat diagnostiku', style='Quiet.TButton',
                                           command=lambda: copy_diagnostic(self.root, self.last_diagnostic))
        self.root.bind("<Configure>", self.resize_content)

    def build_sidebar(self):
        sidebar = tk.Frame(self.root, bg=SIDEBAR, width=self.px(212), padx=self.px(12), pady=self.px(18))
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.pack_propagate(False)
        brand = tk.Frame(sidebar, bg=SIDEBAR)
        brand.pack(fill='x', padx=self.px(6), pady=self.px((0, 28)))
        mark(brand, 34, background=SIDEBAR).pack(side="left", padx=self.px((0, 10)))
        names = tk.Frame(brand, bg=SIDEBAR)
        names.pack(side='left')
        tk.Label(names, text="Kontrola SEO", bg=SIDEBAR, fg="white", font=("Segoe UI Semibold", 13), pady=0).pack(anchor='w')
        tk.Label(names, text="Technické SEO", bg=SIDEBAR, fg=SIDEBAR_TEXT, font=("Segoe UI", 9), pady=0).pack(anchor='w')
        tk.Label(sidebar, text="PRACOVNÍ PROSTOR", bg=SIDEBAR, fg="#646c8f", font=("Segoe UI Semibold", 8)).pack(anchor='w', padx=self.px(8), pady=self.px((0, 6)))
        self.main_section = tk.IntVar(master=self.root, value=0)
        ttk.Radiobutton(sidebar, text='▦   Přehled', variable=self.main_section, value=0,
                        style='Side.TRadiobutton', command=lambda: self.main_section.set(0)).pack(fill='x', pady=self.px(2))
        self.plan_button = ttk.Radiobutton(sidebar, text='✓   Plán oprav', variable=self.main_section, value=1,
                                           style='Side.TRadiobutton', command=self.open_plan, state='disabled')
        self.plan_button.pack(fill='x', pady=self.px(2))
        ttk.Radiobutton(sidebar, text='◷   Projekty a historie', variable=self.main_section, value=2,
                        style='Side.TRadiobutton', command=self.open_history).pack(fill='x', pady=self.px(2))
        ttk.Radiobutton(sidebar, text='⚡   Rychlost a Google', variable=self.main_section, value=3,
                        style='Side.TRadiobutton', command=self.open_insights).pack(fill='x', pady=self.px(2))
        bottom = tk.Frame(sidebar, bg=SIDEBAR)
        bottom.pack(side='bottom', fill='x')
        self.save_hint = tk.Label(bottom, text='Zadání se ukládá automaticky' if self.store else 'Ukládání zadání není dostupné',
                                  bg=SIDEBAR, fg="#646c8f", font=('Segoe UI', 8), anchor='w', justify='left', wraplength=self.px(180))
        self.save_hint.pack(side='bottom', fill='x', padx=self.px(8), pady=self.px((12, 0)))
        ttk.Button(bottom, text='⚙   Nastavení', style='Side.TButton', command=self.open_settings).pack(side='bottom', fill='x')
        tk.Frame(bottom, bg="#232a45", height=self.px(1)).pack(side='bottom', fill='x', pady=self.px((0, 10)))

    def resize_result_columns(self, event):
        available = event.width - self.px(144)
        check_width = max(self.px(140), int(available * .62))
        self.tree.column('check', width=check_width)
        self.tree.column('page', width=max(self.px(100), available - check_width))

    def resize_content(self, event):
        if event.widget == self.root:
            width = self.root.winfo_width()
            compact = width < self.px(1280)
            if getattr(self, '_compact_layout', None) != compact:
                self._compact_layout = compact
                if compact:
                    self.mode_question.pack_forget()
                else:
                    self.mode_question.pack(side='left', before=self.mode_segments, padx=self.px((0, 14)))
                for card, widgets in self.stat_panels.values():
                    hint = widgets[3]
                    hint.configure(text='' if compact else hint.full_text)
                self.results_heading.configure(font=('Segoe UI Semibold', 12 if compact else 14))
                self.search_box.grid_configure(row=0, column=0, columnspan=3 if compact else 1,
                                               pady=self.px((0, 6 if compact else 0)),
                                               padx=self.px((0, 0 if compact else 8)))
                self.filter_input.grid_configure(row=1 if compact else 0, column=0 if compact else 1, sticky='ew')
                self.page_input.grid_configure(row=1 if compact else 0, column=1 if compact else 2, sticky='ew')
                self.reset_button.grid_configure(row=1 if compact else 0, column=2 if compact else 3)
            self.status_label.configure(wraplength=max(self.px(300), width-self.px(500)))
            self.error_banner.configure(wraplength=max(self.px(400), width-self.px(320)))
            self.inspector.configure(width=self.px(320 if width < self.px(1280) else 360))

    def highlight_filter(self):
        for status, (card, widgets) in self.stat_panels.items():
            active = self.status_filter.get() == status
            color = STATUS_SOFT[status] if active else SURFACE
            card.set_color(color, STATUS_COLORS[status] if active else LINE)
            for widget in widgets:
                widget.configure(bg=color)

    def show_error(self, message):
        self.error_banner.configure(text=message)
        self.error_banner.grid()

    def clear_error(self):
        self.error_banner.grid_remove()

    def show_empty(self, title, copy):
        self.empty_title.configure(text=title)
        self.empty_copy.configure(text=copy)
        self.empty_steps.pack_forget()
        self.empty.grid()
