import json
import unittest
from pathlib import Path
from payroll import CzechInput, GermanInput, Child, InputError
from storage import calculate, read_scenario, write_json, write_csv

# Use a project directory: on some Windows sandboxes TemporaryDirectory is not writable.
TEMP = Path(__file__).resolve().parents[1]/'tests'/'.scratch'


class StorageTests(unittest.TestCase):
    def setUp(self):
        TEMP.mkdir(exist_ok=True)
        self.path=TEMP/'scenario.json'

    def tearDown(self):
        for name in ('scenario.json','scenario.csv'):
            path=TEMP/name
            if path.exists(): path.unlink()
        TEMP.rmdir()

    def test_roundtrip_both_countries(self):
        for inputs in [CzechInput(children=(Child(2,True),Child(3))),
                       GermanInput(parent=True,children_under_25=3,tax_class=4,factor='.825')]:
            write_json(self.path,inputs)
            loaded=read_scenario(self.path)
            self.assertEqual(inputs,loaded)
            self.assertEqual(calculate(inputs),calculate(loaded))

    def test_import_does_not_trust_results(self):
        write_json(self.path,CzechInput())
        data=json.loads(self.path.read_text(encoding='utf-8'))
        data['result']['net']='1000000000'
        self.path.write_text(json.dumps(data),encoding='utf-8')
        self.assertEqual(calculate(read_scenario(self.path)).net,39270)

    def test_bad_data_and_wrong_year(self):
        for data in [[],None,{'schema':'taxcalc-payroll/1','year':2025},
                     {'schema':'taxcalc-payroll/1','year':2026,'country':'CZ','inputs':{'declaration':'false'}},
                     {'schema':'taxcalc-payroll/1','year':2026,'country':'DE','inputs':{'gross':'NaN'}},
                     {'schema':'taxcalc-payroll/1','year':2026,'country':'CZ','inputs':{'children':[{'order':-1}]}},
                     {'schema':'taxcalc-payroll/1','year':2026,'country':'CZ','inputs':{'unknown':1}}]:
            self.path.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaises(InputError): read_scenario(self.path)

    def test_csv_contains_inputs_and_currency(self):
        path=TEMP/'scenario.csv'
        write_csv(path,GermanInput())
        text=path.read_text(encoding='utf-8-sig')
        self.assertIn('inputs.additional_health;2.90',text)
        self.assertIn('result.currency;€',text)
        self.assertIn('result.net;2605.50',text)

    def test_chamber_deduction_export_and_reload(self):
        inputs=GermanInput(state='Saarland')
        write_json(self.path,inputs)
        data=json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual(data['result']['deductions'],
                         {'Příspěvek zaměstnanecké komoře · Saarland':'6.00'})
        self.assertEqual(str(calculate(read_scenario(self.path)).net),'2599.50')


if __name__=='__main__': unittest.main()
