#!/usr/bin/env python3
"""TaxCalc 3 — desktop employee payroll, CZ + DE, 2026."""
import sys
from pathlib import Path
from decimal import Decimal
from PySide6.QtCore import Qt, QUrl, QDir
from PySide6.QtGui import QColor, QPainter, QDesktopServices
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel,
    QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout, QScrollArea, QStackedWidget,
    QLineEdit, QComboBox, QCheckBox, QSpinBox, QFileDialog, QMessageBox, QTextBrowser,
    QDialog, QDialogButtonBox, QSizePolicy, QListView, QStyledItemDelegate)
from payroll import (CzechInput, GermanInput, Child, STATES, InputError, annual_model)
from storage import calculate, read_scenario, write_json, write_csv

APP_NAME = 'TaxCalc'
APP_VER = '3.0'
QDir.addSearchPath('taxcalc', str(Path(__file__).resolve().parent / 'assets'))
# Typical situations, not automatic eligibility rules: § 38b EStG, BMF LStH 2026.
DE_TAX_CLASSES = (
    ('I. třída · svobodný / rozvedený',
     'Typicky svobodný, rozvedený nebo trvale odloučený. Patří sem i rodič s dětmi, '
     'který nemá nárok na II. třídu; bezdětnost není podmínkou.'),
    ('II. třída · samoživitel s dítětem',
     'Osamělý rodič s dítětem ve své domácnosti a nárokem na úlevu pro samoživitele. '
     'Samotný rozvod a existence dětí nestačí; rozhodují podmínky společné domácnosti.'),
    ('III. třída · manželé, obvykle vyšší příjem',
     'V kombinaci III/V ji obvykle volí více vydělávající z manželů; druhý má V. '
     'Poměr příjmů není zákonnou podmínkou. Zvláštní pravidla mohou platit i pro ovdovělé.'),
    ('IV. třída · manželé, výchozí pro oba',
     'Výchozí kombinace IV/IV pro manžele, kteří nežijí trvale odděleně. '
     'Stejné příjmy nejsou podmínkou. Lze použít také schválený faktor IV/IV.'),
    ('V. třída · manželé, obvykle nižší příjem',
     'Protějšek III. třídy: druhý z manželů má III. Obvykle ji má méně vydělávající partner, '
     'ale nižší příjem není zákonnou podmínkou.'),
)
QSS = """
QWidget { color: #172b3a; font-family: 'Segoe UI'; font-size: 13px; }
QMainWindow, QWidget#canvas { background: #f2f5f7; }
QLabel { background: transparent; }
QFrame#sidebar { background: #102c3a; }
QFrame#sidebar QLabel { color: #d9e8ed; }
QLabel#brand { color: white; font-size: 25px; font-weight: 700; }
QLabel#sideHint { color: #9cb5bf; font-size: 12px; }
QFrame#card { background: white; border: 1px solid #e0e7eb; border-radius: 14px; }
QLabel#eyebrow { color: #587280; font-size: 11px; font-weight: 700; }
QLabel#heading { font-size: 28px; font-weight: 700; }
QLabel#section { font-size: 16px; font-weight: 700; }
QLabel#muted { color: #617684; }
QLabel#small { color: #617684; font-size: 11px; }
QLineEdit, QComboBox, QSpinBox { background: #f8fafb; border: 1px solid #cdd9df; border-radius: 7px; padding: 9px 10px; min-height: 18px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 2px solid #087d77; padding: 8px 9px; }
QSpinBox { padding-right: 40px; }
QSpinBox:focus { padding-right: 39px; }
QSpinBox::up-button, QSpinBox::down-button {
    subcontrol-origin: border; width: 32px;
    background: #edf3f5; border-left: 1px solid #cdd9df;
}
QSpinBox::up-button {
    subcontrol-position: top right; margin: 1px 1px 0 0;
    border-top-right-radius: 6px; border-bottom: 1px solid #cdd9df;
}
QSpinBox::down-button {
    subcontrol-position: bottom right; margin: 0 1px 1px 0;
    border-bottom-right-radius: 6px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #dceeea; }
QSpinBox::up-button:pressed, QSpinBox::down-button:pressed { background: #c3e2dc; }
QSpinBox::up-button:disabled, QSpinBox::down-button:disabled,
QSpinBox::up-button:off, QSpinBox::down-button:off { background: #f2f5f7; }
QSpinBox::up-arrow { image: url(taxcalc:chevron-up.svg); width: 14px; height: 14px; }
QSpinBox::down-arrow { image: url(taxcalc:chevron-down.svg); width: 14px; height: 14px; }
QSpinBox::up-arrow:disabled, QSpinBox::up-arrow:off { image: url(taxcalc:chevron-up-disabled.svg); }
QSpinBox::down-arrow:disabled, QSpinBox::down-arrow:off { image: url(taxcalc:chevron-down-disabled.svg); }
QLineEdit#gross { font-size: 25px; font-weight: 600; padding: 12px; }
QComboBox { combobox-popup: 0; }
QComboBox QAbstractItemView {
    background: white; color: #172b3a; border: 1px solid #cdd9df;
    padding: 4px; outline: 0;
    selection-background-color: #dff1ed; selection-color: #102c3a;
}
QComboBox QAbstractItemView::item {
    min-height: 24px; padding: 8px 12px; border: none; border-radius: 4px;
}
QComboBox QAbstractItemView::item:hover { background: #edf5f3; }
QComboBox QAbstractItemView::item:selected { background: #dff1ed; color: #102c3a; }
QComboBox::drop-down { border: none; width: 24px; }
QWidget:disabled { color: #81949e; }
QPushButton { background: white; border: 1px solid #cdd9df; border-radius: 7px; padding: 9px 13px; font-weight: 600; }
QPushButton:hover { background: #e9f2f2; border-color: #67a8a3; }
QPushButton:focus { border: 2px solid #087d77; }
QPushButton:disabled { color: #9aaab3; background: #f0f3f4; }
QPushButton#primary { background: #087d77; color: white; border: none; }
QPushButton#primary:hover { background: #096b66; }
QPushButton#nav { background: transparent; color: #d9e8ed; border: none; text-align: left; padding: 12px; }
QPushButton#nav:checked { background: #244956; color: white; }
QPushButton#nav:hover { background: #1c3e4c; }
QPushButton#country:checked { background: #102c3a; color: white; border-color: #102c3a; }
QCheckBox { spacing: 9px; background: transparent; min-height: 23px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QFrame#hero { background: #087d77; border-radius: 14px; }
QFrame#hero QLabel { color: white; }
QLabel#net { font-size: 37px; font-weight: 700; }
QLabel#heroSmall { color: #d7efeb; font-size: 12px; }
QLabel#error { color: #a33232; background: #fff0ee; border-radius: 7px; padding: 12px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { width: 9px; background: transparent; }
QScrollBar::handle:vertical { background: #c4d3d9; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QTextBrowser { background: white; border: none; padding: 16px; }
"""


