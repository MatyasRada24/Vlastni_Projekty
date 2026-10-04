import os
import unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
    from PySide6.QtWidgets import QApplication, QScrollArea
    from PySide6.QtGui import QFontDatabase
    from app import MainWindow, QSS
    from payroll import CzechInput, GermanInput, Child
    QT_AVAILABLE=True
except ImportError:
    QT_AVAILABLE=False


@unittest.skipUnless(QT_AVAILABLE,'PySide6 not installed')
class UITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        for name in ('segoeui.ttf','segoeuib.ttf'):
            p=Path('C:/Windows/Fonts')/name
            if p.exists(): QFontDatabase.addApplicationFont(str(p))
        cls.app.setStyle('Fusion')
        cls.app.setStyleSheet(QSS)

    def setUp(self):
        self.window=MainWindow()
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_invalid_input_clears_result_and_export(self):
        w=self.window
        w.fields['CZ']['gross'].setText('invalid')
        self.assertIsNone(w.result)
        self.assertFalse(w.export_button.isEnabled())
        self.assertEqual(w.net_label.text(),'—')
        w.fields['CZ']['gross'].setText('50000')
        self.assertEqual(w.result.net,39270)

    def test_child_change_and_declaration(self):
        w=self.window
        w.fields['CZ']['count'].setValue(4)
        self.assertEqual(len(w.inputs().children),4)
        self.assertEqual(w.result.details['Nárok na zvýhodnění na děti'],7767)
        w.fields['CZ']['declaration'].setChecked(False)
        self.assertEqual(w.result.tax,7500)
        w.fields['CZ']['declaration'].setChecked(True)
        self.assertEqual(w.result.tax,0)

    def test_scenario_switch_and_apply(self):
        w=self.window
        inputs=GermanInput(tax_class=4,factor='.823',parent=True,children_under_25=3)
        w.apply_inputs(inputs)
        self.assertEqual(w.inputs(),inputs)
        w.fields['DE']['tax_class'].setCurrentIndex(0)
        self.assertEqual(w.inputs().factor,'1.000')
        self.assertIsNotNone(w.result)
        w.fields['DE']['parent'].setChecked(False)
        self.assertEqual(w.inputs().children_under_25,0)
        w.apply_inputs(CzechInput(children=(Child(2,True),Child(3))))
        self.assertEqual(w.inputs().children,(Child(2,True),Child(3)))

    def test_scenario_comparison_and_reset(self):
        w=self.window
        w.pin_result()
        w.fields['CZ']['gross'].setText('60000')
        self.assertIn('+',w.comparison.text())
        w.reset()
        self.assertIsNone(w.baseline)
        self.assertEqual(w.result.net,39270)

    def test_large_valid_ytd_keeps_monthly_result(self):
        w=self.window
        w.apply_inputs(CzechInput(social_ytd='10000001'))
        self.assertIsNotNone(w.result)
        self.assertEqual(w.result.net,42820)
        self.assertTrue(w.export_button.isEnabled())
        self.assertIn('není zobrazen',w.annual_label.text())

    def test_chamber_deduction_is_visible_and_in_allocation(self):
        w=self.window
        w.apply_inputs(GermanInput(state='Bremen'))
        self.assertEqual(str(w.result.net),'2601.10')
        from PySide6.QtWidgets import QLabel
        self.assertTrue(any('Příspěvek zaměstnanecké komoře' in item.text()
                            for item in w.findChildren(QLabel)))
        self.assertAlmostEqual(sum(w.bar.values),4000)

    def test_layout_at_minimum_size(self):
        w=self.window
        w.resize(w.minimumSize())
        self.app.processEvents()
        area=w.findChild(QScrollArea)
        self.assertEqual(area.horizontalScrollBar().maximum(),0)


if __name__=='__main__': unittest.main()
