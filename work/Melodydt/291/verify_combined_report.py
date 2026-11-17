"""Validate source hashes, independent unit conversions and PDF content."""
import csv
import hashlib
import json
import math
import re
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
PDF = REPO/'output/pdf/seven-model-speed-and-energy-evaluation.pdf'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def normalized(text):
    return re.sub(r'\s+', '', text)


data = read(ROOT/'combined-results.json')
for entry in data['sources']['inputs']:
    assert hashlib.sha256((REPO/entry['path']).read_bytes()).hexdigest() == entry['sha256']
assert len(data['models']) == 7
checks = 0
for model in data['models']:
    assert model['full_prefill512_prediction_error_percent'] is None
    assert model['prefill512_power_evaluated'] is False
    original = read(REPO/'work/Melodydt/280'/('{}_tlm_power_v2_no_wire.json'.format(model['model'])))
    for phase, row in model['windows'].items():
        source = original['windows'][phase]
        count = Decimal(source['tokens'])
        for scope, sourcekey in [('on_chip', 'covered_on_chip_subtotal'), ('on_chip_plus_ddr', 'covered_subtotal')]:
            original_energy = source[sourcekey]['energy_nj_per_window']
            expected_energy = [Decimal(str(x))/Decimal(10)**9 for x in original_energy]
            expected_power = [Decimal(str(x))*Decimal(1000)/Decimal(source['elapsed_ps']) for x in original_energy]
            expected_per_token = [x/count for x in expected_energy]
            expected_efficiency = [count/expected_energy[1], count/expected_energy[0]]
            for key, expected in [('average_power_w', expected_power), ('energy_j_per_token', expected_per_token), ('tokens_per_joule', expected_efficiency)]:
                actual = row['scopes'][scope][key]
                for a, e in zip(actual, expected):
                    assert math.isclose(a, float(e), rel_tol=1e-12), (model['model'], phase, key)
                    checks += 1
    original_speed = read(ROOT/'seven-model-speed-results.json')['models'][model['model']]
    assert model['speed'] == original_speed
with (ROOT/'combined-power-units.csv').open(encoding='utf-8-sig', newline='') as f:
    csvrows = list(csv.DictReader(f))
assert len(csvrows) == 28
reader = PdfReader(PDF)
pages = [page.extract_text() for page in reader.pages]
all_text = normalized(''.join(pages))
expected = read(ROOT/'combined-pdf-expected-text.json')
missing = [x for x in expected if normalized(x) not in all_text]
assert not missing, missing[:10]
assert normalized(data['paper_chinese']) in all_text
assert normalized(data['paper_english']) in all_text
assert all('P512为条件估计' in normalized(text) for text in pages)
assert all(len(text) > 250 for text in pages)
assert not any('\ufffd' in text for text in pages)
for required in ['未知／未验证', '不是512-token Prefill功耗', '14.83', 'J/token', 'token/J']:
    assert normalized(required) in all_text, required
receipt = dict(status='passed', source_hashes=len(data['sources']['inputs']), models=7,
               matched_windows=14, converted_scope_rows=28, independent_decimal_endpoint_checks=checks,
               pdf_pages=len(pages), pdf_cell_and_warning_checks=len(expected), paper_paragraphs=2,
               pdf_sha256=hashlib.sha256(PDF.read_bytes()).hexdigest(),
               independent_sequence_validation='not executed; deferred by user',
               validation_scope='Report arithmetic, frozen sources, units and document content only')
(ROOT/'combined-validation.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
print(json.dumps(receipt, ensure_ascii=False))
