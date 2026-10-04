"""Monthly employee payroll for the explicitly supported 2026 scenarios.

Money uses Decimal; official source links and exclusions are in AUDIT.md.
German wage tax runs entirely offline using the bundled BMF PAP.
"""
from dataclasses import dataclass, field, asdict
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_UP, ROUND_DOWN
from pap2026 import Lohnsteuer2026

D = Decimal
YEAR = 2026
VERIFIED = '2026-10-02'
CZ_SOCIAL_CAP = D('2350416')
CZ_HIGH_TAX = D('146901')
CZ_MIN_WAGE = D('22400')
DE_RV_CAP = D('8450')
DE_KV_CAP = D('5812.50')
STATES = ('Baden-Württemberg', 'Bayern', 'Berlin', 'Brandenburg', 'Bremen',
          'Hamburg', 'Hessen', 'Mecklenburg-Vorpommern', 'Niedersachsen',
          'Nordrhein-Westfalen', 'Rheinland-Pfalz', 'Saarland', 'Sachsen',
          'Sachsen-Anhalt', 'Schleswig-Holstein', 'Thüringen')


class InputError(ValueError):
    pass


def number(value, label='Částka', minimum='0', maximum='10000000', places=2):
    if isinstance(value, bool):
        raise InputError(f'{label}: zadejte číslo.')
    try:
        n = D(str(value).replace('\u00a0', '').replace('\u202f', '').replace(' ', '').replace(',', '.'))
    except InvalidOperation:
        raise InputError(f'{label}: zadejte platné číslo.') from None
    if not n.is_finite() or not D(minimum) <= n <= D(maximum):
        raise InputError(f'{label}: povolený rozsah je {minimum} až {maximum}.')
    if n != n.quantize(D(1).scaleb(-places)):
        raise InputError(f'{label}: nejvýše {places} desetinných míst.')
    return n


