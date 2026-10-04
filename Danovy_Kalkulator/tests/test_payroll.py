import json
import unittest
from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
from payroll import *
from pap2026 import Lohnsteuer2026


class CzechTests(unittest.TestCase):
    def test_standard_paycheck(self):
        r = calculate_cz(CzechInput())
        self.assertEqual((r.net,r.tax,r.insurance_total,r.employer_cost), (D(39270),D(4930),D(5800),D(66900)))

    def test_official_financial_administration_examples(self):
        for gross, base, tax in [('45810',45900,6885),('165615',165700,26359)]:
            with self.subTest(gross=gross):
                r=calculate_cz(CzechInput(gross=gross,declaration=False))
                self.assertEqual(r.tax,D(tax))
                self.assertEqual(r.details['Základ zálohy po zaokrouhlení'],D(base))

    def test_progressive_boundary(self):
        for gross,expected in [('146900',22035),('146901',22058),('147000',22058)]:
            self.assertEqual(calculate_cz(CzechInput(gross=gross,declaration=False)).tax,D(expected))

    def test_bonus_threshold(self):
        for gross, expected in [('11199.99',0),('11200',1267)]:
            r=calculate_cz(CzechInput(gross=gross,children=(Child(),),health_minimum=False))
            self.assertEqual(r.bonus,D(expected))

    def test_bonus_minimum_50(self):
        self.assertEqual(calculate_cz(CzechInput(gross='25300',children=(Child(),))).bonus,D(0))  # 42
        self.assertEqual(calculate_cz(CzechInput(gross='25200',children=(Child(),))).bonus,D(57))

    def test_fourth_child_and_child_ztp(self):
        children=(Child(1),Child(2),Child(3),Child(3,True))
        r=calculate_cz(CzechInput(gross='22400',children=children))
        self.assertEqual(r.details['Nárok na zvýhodnění na děti'],D(10087))
        self.assertEqual(r.tax,D(0))
        self.assertEqual(r.bonus,D(9297))

    def test_personal_disability_not_child_disability(self):
        r=calculate_cz(CzechInput(ztp=True,disability=1,children=(Child(),)))
        self.assertEqual(r.tax,D(2108))
        self.assertEqual(r.details['Nárok na zvýhodnění na děti'],D(1267))

    def test_declaration_and_residency(self):
        i=CzechInput(disability=2,ztp=True,children=(Child(),))
        self.assertEqual(calculate_cz(replace(i,resident=False)).tax,D(4930))
        self.assertEqual(calculate_cz(replace(i,declaration=False)).tax,D(7500))

    def test_health_minimum(self):
        i=CzechInput(gross='11200')
        a,b=calculate_cz(i),calculate_cz(replace(i,health_minimum=False))
        self.assertEqual(a.insurance['Zdravotní pojištění'],D(2016))
        self.assertEqual(b.insurance['Zdravotní pojištění'],D(504))
        self.assertEqual(a.employer['Zdravotní pojištění'],D(1008))

    def test_social_cap(self):
        r=calculate_cz(CzechInput(social_ytd='2340000'))
        self.assertEqual(r.insurance['Sociální pojištění'],D(740))
        self.assertEqual(r.details['Základ sociálního pojištění v měsíci'],D(10416))
        self.assertEqual(calculate_cz(CzechInput(social_ytd='2350416')).insurance['Sociální pojištění'],0)

    def test_annual_cap_not_twelve_identical_social_contributions(self):
        i=CzechInput(gross='250000')
        self.assertGreater(annual_model(i),calculate_cz(i).net*12)
        self.assertIsNone(annual_model(replace(i,social_ytd='1')))

    def test_annual_model_accepts_full_monthly_ytd_range(self):
        for ytd in ('10000001', '120000000'):
            i=CzechInput(social_ytd=ytd)
            self.assertEqual(calculate_cz(i).net, D(42820))
            self.assertIsNone(annual_model(i))

    def test_rounding_and_conservation(self):
        for gross in ['4500.01','12345.67','49999.99','146900.01','500000']:
            r=calculate_cz(CzechInput(gross=gross))
            self.assertEqual(r.gross+r.bonus,r.net+r.tax+r.insurance_total)
            health=r.insurance['Zdravotní pojištění']+r.employer['Zdravotní pojištění']
            self.assertEqual(health, max(D(3024),up(D(gross)*D('.135'))))