def label(text, name=None, wrap=False):
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


def money(value, currency):
    return f'{value:,.2f}'.replace(',', '\u00a0').replace('.', ',') + ' ' + currency


def card(title):
    frame = QFrame()
    frame.setObjectName('card')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(14)
    if title:
        layout.addWidget(label(title, 'section'))
    return frame, layout


def button(text, callback, name=None):
    b = QPushButton(text)
    if name:
        b.setObjectName(name)
    b.setCursor(Qt.PointingHandCursor)
    b.clicked.connect(callback)
    return b


class SpaciousComboBox(QComboBox):
    """Consistent, comfortably spaced popup rows, including dynamic child fields."""
    def __init__(self, parent=None):
        super().__init__(parent)
        view = QListView(self)
        view.setSpacing(2)
        view.setUniformItemSizes(True)
        self.setView(view)
        # The native combo delegate can ignore stylesheet item padding.
        self.setItemDelegate(QStyledItemDelegate(view))
        self.setMaxVisibleItems(8)


class AllocationBar(QWidget):
    def __init__(self):
        super().__init__()
        self.values = []
        self.setFixedHeight(12)
        self.setAccessibleName('Rozdělení hrubé mzdy: čistá mzda, pojištění a daň')

    def paintEvent(self, event):
        p = QPainter(self)
        total = max(sum(self.values), 1)
        x = 0
        for amount, color in zip(self.values, ('#087d77', '#6c8cba', '#d6a34c')):
            width = self.width()*amount/total
            p.fillRect(int(x), 0, int(width)+1, self.height(), QColor(color))
            x += width


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('TaxCalc · Mzdová kalkulačka 2026')
        self.resize(1240, 920)
        self.setMinimumSize(1000, 700)
        self.country = 'CZ'
        self.loading = True
        self.current = None
        self.result = None
        self.baseline = None
        self.child_widgets = []
        self.fields = {'CZ': {}, 'DE': {}}
        self.build()
        self.loading = False
        self.recalculate()

    def build(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(192)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 30, 20, 24)
        side.setSpacing(12)
        side.addWidget(label('TaxCalc', 'brand'))
        side.addWidget(label('Přehled o vaší výplatě', 'sideHint', True))
        side.addSpacing(36)
        nav = button('Čistá mzda', lambda: None, 'nav')
        nav.setCheckable(True)
        nav.setChecked(True)
        side.addWidget(nav)
        side.addWidget(button('Metodika a zdroje', self.show_method, 'nav'))
        side.addStretch()
        side.addWidget(label('DAŇOVÝ ROK 2026', 'sideHint'))
        side.addWidget(label('Česko / Německo', None))
        side.addSpacing(10)
        side.addWidget(label('Výpočty běží offline.\nÚdaje zůstávají u vás.', 'sideHint', True))
        side.addSpacing(12)
        side.addWidget(label('VERZE 3.0', 'sideHint'))
        root.addWidget(sidebar)
        area = QScrollArea()
        area.setWidgetResizable(True)
        canvas = QWidget()
        canvas.setObjectName('canvas')
        body = QVBoxLayout(canvas)
        body.setContentsMargins(28, 25, 28, 25)
        body.setSpacing(19)
        top = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(label('MZDA POD KONTROLOU  /  2026', 'eyebrow'))
        titles.addWidget(label('Kolik vám přijde na účet?', 'heading'))
        titles.addWidget(label('Hrubá mzda, daně a odvody. Přehledně na jednom místě.', 'muted', True))
        top.addLayout(titles, 1)
        top.addWidget(button('Načíst JSON', self.import_file))
        body.addLayout(top)
        country_row = QHBoxLayout()
        self.cz_button = button('CZ   Česko', lambda: self.switch_country('CZ'), 'country')
        self.de_button = button('DE   Německo', lambda: self.switch_country('DE'), 'country')
        for b in (self.cz_button, self.de_button):
            b.setCheckable(True)
            b.setMinimumWidth(150)
            country_row.addWidget(b)
        self.cz_button.setChecked(True)
        country_row.addStretch()
        country_row.addWidget(label('Měsíční výplata · 2026', 'muted'))
        body.addLayout(country_row)
        self.scope = label('', 'muted', True)
        body.addWidget(self.scope)
        columns = QHBoxLayout()
        columns.setSpacing(22)
        left = QVBoxLayout()
        left.setSpacing(18)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_cz())
        self.stack.addWidget(self.build_de())
        left.addWidget(self.stack)
        left.addStretch()
        columns.addLayout(left, 6)
        right = QVBoxLayout()
        right.setSpacing(16)
        self.error = label('', 'error', True)
        self.error.hide()
        right.addWidget(self.error)
        hero = QFrame()
        hero.setObjectName('hero')
        hero_l = QVBoxLayout(hero)
        hero_l.setContentsMargins(24, 23, 24, 23)
        hero_l.setSpacing(9)
        hero_l.addWidget(label('ČISTÁ MĚSÍČNÍ MZDA', 'heroSmall'))
        self.net_label = label('—', 'net')
        self.net_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        hero_l.addWidget(self.net_label)
        self.net_hint = label('', 'heroSmall', True)
        hero_l.addWidget(self.net_hint)
        right.addWidget(hero)
        result_card, results = card('Kam jde vaše mzda')
        self.bar = AllocationBar()
        results.addWidget(self.bar)
        results.addWidget(label('<span style="color:#087d77">●</span> Čistá mzda &nbsp; '
                               '<span style="color:#6c8cba">●</span> Pojištění a odvody &nbsp; '
                               '<span style="color:#d6a34c">●</span> Daně', 'small', True))
        self.breakdown = QVBoxLayout()
        self.breakdown.setSpacing(10)
        results.addLayout(self.breakdown)
        self.annual_label = label('', 'muted', True)
        results.addWidget(self.annual_label)
        self.employer_label = label('', 'small', True)
        results.addWidget(self.employer_label)
        right.addWidget(result_card)
        self.comparison = label('', 'muted', True)
        right.addWidget(self.comparison)
        actions = QHBoxLayout()
        self.pin_button = button('Porovnat scénář', self.pin_result)
        self.export_button = button('Uložit výsledek', self.export_file, 'primary')
        actions.addWidget(self.pin_button)
        actions.addWidget(self.export_button)
        right.addLayout(actions)
        right.addWidget(button('Podrobný výpočet', self.show_detail))
        self.notes = label('', 'small', True)
        right.addWidget(self.notes)
        right.addStretch()
        columns.addLayout(right, 5)
        body.addLayout(columns)
        body.addWidget(label('Roční model je součet 12 výplat se stejnými podmínkami. Nejde o roční daňové přiznání ani posouzení přeshraničního zdanění.', 'small', True))
        area.setWidget(canvas)
        root.addWidget(area, 1)

    def field(self, country, key, kind, default, items=None):
        if kind == 'check':
            w = QCheckBox()
            w.setChecked(default)
            signal = w.toggled
        elif kind == 'combo':
            w = SpaciousComboBox()
            w.addItems(items)
            w.setCurrentIndex(default)
            signal = w.currentIndexChanged
        elif kind == 'spin':
            w = QSpinBox()
            w.setRange(0, 30)
            w.setValue(default)
            signal = w.valueChanged
        else:
            w = QLineEdit(str(default))
            w.setMaxLength(24)
            signal = w.textChanged
        w.setAccessibleName(key)
        signal.connect(self.recalculate)
        self.fields[country][key] = w
        return w

    def row(self, layout, text, widget, hint=None):
        lbl = label(text)
        lbl.setBuddy(widget)
        widget.setAccessibleName(text)
        layout.addWidget(lbl)
        layout.addWidget(widget)
        if hint:
            layout.addWidget(label(hint, 'small', True))

    def check(self, layout, country, key, text, value):
        w = self.field(country, key, 'check', value)
        w.setText(text)
        w.setAccessibleName(text)
        layout.addWidget(w)
        return w

    def build_cz(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(18)
        box, form = card('01   Vaše mzda')
        gross = self.field('CZ', 'gross', 'text', '50 000')
        gross.setObjectName('gross')
        self.row(form, 'Hrubá měsíční mzda · Kč', gross)
        self.check(form, 'CZ', 'declaration', 'Podepsané prohlášení poplatníka', True)
        self.check(form, 'CZ', 'resident', 'Jsem daňový rezident ČR', True)
        layout.addWidget(box)
        box, form = card('02   Děti a osobní slevy')
        self.row(form, 'Počet dětí uplatňovaných v této výplatě', self.field('CZ', 'count', 'spin', 0),
                 'Pořadí platí v celé domácnosti. Totéž dítě smí za měsíc uplatnit jen jeden poplatník.')
        self.children_layout = QVBoxLayout()
        form.addLayout(self.children_layout)
        self.fields['CZ']['count'].valueChanged.connect(self.rebuild_children)
        self.row(form, 'Přiznaná invalidita', self.field('CZ', 'disability', 'combo', 0,
                 ['Bez slevy na invaliditu', 'I. nebo II. stupeň · 210 Kč', 'III. stupeň · 420 Kč']))
        self.check(form, 'CZ', 'ztp', 'Mám průkaz ZTP/P · sleva 1 345 Kč', False)
        layout.addWidget(box)
        box, form = card('03   Pojištění')
        self.check(form, 'CZ', 'health_minimum', 'Dopočítat zdravotní pojištění do minima', True)
        form.addWidget(label('Vypněte, pokud se na vás minimum nevztahuje (např. státní pojištěnec po celý měsíc).', 'small', True))
        self.row(form, 'Základ sociálního pojištění od ledna · Kč', self.field('CZ', 'social_ytd', 'text', '0'),
                 'Součet před tímto měsícem u stejného zaměstnavatele. Roční strop: 2 350 416 Kč.')
        layout.addWidget(box)
        layout.addWidget(button('Obnovit výchozí hodnoty', self.reset))
        layout.addStretch()
        return page

    def build_de(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(18)
        box, form = card('01   Vaše mzda')
        gross = self.field('DE', 'gross', 'text', '4 000')
        gross.setObjectName('gross')
        self.row(form, 'Hrubá měsíční mzda · €', gross, 'Standardní zaměstnání nad 2 000 € měsíčně.')
        tax_class = self.field('DE','tax_class','combo',0,
                               [title for title, _ in DE_TAX_CLASSES])
        tax_class.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        for index, (_, explanation) in enumerate(DE_TAX_CLASSES):
            tax_class.setItemData(index, explanation, Qt.ToolTipRole)
        self.row(form, 'Daňová třída · Steuerklasse', tax_class)
        self.tax_class_hint = label('', 'small', True)
        form.addWidget(self.tax_class_hint)
        form.addWidget(label('Vyberte třídu z výplatní pásky nebo ELStAM. '
                             'Popisky uvádějí typické situace; manželé zahrnují i registrované partnery.',
                             'small', True))
        self.row(form, 'Faktor pro třídu IV', self.field('DE','factor','text','1.000'), 'Faktor z ELStAM; 1 znamená bez faktorového postupu.')
        layout.addWidget(box)
        box, form = card('02   Pojištění a spolková země')
        self.row(form, 'Zusatzbeitrag vaší Krankenkasse · %', self.field('DE','additional_health','text','2,90'),
                 'Celá doplňková sazba; zaměstnanec platí polovinu. Výchozí 2,9 % je úřední průměr, ne sazba každé pojišťovny.')
        self.row(form, 'Spolková země zaměstnání a mzdové účtárny', self.field('DE','state','combo',2,list(STATES)),
                 'Sasko mění podíl pojištění péče. Pro církevní daň se předpokládá stejná země účtárny.')
        self.check(form,'DE','church','Standardní církevní daň · 8 / 9 %',False)
        self.check(form,'DE','age_23','Měsíc po 23. narozeninách nebo později',True)
        form.addWidget(label('Příplatek za bezdětnost začíná až měsícem po 23. narozeninách.', 'small', True))
        self.check(form,'DE','parent','Mám doložené rodičovství pro pojištění péče',False)
        self.row(form, 'Počet zohledňovaných dětí · pojištění péče', self.field('DE','children_under_25','spin',0),
                 'Děti se započítávají včetně celého měsíce, ve kterém dosáhnou 25 let.')
        layout.addWidget(box)
        box, form = card('03   Údaje z ELStAM')
        self.row(form, 'Kinderfreibetrag · počet podílů', self.field('DE','child_allowance','text','0'),
                 'Např. 0,5 nebo 1. Ovlivňuje Solidaritätszuschlag a církevní daň; ne Lohnsteuer. Kindergeld se k výplatě nepřičítá.')
        self.row(form, 'Měsíční Freibetrag · €', self.field('DE','allowance','text','0'),
                 'Pouze částka evidovaná v ELStAM. U třídy II i případné navýšení za další děti.')
        layout.addWidget(box)
        layout.addWidget(button('Obnovit výchozí hodnoty', self.reset))
        layout.addStretch()
        return page

    def rebuild_children(self, *args):
        count = self.fields['CZ']['count'].value()
        while len(self.child_widgets) > count:
            row, _, _ = self.child_widgets.pop()
            self.children_layout.removeWidget(row)
            row.deleteLater()
        while len(self.child_widgets) < count:
            row = QWidget()
            lay = QHBoxLayout(row)
            lay.setContentsMargins(0,0,0,0)
            order = SpaciousComboBox()
            order.addItems(['1. dítě', '2. dítě', '3. a další dítě'])
            order.setCurrentIndex(min(len(self.child_widgets), 2))
            order.setAccessibleName(f'Pořadí dítěte {len(self.child_widgets)+1}')
            ztp = QCheckBox('ZTP/P dítěte')
            ztp.setAccessibleName(f'ZTP/P dítěte {len(self.child_widgets)+1}')
            order.currentIndexChanged.connect(self.recalculate)
            ztp.toggled.connect(self.recalculate)
            lay.addWidget(order,1)
            lay.addWidget(ztp)
            self.children_layout.addWidget(row)
            self.child_widgets.append((row,order,ztp))
        self.recalculate()

    def inputs(self):
        values = {}
        for key, w in self.fields[self.country].items():
            if isinstance(w, QCheckBox):
                values[key] = w.isChecked()
            elif isinstance(w, QComboBox):
                values[key] = w.currentIndex()
            elif isinstance(w, QSpinBox):
                values[key] = w.value()
            else:
                values[key] = w.text()
        if self.country == 'CZ':
            values.pop('count')
            values['children'] = tuple(Child(o.currentIndex()+1,z.isChecked()) for _,o,z in self.child_widgets)
            return CzechInput(**values)
        values['tax_class'] += 1
        values['state'] = STATES[values['state']]
        if values['tax_class'] != 4:
            values['factor'] = '1.000'
        if not values['parent']:
            values['children_under_25'] = 0
        if values['tax_class'] == 5:
            values['child_allowance'] = '0'
        return GermanInput(**values)

    def switch_country(self, country):
        self.country = country
        self.stack.setCurrentIndex(int(country=='DE'))
        self.cz_button.setChecked(country=='CZ')
        self.de_button.setChecked(country=='DE')
        self.recalculate()

    def clear_rows(self):
        while self.breakdown.count():
            item = self.breakdown.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()

    def result_row(self, name, value, currency):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(label(name, None, True), 1)
        val = label(money(value,currency))
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(val)
        self.breakdown.addWidget(row)

    def recalculate(self, *args):
        if self.loading:
            return
        de = self.fields['DE']
        self.tax_class_hint.setText(DE_TAX_CLASSES[de['tax_class'].currentIndex()][1])
        de['factor'].setEnabled(de['tax_class'].currentIndex()==3)
        de['children_under_25'].setEnabled(de['parent'].isChecked())
        de['child_allowance'].setEnabled(de['tax_class'].currentIndex()!=4)
        cz = self.fields['CZ']
        can_claim = cz['declaration'].isChecked() and cz['resident'].isChecked()
        for key in ('count','disability','ztp'):
            cz[key].setEnabled(can_claim)
        for row,_,_ in self.child_widgets:
            row.setEnabled(can_claim)
        self.scope.setText('Běžný pracovní poměr · celý měsíc · jeden zaměstnavatel · bez režimu pracujícího důchodce'
                           if self.country=='CZ' else 'Běžný zaměstnanec · bez Altersentlastungsbetrag · zákonné pojištění · bez Mini/Midijob a souběhu zaměstnání')
        self.clear_rows()
        try:
            inputs = self.inputs()
            result = calculate(inputs)
            annual = annual_model(inputs)
        except InputError as error:
            self.current = self.result = None
            self.error.setText(str(error))
            self.error.show()
            self.net_label.setText('—')
            self.net_hint.setText('Upravte vstupní údaje.')
            self.annual_label.clear()
            self.employer_label.clear()
            self.notes.clear()
            self.comparison.clear()
            self.bar.values = []
            self.bar.update()
            self.export_button.setEnabled(False)
            self.pin_button.setEnabled(False)
            return
        self.error.hide()
        self.current, self.result = inputs, result
        self.export_button.setEnabled(True)
        self.pin_button.setEnabled(True)
        self.net_label.setText(money(result.net,result.currency))
        pct = result.net/result.gross*100
        self.net_hint.setText(f'{pct:.1f}'.replace('.',',')+' % hrubé mzdy'+(' · včetně daňového bonusu' if result.bonus else ''))
        self.result_row('Hrubá mzda',result.gross,result.currency)
        self.result_row('Daň po slevách' if self.country=='CZ' else 'Lohnsteuer',result.tax,result.currency)
        if self.country=='DE':
            self.result_row('Solidaritätszuschlag',result.solidarity,result.currency)
            if inputs.church:
                self.result_row('Církevní daň',result.church,result.currency)
        for name,value in result.insurance.items():
            self.result_row(name,value,result.currency)
        for name,value in result.deductions.items():
            self.result_row(name,value,result.currency)
        if result.bonus:
            self.result_row('Daňový bonus (+)',result.bonus,result.currency)
        self.bar.values = [float(max(Decimal(0),result.net-result.bonus)),float(result.insurance_total+result.deductions_total),float(result.taxes_total)]
        self.bar.update()
        self.annual_label.setText('Roční model od ledna\n'+money(annual,result.currency) if annual is not None else
                                  'Roční model není zobrazen při zadaném předchozím základu pojištění.')
        self.employer_label.setText('Mzda + základní odvody zaměstnavatele: '+money(result.employer_cost,result.currency)+
                                    '\nBez úrazového pojištění, zvláštních příspěvků a dalších nákladů.')
        self.notes.setText('\n\n'.join(result.notes))
        if self.baseline and self.baseline.country==self.country:
            diff = result.net-self.baseline.net
            self.comparison.setText('Proti uloženému scénáři: '+('+' if diff>=0 else '')+money(diff,result.currency)+' čistého / měsíc')
        else:
            self.comparison.clear()

    def pin_result(self):
        if self.result:
            self.baseline = self.result
            self.recalculate()

    def apply_inputs(self, inputs):
        country = 'CZ' if isinstance(inputs,CzechInput) else 'DE'
        self.loading = True
        try:
            if country=='CZ':
                self.fields['CZ']['count'].setValue(len(inputs.children))
                self.rebuild_children()
                for child, (_,order,ztp) in zip(inputs.children,self.child_widgets):
                    order.setCurrentIndex(child.order-1)
                    ztp.setChecked(child.ztp)
            for key,w in self.fields[country].items():
                if key=='count':
                    continue
                value = getattr(inputs,key)
                if isinstance(w,QCheckBox):
                    w.setChecked(value)
                elif isinstance(w,QComboBox):
                    index = STATES.index(value) if key=='state' else value-1 if key=='tax_class' else value
                    w.setCurrentIndex(index)
                elif isinstance(w,QSpinBox):
                    w.setValue(value)
                else:
                    w.setText(str(value))
        finally:
            self.loading = False
        self.switch_country(country)

    def reset(self):
        self.baseline = None
        self.apply_inputs(CzechInput() if self.country=='CZ' else GermanInput())

    def export_file(self):
        if not self.current:
            return
        path, chosen = QFileDialog.getSaveFileName(self,'Uložit výsledek',f'TaxCalc_{self.country}_2026.json',
                                                   'JSON scénář (*.json);;CSV přehled (*.csv)')
        if not path:
            return
        suffix = '.csv' if chosen.startswith('CSV') else '.json'
        path = str(Path(path).with_suffix(suffix))
        try:
            (write_csv if suffix=='.csv' else write_json)(path,self.current)
            self.statusBar().showMessage('Uloženo: '+path,8000)
        except OSError as error:
            QMessageBox.warning(self,'Uložení se nezdařilo',str(error))

    def import_file(self):
        path,_ = QFileDialog.getOpenFileName(self,'Načíst scénář','','JSON scénář (*.json)')
        if path:
            try:
                inputs = read_scenario(path)
                self.apply_inputs(inputs)
            except (OSError,InputError) as error:
                QMessageBox.warning(self,'Soubor nelze načíst',str(error))

    def show_detail(self):
        if not self.result:
            return
        r = self.result
        text = '\n'.join(f'{k}: {money(v,r.currency)}' for k,v in r.details.items())
        text += '\n\nZákladní odvody zaměstnavatele:\n'
        text += '\n'.join(f'{k}: {money(v,r.currency)}' for k,v in r.employer.items())
        QMessageBox.information(self,'Podrobný výpočet · měsíc',text)

    def show_method(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Metodika a zdroje · 2026')
        dialog.resize(850,700)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        path = Path(__file__).with_name('AUDIT.md')
        browser.setMarkdown(path.read_text(encoding='utf-8') if path.exists() else 'Metodika je v souboru AUDIT.md.')
        layout.addWidget(browser)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(dialog.reject)
        layout.addWidget(close)
        dialog.exec()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VER)
    app.setStyle('Fusion')
    app.setStyleSheet(QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