def integer(value, label, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise InputError(f'{label}: celé číslo {minimum} až {maximum}.')
    return value


def flag(value, label):
    if type(value) is not bool:
        raise InputError(f'{label}: očekávána hodnota ano/ne.')
    return value


def up(value, unit='1'):
    unit = D(unit)
    return (value / unit).to_integral_value(rounding=ROUND_CEILING) * unit


def cents(value):
    return value.quantize(D('.01'), rounding=ROUND_HALF_UP)


def cents_down(value):
    return value.quantize(D('.01'), rounding=ROUND_DOWN)


@dataclass(frozen=True)
class Child:
    order: int = 1
    ztp: bool = False


@dataclass(frozen=True)
class CzechInput:
    gross: str = '50000'
    declaration: bool = True
    resident: bool = True
    disability: int = 0  # 0 none, 1 I/II, 2 III
    ztp: bool = False
    children: tuple = ()
    health_minimum: bool = True
    social_ytd: str = '0'  # this employer, before this month


@dataclass(frozen=True)
class GermanInput:
    gross: str = '4000'
    tax_class: int = 1
    factor: str = '1.000'
    additional_health: str = '2.90'
    state: str = 'Berlin'
    church: bool = False
    age_23: bool = True  # payroll month is after the month of the 23rd birthday
    parent: bool = False
    children_under_25: int = 0  # includes the month of each child's 25th birthday
    child_allowance: str = '0'  # ELStAM ZKF, unrelated to care discount
    allowance: str = '0'  # monthly ELStAM Freibetrag


@dataclass
class Result:
    country: str
    currency: str
    gross: D
    net: D
    tax: D
    insurance: dict
    employer: dict
    bonus: D = D(0)
    solidarity: D = D(0)
    church: D = D(0)
    details: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    deductions: dict = field(default_factory=dict)

    @property
    def insurance_total(self):
        return sum(self.insurance.values(), D(0))

    @property
    def taxes_total(self):
        return self.tax + self.solidarity + self.church

    @property
    def deductions_total(self):
        return sum(self.deductions.values(), D(0))

    @property
    def employer_cost(self):
        return self.gross + sum(self.employer.values(), D(0))


def calculate_cz(i: CzechInput):
    gross = number(i.gross, 'Hrubá mzda', minimum='4500')
    ytd = number(i.social_ytd, 'Předchozí základ sociálního pojištění', maximum='120000000')
    for name in ('declaration', 'resident', 'ztp', 'health_minimum'):
        flag(getattr(i, name), name)
    integer(i.disability, 'Invalidita', 0, 2)
    if not isinstance(i.children, (tuple, list)) or len(i.children) > 30:
        raise InputError('Lze zadat nejvýše 30 dětí.')
    seen = set()
    entitlement = D(0)
    for child in i.children:
        if not isinstance(child, Child):
            raise InputError('Neplatný záznam dítěte.')
        integer(child.order, 'Pořadí dítěte', 1, 3)
        flag(child.ztp, 'ZTP/P dítěte')
        if child.order < 3 and child.order in seen:
            raise InputError('První a druhé pořadí lze v domácnosti uplatnit jen jednou.')
        seen.add(child.order)
        entitlement += D((1267, 1860, 2320)[child.order - 1]) * (2 if child.ztp else 1)
    base = up(gross, '100')
    raw_tax = up(min(base, CZ_HIGH_TAX)*D('.15') + max(D(0), base-CZ_HIGH_TAX)*D('.23'))
    personal = D(2570) if i.declaration else D(0)
    if i.declaration and i.resident:
        personal += D((0, 210, 420)[i.disability]) + (D(1345) if i.ztp else D(0))
    if not i.declaration or not i.resident:
        entitlement = D(0)
    after_personal = max(D(0), raw_tax-personal)
    child_used = min(after_personal, entitlement)
    tax = after_personal-child_used
    potential_bonus = max(D(0), entitlement-after_personal)
    bonus = potential_bonus if gross >= D(11200) and potential_bonus >= 50 else D(0)
    sv_base = min(gross, max(D(0), CZ_SOCIAL_CAP-ytd))
    social = up(sv_base*D('.071'))
    health_total = up(gross*D('.135'))
    health_employee = up(gross*D('.045'))
    health_employer = health_total-health_employee
    topup = max(D(0), D(3024)-health_total) if i.health_minimum else D(0)
    health_employee += topup
    insurance = {'Sociální pojištění': social, 'Zdravotní pojištění': health_employee}
    employer = {'Sociální pojištění': up(sv_base*D('.248')), 'Zdravotní pojištění': health_employer}
    notes = ['Běžný pracovní poměr, celý měsíc, české pojištění a jeden zaměstnavatel.']
    if topup:
        notes.append('Zdravotní pojištění zahrnuje doplatek do minima hrazený zaměstnancem.')
    if gross < CZ_MIN_WAGE:
        notes.append('Mzda pod minimální měsíční mzdou: model např. zkráceného úvazku; neověřuje hodinové minimum.')
    if potential_bonus and not bonus:
        notes.append('Bonus se nevyplácí: nesplněn příjem 11 200 Kč nebo bonus nedosahuje 50 Kč.')
    if not i.declaration:
        notes.append('Bez podepsaného prohlášení se měsíční slevy a zvýhodnění neuplatní.')
    if not i.resident:
        notes.append('Nerezident: měsíčně je zahrnuta jen základní sleva při podepsaném prohlášení.')
    if sv_base < gross:
        notes.append('U sociálního pojištění byl uplatněn roční strop u tohoto zaměstnavatele.')
    return Result('CZ', 'Kč', gross, gross-social-health_employee-tax+bonus, tax, insurance, employer,
                  bonus=bonus, details={'Základ zálohy po zaokrouhlení': base, 'Daň před slevami': raw_tax,
                  'Osobní slevy skutečně využité': min(raw_tax, personal), 'Nárok na zvýhodnění na děti': entitlement,
                  'Zvýhodnění využité proti dani': child_used, 'Doplatek zdravotního pojištění': topup,
                  'Základ sociálního pojištění v měsíci': sv_base}, notes=notes)


def german_pap_inputs(i: GermanInput):
    gross = number(i.gross, 'Hrubá mzda', minimum='2000.01', maximum='1000000')
    integer(i.tax_class, 'Daňová třída', 1, 5)
    factor = number(i.factor, 'Faktor IV', minimum='.001', maximum='1', places=3)
    if i.tax_class != 4 and factor != 1:
        raise InputError('Faktor lze použít pouze ve třídě IV.')
    kvz = number(i.additional_health, 'Zusatzbeitrag', maximum='10')
    zkf = number(i.child_allowance, 'Kinderfreibetrag', maximum='15', places=1)
    if zkf % D('.5'):
        raise InputError('Kinderfreibetrag musí být násobek 0,5.')
    if i.tax_class == 5 and zkf:
        raise InputError('Ve třídě V se Kinderfreibetrag neuplatňuje.')
    allowance = number(i.allowance, 'Měsíční Freibetrag', maximum='1000000')
    for name in ('church', 'age_23', 'parent'):
        flag(getattr(i, name), name)
    integer(i.children_under_25, 'Počet dětí do 25 let', 0, 30)
    if not i.parent and i.children_under_25:
        raise InputError('Děti do 25 let vyžadují potvrzené rodičovství.')
    if i.tax_class == 2 and not i.parent:
        raise InputError('Třída II je pro oprávněného samoživitele. Potvrďte rodičovství a nárok dle ELStAM.')
    if i.state not in STATES:
        raise InputError('Vyberte platnou spolkovou zemi.')
    return dict(RE4=gross*100, LZZ=2, STKL=i.tax_class, KVZ=kvz,
                PVS=int(i.state=='Sachsen'), PVZ=int(not i.parent and i.age_23),
                PVA=max(0, min(5, i.children_under_25)-1), ZKF=zkf,
                R=int(i.church), af=int(factor!=1), f=factor, LZZFREIB=allowance*100)


def calculate_de(i: GermanInput):
    parameters = german_pap_inputs(i)
    p = Lohnsteuer2026(**parameters).calculate()
    gross = parameters['RE4']/100
    rv_base, kv_base = min(gross, DE_RV_CAP), min(gross, DE_KV_CAP)
    # General contribution and Zusatzbeitrag are calculated/rounded separately.
    health = cents(kv_base*D('.073')) + cents(kv_base*parameters['KVZ']/200)
    care_rate = D('.023') if i.state=='Sachsen' else D('.018')
    care_rate += D('.006')*parameters['PVZ'] - D('.0025')*parameters['PVA']
    insurance = {'Důchodové pojištění · RV': cents(rv_base*D('.093')),
                 'Zdravotní pojištění · KV': health,
                 'Pojištění péče · PV': cents(kv_base*care_rate),
                 'Pojištění nezaměstnanosti · AV': cents(rv_base*D('.013'))}
    employer = {'Důchodové pojištění · RV': cents(rv_base*D('.093')),
                'Zdravotní pojištění · KV': health,
                'Pojištění péče · PV': cents(kv_base*(D('.013') if i.state=='Sachsen' else D('.018'))),
                'Pojištění nezaměstnanosti · AV': cents(rv_base*D('.013'))}
    tax, soli = p.LSTLZZ.value/100, p.SOLZLZZ.value/100
    church_rate = D('.08') if i.state in ('Bayern', 'Baden-Württemberg') else D('.09')
    # Bavaria: AVKirchStG § 9(2); other states remain a documented estimate.
    church_round = cents_down if i.state == 'Bayern' else cents
    church = church_round(p.BK.value/100*church_rate) if i.church else D(0)
    deductions = {}
    if i.state == 'Bremen':
        deductions['Příspěvek zaměstnanecké komoře · Bremen'] = cents_down(gross*D('.0011'))
    elif i.state == 'Saarland':
        deductions['Příspěvek zaměstnanecké komoře · Saarland'] = cents_down(rv_base*D('.0015'))
    notes = ['Běžný zaměstnanec bez Altersentlastungsbetrag (k 1. 1. 2026 ještě nedovršených 64 let), zákonné zdravotní pojištění, celý měsíc a jediná práce nad 2 000 €.',
             'Lohnsteuer a Solidaritätszuschlag: oficiální PAP BMF 2026, lokální výpočet.',
             'Zusatzbeitrag 2,9 % je výchozí průměr pro 2026; zadejte sazbu své Krankenkasse.']
    if i.church:
        notes.append('Církevní daň je standardní srážka 8/9 % z Maßstabsteuer; bez zvláštního Kirchgeld, církevních výjimek a zastropování.')
        if i.state != 'Bayern':
            notes.append('Církevní daň je orientační: místní pravidlo zaokrouhlení nebylo ověřeno; používá se matematické zaokrouhlení na centy.')
    if deductions:
        notes.append('Netto zahrnuje povinný příspěvek zaměstnanecké komoře; model předpokládá běžného zaměstnance bez výjimky z členství.')
    if gross > D('6450'):
        notes.append('Při dobrovolné GKV je netto orientační: používá zaměstnanecké podíly pojistného; samostatný předpis pojišťovny a příspěvek zaměstnavatele mohou mít jiné centové zaokrouhlení.')
    return Result('DE', '€', gross, gross-sum(insurance.values())-tax-soli-church-sum(deductions.values()), tax,
                  insurance, employer, solidarity=soli, church=church,
                  details={'Základ pro církevní daň · Maßstabsteuer': p.BK.value/100,
                           'Základ pro RV a AV': rv_base, 'Základ pro KV a PV': kv_base}, notes=notes,
                  deductions=deductions)


def annual_model(i):
    """12 identical monthly paychecks starting in January, not annual tax settlement."""
    if isinstance(i, GermanInput):
        return calculate_de(i).net*12
    if number(i.social_ytd, 'Předchozí základ sociálního pojištění', maximum='120000000') != 0:
        return None
    ytd = D(0)
    total = D(0)
    for _ in range(12):
        params = asdict(i)
        params['children'] = i.children
        params['social_ytd'] = str(ytd)
        total += calculate_cz(CzechInput(**params)).net
        ytd += number(i.gross)
    return total
