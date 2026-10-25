from __future__ import annotations

import queue
import threading
import webbrowser
import tkinter as tk
from urllib.parse import urlsplit
from tkinter import filedialog, messagebox, simpledialog

from .engine import STATUSES, audit_local, audit_url
from .export import save_report
from .dpi import enable_high_dpi, pixels, window_dpi, work_area

from .theme import BG, STATUS_COLORS, STATUS_SOFT, readable
from .ui import DesktopLayout
from .storage import Store
from .planning import compare_reports
from .reporting import audit_summary, problem_line, browser_url
from .diagnostics import diagnose, copy_diagnostic


class Application(DesktopLayout):
    def __init__(self, root, database=None):
        self.root = root
        self.report = None
        self.running = False
        self.worker_thread = None
        self.recheck_view = None
        self.closing = False
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.rows = {}
        self.project_id = None
        self.audit_id = None
        self.insights_window = None
        self.plan_window = None
        self.history_window = None
        self.page_window = None
        self.summary_window = None
        self.export_window = None
        self.storage_error = ""
        self.last_diagnostic = None
        try:
            self.store = Store(database)
        except Exception as exc:
            self.store = None
            self.storage_error = f"Historie není dostupná: {exc}. Výsledky můžete exportovat."
        self.mode = tk.StringVar(value="URL")
        self.url = tk.StringVar()
        self.path = tk.StringVar()
        self.limit = tk.StringVar(value="100")
        self.rendering = tk.BooleanVar(value=False)
        self.status_filter = tk.StringVar(value="Všechny stavy")
        self.search = tk.StringVar()
        self.page_filter = tk.StringVar(value="Všechny stránky")
        self.scope_label = tk.StringVar(value='Zkontrolujte web. Vyberte opravy. Sledujte změny.')
        self.status = tk.StringVar(value="Připraveno ke kontrole")
        self.subtitle = tk.StringVar(value="Všechny nálezy na jednom místě.")
        self._input_after = None
        self._input_dirty = False
        self.input_variables = {'mode': self.mode, 'url': self.url, 'path': self.path,
                                'limit': self.limit, 'rendering': self.rendering}
        self.restore_inputs()
        for variable in self.input_variables.values():
            variable.trace_add('write', self.inputs_changed)
        root.title("Kontrola SEO")
        self.dpi = window_dpi(root)
        root.dpi_scale = self.dpi / 96
        root.tk.call("tk", "scaling", self.dpi / 72)
        self.configure_window_size(initial=True)
        root.configure(background=BG)
        self.setup_style()
        self.build()
        self.refresh_draft()
        self.switch_mode()
        if self.mode.get() == 'Soubory':
            self.file_entry.focus_set()
        if self.storage_error:
            self.show_error(self.storage_error)
        self._poll_after = root.after(100, self.poll)
        self._close_after = None
        self._dpi_after = root.after(400, self.check_dpi)
        root.protocol("WM_DELETE_WINDOW", self.close)

    def restore_inputs(self):
        if not self.store:
            return
        try:
            saved = self.store.get_setting('audit_inputs')
            for name in ('url', 'path', 'limit'):
                if isinstance(saved.get(name), str):
                    self.input_variables[name].set(saved[name])
            if saved.get('mode') in ('URL', 'Soubory'):
                self.mode.set(saved['mode'])
            if isinstance(saved.get('rendering'), bool):
                self.rendering.set(saved['rendering'])
        except Exception:
            self.storage_error = 'Poslední zadání se nepodařilo obnovit. Zadejte je znovu.'

    def inputs_changed(self, *_):
        self._input_dirty = True
        if self._input_after:
            self.root.after_cancel(self._input_after)
        self._input_after = self.root.after(500, self.save_inputs)

    def save_inputs(self):
        if self._input_after:
            self.root.after_cancel(self._input_after)
            self._input_after = None
        if not self.store or not self._input_dirty:
            return
        try:
            self.store.set_setting('audit_inputs', {name: variable.get() for name, variable in self.input_variables.items()})
            self._input_dirty = False
        except Exception:
            self.status.set('Poslední zadání se nepodařilo uložit pro příští spuštění.')

    def px(self, value):
        return pixels(value, self.root.dpi_scale)

    def configure_window_size(self, initial=False):
        available_width, available_height = work_area(self.root)
        width = max(1, available_width - self.px(20))
        height = max(1, available_height - self.px(48))
        self.root.minsize(min(self.px(1060), width), min(self.px(700), height))
        if initial:
            self.root.geometry(f"{min(self.px(1280), width)}x{min(self.px(820), height)}")

    def check_dpi(self):
        dpi = window_dpi(self.root)
        if dpi != self.dpi:
            self.apply_dpi(dpi)
        self._dpi_after = self.root.after(400, self.check_dpi)

    def apply_dpi(self, dpi):
        """Recreate presentation on monitor changes; preserve audit, filters and worker."""
        if dpi <= 0 or dpi == self.dpi:
            return
        focused = self.root.focus_get()
        focus_name = next((name for name in ("url_entry", "file_entry", "limit_input", "filter_input", "page_input", "search_entry", "tree", "start_button")
                           if getattr(self, name) is focused), None)
        selection = self.tree.selection()
        selected = self.rows.get(selection[0]) if selection else None
        scroll = self.tree.yview()[0]
        subtitle = self.subtitle.get()
        error = self.error_banner.cget("text") if self.error_banner.grid_info() else ""
        self.progress.stop()
        if self.insights_window and self.insights_window.win.winfo_exists():
            self.insights_window.close()
        for widget in self.root.winfo_children():
            widget.destroy()
        self.dpi = dpi
        self.root.dpi_scale = dpi / 96
        self.root.tk.call("tk", "scaling", dpi / 72)
        self.configure_window_size()
        self.setup_style()
        self.build()
        self.refresh_draft()
        self.switch_mode()
        if self.report:
            self.page_input.configure(values=("Všechny stránky",) + tuple(page.location for page in self.report.pages), state="readonly")
            self.filter_input.configure(state="readonly")
            for name, count in self.report.counts().items():
                self.count_labels[name].configure(text=str(count))
            self.refresh()
            if selected:
                for key, value in self.rows.items():
                    if value == selected:
                        self.tree.selection_set(key)
                        self.tree.focus(key)
                        self.show_detail()
                        break
            self.tree.yview_moveto(scroll)
        self.set_running(self.running)
        self.subtitle.set(subtitle)
        if error:
            self.show_error(error)
        if focus_name:
            getattr(self, focus_name).focus_set()

    def switch_mode(self):
        self.url_frame.pack_forget()
        self.files_frame.pack_forget()
        target = self.url_frame if self.mode.get() == "URL" else self.files_frame
        target.pack(fill="x")
        self.clear_error()
        self.hint.configure(text="Například https://www.vasweb.cz  ·  Prochází stránky stejného webu." if self.mode.get() == "URL" else "HTML, složka nebo ZIP  ·  Soubory zůstávají na počítači. Max. 5 MB na HTML.")
        self.hint.pack_forget()
        if self.mode.get() != 'URL':
            self.hint.pack(anchor='w', pady=self.px((6, 0)))
        self.render_check.configure(state='normal' if self.mode.get() == 'URL' and not self.running else 'disabled')
        self.root.after_idle(lambda: self.input_panel._fit_height(None) if not self.closing else None)

    def choose_file(self):
        path = filedialog.askopenfilename(title="Vyberte web", filetypes=[("Webové soubory", "*.html *.htm *.zip"), ("Všechny soubory", "*.*")])
        if path:
            self.path.set(path)

    def choose_folder(self):
        path = filedialog.askdirectory(title="Vyberte složku s HTML soubory")
        if path:
            self.path.set(path)

    def refresh_draft(self):
        try:
            self.saved_draft = self.store.draft() if self.store else None
        except Exception as exc:
            self.saved_draft = None
            self.show_diagnostic(exc, 'storage')
        draft = self.saved_draft
        if draft:
            count = len(draft['report']['pages'])
            self.resume_label.configure(text=f"Rozpracovaná kontrola · {count} zpracovaných · {draft['source']}")
            self.resume_bar.pack(fill='x', pady=self.px((8, 0)))
        else:
            self.resume_bar.pack_forget()
        self.root.after_idle(lambda: self.input_panel._fit_height(None) if not self.closing else None)

    def resume_audit(self):
        if self.running:
            return
        self.refresh_draft()
        draft = self.saved_draft
        if not draft:
            return
        count = len(draft['report']['pages'])
        waiting = len(draft.get('queue', [])) if draft['mode'] == 'URL' else len(draft.get('manifest', [])) - count
        limit = draft['limit']
        if count >= limit and waiting:
            if count >= 1000:
                self.show_error('Rozpracovaná kontrola dosáhla limitu 1000 stránek. Další URL ověřte novým cíleným auditem.')
                return
            limit = simpledialog.askinteger('Pokračovat v kontrole', 'Celkový limit včetně již zpracovaných stránek:',
                                           initialvalue=min(1000, count+100), minvalue=count+1, maxvalue=1000, parent=self.root)
            if limit is None:
                return
        self.mode.set(draft['mode'])
        (self.url if draft['mode'] == 'URL' else self.path).set(draft['source'])
        self.rendering.set(draft.get('rendering', False))
        self.limit.set(str(limit))
        self.switch_mode()
        self.start(resume=draft)

    def start(self, resume=None):
        if self.running:
            return
        mode = self.mode.get()
        source = (self.url.get() if mode == "URL" else self.path.get()).strip()
        if not source:
            self.show_error("Zadejte URL adresu nebo vyberte soubory webu.")
            (self.url_entry if mode == "URL" else self.file_entry).focus_set()
            return
        try:
            limit = int(self.limit.get())
            if not 1 <= limit <= 1000:
                raise ValueError()
        except ValueError:
            self.show_error("Limit stránek musí být celé číslo od 1 do 1000.")
            self.limit_input.focus_set()
            return
        self.refresh_draft()
        if not resume and self.saved_draft:
            if not messagebox.askyesno('Nová kontrola', 'Nová kontrola nahradí rozpracovaný postup. Uložené audity v historii zůstanou zachované. Pokračovat?', parent=self.root):
                return
            self.store.clear_draft()
        self.clear_error()
        self.cancel = threading.Event()
        self.save_inputs()
        self.set_running(True)
        self.status.set("Spouštím kontrolu…")
        self.worker_thread = threading.Thread(target=self.worker, args=(mode, source, limit, self.cancel, self.rendering.get() and mode == 'URL', resume), daemon=True)
        self.worker_thread.start()

    def worker(self, mode, source, limit, cancel, rendering=False, resume=None):
        draft_store = None
        try:
            if self.store and self.store.path != ':memory:':
                draft_store = Store(self.store.path)
            def checkpoint(data):
                if draft_store:
                    draft_store.save_draft(data)
                elif self.store:
                    self.events.put(('checkpoint', data))
            callback = lambda message: self.events.put(("progress", message))
            fn = audit_url if mode == "URL" else audit_local
            options = {'rendering': rendering} if mode == 'URL' else {}
            options.update(resume=resume, checkpoint=checkpoint, activity=lambda data: self.events.put(('activity', data)))
            report = fn(source, limit=limit, cancel=cancel, progress=callback, **options)
            self.events.put(("done", report))
        except Exception as exc:
            self.events.put(("error", exc))
        finally:
            if draft_store:
                draft_store.close()

    def show_diagnostic(self, error, action='audit'):
        self.last_diagnostic = diagnose(error, action)
        detail = str(error) if isinstance(error, ValueError) else ''
        self.show_error(self.last_diagnostic['category'] + '\n' + detail + '\n' + self.last_diagnostic['step'])
        self.diagnostic_button.pack(side='right', padx=self.px((8, 0)))

    def start_recheck(self, view, occurrences):
        if self.running:
            return False
        if not self.store or not view.audit_id:
            raise ValueError('Nejprve uložte audit do historie. Ověření se ukládá k jeho původním nálezům.')
        self.recheck_view = view
        self.recheck_audit_id = view.audit_id
        self.cancel = threading.Event()
        self.set_running(True)
        self.status.set('Ověřuji opravy vybraných stránek; zobrazen je původní audit.')
        def worker():
            from .repairs import verify_repairs
            try:
                data = verify_repairs(view.report, occurrences, cancel=self.cancel,
                                      progress=lambda value: self.events.put(('repair-progress', value)))
                self.events.put(('repair-done', data))
            except Exception as exc:
                self.events.put(('repair-error', str(exc) or type(exc).__name__))
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()
        return True

    def finish_recheck(self, data=None, error=''):
        view = self.recheck_view
        cancelled = self.cancel.is_set()
        if data and not cancelled and not self.closing:
            try:
                self.store.save_repair_check(self.recheck_audit_id, data)
            except Exception as exc:
                error = f'Ověření proběhlo, ale výsledek se nepodařilo uložit: {exc}'
                data = None
        self.recheck_view = None
        self.set_running(False)
        message = ('Ověření zastaveno; výsledek nebyl uložen.' if cancelled else
                   error or 'Ověření oprav uloženo k původnímu auditu. Podrobnosti jsou v Plánu oprav.')
        self.status.set(message)
        if view and view.win.winfo_exists():
            view.recheck_finished(data if not cancelled and not error else None, message)

    def set_running(self, running):
        self.running = running
        self.resume_button.configure(state='disabled' if running else 'normal')
        for widget in [self.start_button, self.url_entry, self.file_entry, self.file_button, self.folder_button, self.limit_input, *self.mode_buttons]:
            widget.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        self.export_button.configure(state="normal" if self.report and not running else "disabled")
        self.plan_button.configure(state="normal" if self.report and not running else "disabled")
        for button in (self.pages_button, self.summary_button, self.scope_button):
            button.configure(state='normal' if self.report else 'disabled')
        self.render_check.configure(state='normal' if not running and self.mode.get() == 'URL' else 'disabled')
        if running:
            self.activity_label.configure(text='Připravuji kontrolu…')
            self.activity_label.pack(fill='x', pady=self.px((6, 0)))
            self.input_panel.configure(height=self.px(120))
            self.start_button.configure(text="Kontroluji…")
            self.stop_button.pack(side="right", padx=self.px((8, 0)), before=self.source_slot)
            self.progress.pack(fill="x", pady=self.px((7, 0)))
            self.progress.start(12)
            if not self.report:
                self.show_empty("Kontroluji váš web…", "Postupně procházím stránky a hledám nálezy.\nKontrolu můžete kdykoli zastavit.")
            else:
                self.subtitle.set("Probíhá nová kontrola · Zobrazen je předchozí výsledek.")
                self.subtitle_label.grid()
        else:
            self.activity_label.pack_forget()
            self.input_panel.configure(height=self.px(108))
            self.start_button.configure(text="Spustit kontrolu  →")
            self.stop_button.pack_forget()
            self.progress.stop()
            self.progress.pack_forget()
            self.subtitle_label.grid_remove()
        self.root.after_idle(lambda: self.input_panel._fit_height(None) if not self.closing else None)

    def stop(self):
        self.cancel.set()
        self.stop_button.configure(state="disabled")
        self.status.set("Zastavuji… čekám na dokončení probíhajícího požadavku.")

    def poll(self):
        if self.closing:
            return
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'repair-progress':
                    if not self.cancel.is_set():
                        self.status.set(value)
                        view = self.recheck_view
                        if view and view.win.winfo_exists():
                            view.recheck_status.configure(text=value)
                elif kind == 'repair-done':
                    self.finish_recheck(value)
                elif kind == 'repair-error':
                    self.finish_recheck(error=value)
                elif kind == "progress":
                    if not self.cancel.is_set():
                        self.status.set(value)
                elif kind == 'checkpoint':
                    if self.store:
                        try:
                            self.store.save_draft(value)
                        except Exception as exc:
                            self.cancel.set()
                            self.show_diagnostic(exc, 'storage')
                elif kind == 'activity':
                    self.activity_label.configure(text=f"Dokončeno: {value['completed']} · Čeká: {value['waiting']} · Limit: {value['limit']}\n" + value['current'])
                elif kind == "error":
                    self.set_running(False)
                    self.status.set("Kontrolu se nepodařilo dokončit." + (" Zobrazeny jsou výsledky předchozí kontroly." if self.report else ""))
                    self.show_diagnostic(value)
                    self.refresh_draft()
                    if not self.report:
                        self.show_empty("Kontrola se nezdařila", "Ověřte zdroj a zkuste kontrolu spustit znovu.\nPodrobnosti najdete nad výsledky.")
                    else:
                        self.subtitle.set("Výsledky předchozí kontroly · Novou kontrolu se nepodařilo dokončit.")
                        self.subtitle_label.grid()
                elif kind == "done":
                    self.project_id = self.audit_id = None
                    if self.store:
                        try:
                            self.project_id, self.audit_id = self.store.save(value)
                            draft = self.store.draft()
                            waiting = len(draft.get('queue', [])) if draft and draft['mode'] == 'URL' else len(draft.get('manifest', [])) - len(draft['report']['pages']) if draft else 0
                            if not self.cancel.is_set() and not waiting:
                                self.store.clear_draft()
                        except Exception as exc:
                            self.show_diagnostic(exc, 'storage')
                    self.display_report(value)
                    self.refresh_draft()
        except queue.Empty:
            pass
        self._poll_after = self.root.after(100, self.poll)

    def display_report(self, report):
        for name in ('page_window', 'summary_window'):
            view = getattr(self, name)
            if view and view.win.winfo_exists() and view.report is not report:
                view.win.destroy()
        self.report = report
        self.set_running(False)
        self.status_filter.set("Všechny stavy")
        self.search.set('')
        self.page_filter.set("Všechny stránky")
        self.page_input.configure(values=("Všechny stránky",) + tuple(page.location for page in report.pages), state="readonly")
        self.filter_input.configure(state="readonly")
        for name, count in report.counts().items():
            self.count_labels[name].configure(text=str(count))
        summary = audit_summary(report)
        self.subtitle.set(problem_line(summary) + f" · Neověřené kontroly: {summary['uncertain']}")
        self.scope_label.set(f"{summary['scope']} · {summary['visited']}/{summary['discovered']} URL/souborů")
        scope = "Dokončený zadaný rozsah." if report.complete else "Částečná kontrola — část URL nebyla ověřena."
        saved = f" Uloženo do historie, kontrola #{self.audit_id}." if self.audit_id else " Výsledek není uložen; použijte export."
        self.status.set(scope + saved)
        self.refresh()

    def open_plan(self):
        if self.report:
            self.main_section.set(1)
            if self.plan_window and self.plan_window.win.winfo_exists():
                if self.plan_window.report is self.report:
                    self.plan_window.refresh()
                    self.plan_window.win.lift()
                    return
                self.plan_window.win.destroy()
            from .workspace import PlanWindow
            self.plan_window = PlanWindow(self)
            self.main_section.set(1)

    def open_history(self):
        if self.store:
            self.main_section.set(2)
            if self.history_window and self.history_window.win.winfo_exists():
                self.history_window.load_projects()
                self.history_window.win.lift()
                return
            from .workspace import HistoryWindow
            self.history_window = HistoryWindow(self)
            self.main_section.set(2)
        else:
            self.show_error(self.storage_error or "Úložiště historie není dostupné.")

    def open_insights(self):
        self.main_section.set(3)
        if self.insights_window and self.insights_window.win.winfo_exists():
            if self.insights_window.audit_id == self.audit_id or self.insights_window.busy:
                self.insights_window.win.lift()
                return
            self.insights_window.close()
        from .insights_ui import InsightsWindow
        self.insights_window = InsightsWindow(self)
        self.main_section.set(3)

    def open_settings(self):
        self.open_insights()
        if self.insights_window:
            self.insights_window.show_settings('search')

    def load_audit(self, audit_id):
        self.project_id, report = self.store.load(audit_id)
        self.audit_id = audit_id
        self.mode.set(report.mode)
        (self.url if report.mode == "URL" else self.path).set(report.source)
        self.limit.set(str(report.limit))
        self.rendering.set(report.rendering)
        self.switch_mode()
        self.display_report(report)

    def refresh(self, event=None):
        self.tree.delete(*self.tree.get_children())
        self.rows.clear()
        if not self.report:
            return
        query = self.search.get().strip().casefold()
        self.highlight_filter()
        findings = [(page, finding) for page in self.report.pages for finding in page.findings
                    if self.status_filter.get() in ("Všechny stavy", finding.status)
                    and self.page_filter.get() in ("Všechny stránky", page.location)
                    and (not query or query in ' '.join((page.location, finding.name, finding.detail, finding.advice)).casefold())]
        findings.sort(key=lambda row: STATUSES.index(row[1].status))
        for index, (page, finding) in enumerate(findings):
            key = str(index)
            location = page.location
            if self.report.mode == 'URL':
                parts = urlsplit(location)
                if parts.netloc == urlsplit(self.report.source).netloc:
                    location = (parts.path or '/') + ('?' + parts.query if parts.query else '') + ('#' + parts.fragment if parts.fragment else '')
            self.tree.insert("", "end", iid=key, image=self.status_images[finding.status], values=('V pořádku' if finding.status == 'Správně' else finding.status, finding.name, location), tags=(finding.status, "alternate" if index % 2 else "plain"))
            self.rows[key] = (page, finding)
        total = sum(len(page.findings) for page in self.report.pages)
        self.result_count.configure(text=f'Ve výběru {len(findings)} z {total} nálezů')
        if findings:
            self.empty.grid_remove()
            self.tree.selection_set("0")
            self.tree.focus("0")
            self.show_detail()
        else:
            self.show_empty("Žádné nálezy v tomto výběru", "Zkuste vybrat jiný stav nebo jinou stránku.")
            self.set_detail("Žádné výsledky", "Pro zvolený filtr nebyly nalezeny výsledky.")
            self.copy_button.configure(state='disabled')
            self.open_page_button.configure(state='disabled')
            self.inspector.grid_remove()
            self.detail_status.configure(text='Detail nálezu')

    def quick_filter(self, status):
        if self.report:
            self.status_filter.set('Všechny stavy' if self.status_filter.get() == status else status)
            self.refresh()

    def reset_filters(self):
        self.status_filter.set('Všechny stavy')
        self.page_filter.set('Všechny stránky')
        self.search.set('')
        self.refresh()

    def copy_page(self):
        selected = self.tree.selection()
        if selected and selected[0] in self.rows:
            url = self.rows[selected[0]][0].location
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.status.set('Adresa stránky byla zkopírována.')

    def open_selected_page(self):
        selected = self.tree.selection()
        if selected and selected[0] in self.rows:
            location = self.rows[selected[0]][0].location
            if self.report.mode == 'URL' and browser_url(location):
                try:
                    if webbrowser.open(location):
                        return
                except OSError:
                    pass
                self.show_error('Stránku se nepodařilo otevřít ve výchozím prohlížeči.')

    def set_detail(self, title, text, advice="", location="", example="", url=""):
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("end", title + "\n", "heading")
        if url:
            self.detail.insert('end', url + '\n', 'muted')
        self.detail.insert("end", readable(text))
        if advice:
            self.detail.insert("end", "\n\nJak to opravit\n", "adviceheading")
            self.detail.insert("end", advice, "advice")
        if example:
            self.detail.insert('end', '\n\nPříklad — upravte podle stránky\n', 'adviceheading')
            self.detail.insert('end', example, 'code')
        if location:
            self.detail.insert("end", "\n\n" + location, "muted")
        self.detail.configure(state="disabled")

    def show_detail(self, event=None):
        selected = self.tree.selection()
        if selected and selected[0] in self.rows:
            page, finding = self.rows[selected[0]]
            self.inspector.grid()
            self.detail_status.configure(text='V pořádku' if finding.status == 'Správně' else finding.status,
                                         fg=STATUS_COLORS[finding.status], bg=STATUS_SOFT[finding.status])
            self.copy_button.configure(state='normal')
            self.open_page_button.configure(state='normal' if self.report.mode == 'URL' and browser_url(page.location) else 'disabled')
            evidence = ''
            if page.inbound:
                evidence += "\n\nOdkazuje sem:\n" + "\n".join(page.inbound)
            if page.sitemap_sources:
                evidence += "\n\nSitemapy:\n" + "\n".join(page.sitemap_sources)
            example = ''
            if finding.name == 'Meta description' and not page.description and finding.status == 'Doporučení':
                example = '<meta name="description"\n  content="Výstižný popis obsahu stránky.">'
            advice = finding.advice
            if advice and finding.status in ('Chyba', 'Doporučení'):
                advice = '1. ' + advice + '\n\n2. Po uložení změny spusťte novou kontrolu.'
            self.set_detail(finding.name, finding.detail, advice, evidence, example, page.location)

    def open_report_view(self, attribute, cls, *args):
        if not self.report:
            return
        existing = getattr(self, attribute)
        if existing and existing.win.winfo_exists():
            existing.win.destroy()
        setattr(self, attribute, cls(self, *args))

    def open_pages(self):
        from .report_ui import PageWindow
        selection = self.tree.selection()
        page = self.rows[selection[0]][0] if selection and selection[0] in self.rows else None
        self.open_report_view('page_window', PageWindow, page)

    def open_page_cell(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.show_detail()
        if row and self.tree.identify_column(event.x) == '#3':
            self.tree.selection_set(row)
            self.open_pages()

    def open_summary(self):
        from .report_ui import SummaryWindow
        self.open_report_view('summary_window', SummaryWindow)

    def export(self):
        from .report_ui import ExportWindow
        self.open_report_view('export_window', ExportWindow)

    def close(self):
        if self.closing:
            return
        self.closing = True
        self.progress.stop()
        self.root.after_cancel(self._poll_after)
        self.save_inputs()
        self.cancel.set()
        if self.insights_window and self.insights_window.win.winfo_exists():
            self.insights_window.close()
        self.root.withdraw()
        self.finish_close()

    def finish_close(self):
        if self._close_after:
            self.root.after_cancel(self._close_after)
            self._close_after = None
        # Let the rendering worker close its browser before the GUI process exits.
        if self.worker_thread and self.worker_thread.is_alive():
            self._close_after = self.root.after(100, self.finish_close)
            return
        self.root.after_cancel(self._dpi_after)
        if self.store:
            self.store.close()
        self.root.destroy()


def main():
    enable_high_dpi()
    root = tk.Tk()
    Application(root)
    root.mainloop()
