"""Versioned, validated scenario files. Imported results are never trusted."""
import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from payroll import (YEAR, VERIFIED, CzechInput, GermanInput, Child, InputError,
                     calculate_cz, calculate_de)


def calculate(inputs):
    return calculate_cz(inputs) if isinstance(inputs, CzechInput) else calculate_de(inputs)


def document(inputs):
    result = calculate(inputs)
    return {'schema': 'taxcalc-payroll/1', 'year': YEAR, 'verified': VERIFIED,
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'country': result.country, 'inputs': asdict(inputs), 'result': asdict(result)}


def read_scenario(path):
    path = Path(path)
    if path.stat().st_size > 100_000:
        raise InputError('Soubor je příliš velký (maximum 100 kB).')
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(data, dict) or data.get('schema') != 'taxcalc-payroll/1' or type(data.get('year')) is not int or data['year'] != YEAR:
            raise InputError('Očekáván export TaxCalc 3 pro rok 2026. Staré exporty 2.2 nejsou kompatibilní.')
        params = data['inputs']
        if not isinstance(params, dict):
            raise InputError('Neplatná vstupní data.')
        if data['country'] == 'CZ':
            params = dict(params)
            params['children'] = tuple(Child(**c) for c in params.get('children', []))
            inputs = CzechInput(**params)
        elif data['country'] == 'DE':
            inputs = GermanInput(**params)
        else:
            raise InputError('Neznámá země.')
        calculate(inputs)
        return inputs
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        if isinstance(error, InputError):
            raise
        raise InputError('Soubor obsahuje neplatný formát nebo vstupy.') from error


def write_json(path, inputs):
    Path(path).write_text(json.dumps(document(inputs), ensure_ascii=False, indent=2,
                                    default=lambda x: str(x) if isinstance(x, Decimal) else x), encoding='utf-8')


def write_csv(path, inputs):
    data = document(inputs)
    def flatten(value, prefix=''):
        if isinstance(value, dict):
            for key, child in value.items():
                yield from flatten(child, f'{prefix}.{key}' if prefix else key)
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                yield from flatten(child, f'{prefix}.{index+1}')
        else:
            text = str(value)
            if isinstance(value, str) and text.startswith(('=', '+', '-', '@', '\t', '\r')):
                text = "'" + text
            yield prefix, text
    with Path(path).open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Položka', 'Hodnota'])
        writer.writerows(flatten(data))
