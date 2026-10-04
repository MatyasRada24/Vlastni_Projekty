"""Translate the bundled, official BMF XML into reviewable Python. No runtime eval."""
from pathlib import Path
import hashlib
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'vendor' / 'Lohnsteuer2026.xml'
tree = ET.parse(source)
names = {e.attrib['name'] for e in tree.iter() if e.tag in {'INPUT', 'OUTPUT', 'INTERNAL', 'CONSTANT'}}

def expression(value):
    value = value.replace('&&', ' and ').replace('||', ' or ')
    value = value.replace('{', '[').replace('}', ']').replace('new BigDecimal', 'BigDecimal')
    return re.sub(r'\b[A-Za-z_][A-Za-z_0-9]*\b', lambda m: 'self.'+m[0] if m[0] in names else m[0], value)

def statements(parent, indent):
    lines = []
    for e in parent:
        p = '    ' * indent
        if e.tag == 'EVAL':
            lines.append(p + expression(e.attrib['exec']))
        elif e.tag == 'EXECUTE':
            lines.append(p + 'self.' + e.attrib['method'] + '()')
        elif e.tag == 'IF':
            lines.append(p + 'if ' + expression(e.attrib['expr']) + ':')
            lines.extend(statements(e.find('THEN'), indent + 1) or [p + '    pass'])
            other = e.find('ELSE')
            if other is not None:
                lines.append(p + 'else:')
                lines.extend(statements(other, indent + 1) or [p + '    pass'])
        else:
            raise ValueError(f'Unknown PAP element: {e.tag}')
    return lines

lines = [
    '"""Generated from the official BMF PAP 2026. Do not edit; run tools/generate_pap.py.',
    'Source: https://www.bmf-steuerrechner.de/javax.faces.resource/daten/xmls/Lohnsteuer2026.xml.xhtml',
    'SHA256: ' + hashlib.sha256(source.read_bytes()).hexdigest(),
    '"""',
    'from decimal_math import BigDecimal', '', 'class Lohnsteuer2026:', '    def __init__(self, **inputs):',
]
inputs = {}
for e in tree.iter():
    if e.tag in {'INPUT','OUTPUT','INTERNAL','CONSTANT'}:
        default = e.attrib.get('default', e.attrib.get('value', 'BigDecimal.ZERO' if e.attrib['type']=='BigDecimal' else '0'))
        lines.append('        self.' + e.attrib['name'] + ' = ' + expression(default))
        if e.tag == 'INPUT':
            inputs[e.attrib['name']] = e.attrib['type']
lines.extend(['        types = '+repr(inputs), '        for name, value in inputs.items():',
              '            if name not in types:', '                raise ValueError(f"Unknown PAP input: {name}")',
              '            setattr(self, name, BigDecimal(value) if types[name] == "BigDecimal" else value)', '', '    def calculate(self):'])
lines.extend(statements(tree.find('.//MAIN'), 2))
lines.append('        return self')
for method in tree.iter('METHOD'):
    lines.extend(['', '    def '+method.attrib['name']+'(self):'])
    lines.extend(statements(method,2))
(ROOT/'pap2026.py').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print('Generated pap2026.py')