class GermanTests(unittest.TestCase):
    def test_bmf_official_fixtures(self):
        fixtures=json.loads(Path(__file__).with_name('bmf_cases.json').read_text(encoding='utf-8'))
        self.assertEqual(len(fixtures['cases']),42)
        for case in fixtures['cases']:
            with self.subTest(inputs=case['input']):
                p=Lohnsteuer2026(**case['input']).calculate()
                for name,value in case['expected'].items():
                    self.assertEqual(getattr(p,name).value,D(value),name)

    def test_standard_paycheck(self):
        r=calculate_de(GermanInput())
        self.assertEqual(r.tax,D('524.50'))
        self.assertEqual(r.net,D('2605.50'))
        self.assertEqual(r.insurance_total,D(870))

    def test_application_inputs_against_bmf_reference_outputs(self):
        # Exercise the application's mapping, not just the generated PAP class.
        cases=[
            (GermanInput(gross='5555.55',tax_class=4,factor='.823',church=True,
                         child_allowance='1.5',state='Sachsen',parent=True,children_under_25=3),
             '781.00','607.08'),
            (GermanInput(gross='6123.45',additional_health='2.69',church=True,
                         child_allowance='.5',parent=True,children_under_25=5),
             '1154.08','1002.16'),
            (GermanInput(gross='3500',tax_class=2,parent=True,child_allowance='1',allowance='200'),
             '256.66','0'),
            (GermanInput(gross='5812.51',church=True,state='Sachsen'),
             '1000.75','1000.75'),
            (GermanInput(gross='3000.12',age_23=False,additional_health='0'),
             '310.00','0'),
        ]
        for inputs,tax,church_base in cases:
            with self.subTest(inputs=inputs):
                r=calculate_de(inputs)
                self.assertEqual(r.tax,D(tax))
                self.assertEqual(r.solidarity,0)
                self.assertEqual(r.details['Základ pro církevní daň · Maßstabsteuer'],D(church_base))

    def test_care_family_saxony_and_under23(self):
        i=GermanInput()
        for changes,expected in [({},96),({'state':'Sachsen'},116),({'age_23':False},72),
                                 ({'parent':True},72),({'parent':True,'children_under_25':2},62),
                                 ({'parent':True,'children_under_25':5},32),
                                 ({'parent':True,'children_under_25':8},32)]:
            with self.subTest(changes=changes):
                self.assertEqual(calculate_de(replace(i,**changes)).insurance['Pojištění péče · PV'],D(expected))

    def test_social_caps(self):
        a=calculate_de(GermanInput(gross='8450'))
        b=calculate_de(GermanInput(gross='30000'))
        self.assertEqual(a.insurance,b.insurance)
        self.assertEqual(b.insurance['Důchodové pojištění · RV'],D('785.85'))
        self.assertEqual(b.insurance['Zdravotní pojištění · KV'],D('508.59'))

    def test_health_components_round_separately(self):
        # 219.00438 -> 219.00 plus 43.50087 -> 43.50; combined rounding would be 262.51.
        r=calculate_de(GermanInput(gross='3000.06'))
        self.assertEqual(r.insurance['Zdravotní pojištění · KV'],D('262.50'))

    def test_church_children_and_state(self):
        i=GermanInput(gross='8000',church=True,parent=True)
        a,b=calculate_de(i),calculate_de(replace(i,child_allowance='1'))
        self.assertEqual(a.tax,b.tax)
        self.assertLess(b.church,a.church)
        self.assertLess(calculate_de(replace(i,state='Bayern')).church,a.church)

    def test_bavarian_church_tax_truncates_fractional_cents(self):
        # AVKirchStG § 9(2): 293.08 * .08 = 23.4464 -> 23.44, not 23.45.
        r=calculate_de(GermanInput(gross='3000',state='Bayern',church=True))
        self.assertEqual(r.tax,D('293.08'))
        self.assertEqual(r.church,D('23.44'))
        self.assertEqual(r.net,D('2030.98'))

    def test_chamber_contributions_2026(self):
        # Official Bremen 2026 leaflet and Saarland 2026 contribution table.
        cases=[('Bremen','4000','4.40'),('Bremen','3456.78','3.80'),
               ('Bremen','30000','33.00'),('Saarland','4000','6.00'),
               ('Saarland','8450','12.67'),('Saarland','30000','12.67')]
        for state,gross,expected in cases:
            with self.subTest(state=state,gross=gross):
                i=GermanInput(gross=gross,state=state)
                r=calculate_de(i)
                self.assertEqual(r.deductions_total,D(expected))
                self.assertEqual(r.net,calculate_de(replace(i,state='Berlin')).net-D(expected))
                self.assertEqual(r.gross,r.net+r.insurance_total+r.taxes_total+r.deductions_total)
                self.assertEqual(annual_model(i),r.net*12)

    def test_soli_transition(self):
        r=calculate_de(GermanInput(gross='8500'))
        self.assertGreater(r.solidarity,0)
        self.assertLess(r.solidarity,r.tax*D('.055'))

    def test_factor(self):
        a=calculate_de(GermanInput(tax_class=4))
        b=calculate_de(GermanInput(tax_class=4,factor='.800'))
        self.assertLess(b.tax,a.tax)

    def test_conservation(self):
        for gross in ['2000.01','3456.78','5812.51','8450.01','999999.99']:
            r=calculate_de(GermanInput(gross=gross,church=True))
            self.assertEqual(r.gross,r.net+r.insurance_total+r.taxes_total)


class ValidationTests(unittest.TestCase):
    def test_bad_money(self):
        for text in ['', 'NaN', 'Infinity', '-5000', '1e10000000', '40.000,50', '4500.001',True,[]]:
            with self.subTest(text=text),self.assertRaises(InputError):
                calculate_cz(CzechInput(gross=text))

    def test_localized_money(self):
        self.assertEqual(number('50\u00a0000,25'),D('50000.25'))
        self.assertEqual(number('50\u202f000,25'),D('50000.25'))

    def test_invalid_options(self):
        bad=[CzechInput(children=(Child(1),Child(1))),CzechInput(disability=-1),
             CzechInput(declaration='false'),CzechInput(gross='4499.99')]
        for i in bad:
            with self.assertRaises(InputError): calculate_cz(i)
        bad=[GermanInput(gross='2000'),GermanInput(tax_class=6),GermanInput(tax_class=2),
             GermanInput(children_under_25=1),GermanInput(factor='.8'),
             GermanInput(child_allowance='.7'),GermanInput(state='Prague'),
             GermanInput(tax_class=5,child_allowance='1')]
        for i in bad:
            with self.assertRaises(InputError): calculate_de(i)


if __name__=='__main__': unittest.main()
