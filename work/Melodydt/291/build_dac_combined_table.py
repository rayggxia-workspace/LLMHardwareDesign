"""Combine frozen throughput and lower energy endpoints into one editable Word table."""
import copy
import hashlib
import json
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from build_dac_tables import ORDER, HEADERS, caption, cell_text, element, make_table, note, rule

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
SOURCE = TASK / 'combined-results.json'
REFERENCE = ROOT / 'output/docx/seven-model-dac-tables.docx'
OUTPUT = ROOT / 'output/docx/seven-model-dac-combined-table.docx'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    assert sha(SOURCE) == '741b593914265932c88c1b9924bdd80d8e8ae3e78e1652741cd66b4c3bf200e9'
    assert sha(REFERENCE) == 'e5881fac9aebcbf4b047d0a0dcf35276d3e943747161e5479054b39626d5e9bf'
    model_index = {r['model']: r for r in json.loads(SOURCE.read_text(encoding='utf-8'))['models']}
    rows = [model_index[m] for m in ORDER]
    doc = Document(REFERENCE)
    section = copy.deepcopy(doc._element.body.sectPr)
    for child in list(doc._element.body):
        doc._element.body.remove(child)
    doc._element.body.append(section)
    doc.core_properties.title = 'Seven-model combined throughput and covered energy table'
    doc.core_properties.subject = 'Prefill and decode columns; energy lower calibration endpoints'
    caption(doc, 'II', 'Seven-Model Throughput and Covered Energy', first=True)
    table = make_table(doc, 5, [1660] + [626] * 13 + [628], [''] * 15)
    for cell in table.rows[0].cells:
        borders = cell._tc.get_or_add_tcPr().find(qn('w:tcBorders'))
        if borders is not None:
            cell._tc.get_or_add_tcPr().remove(borders)
    table.rows[1]._tr.get_or_add_trPr().append(element('tblHeader'))
    metric = table.cell(0, 0).merge(table.cell(1, 0))
    cell_text(metric, 'Metric', header=True)
    rule(metric, 'bottom')
    for m, header in enumerate(HEADERS):
        j = 1 + 2 * m
        group = table.cell(0, j).merge(table.cell(0, j + 1))
        cell_text(group, header, header=True)
        rule(group, 'bottom')
        for k, label in enumerate(['Prefill', 'Decode']):
            cell_text(table.cell(1, j + k), label, header=True)
            rule(table.cell(1, j + k), 'bottom')
    # Compact numeric columns retain sufficient width for six-character values at 8 pt.
    margins = table._tbl.tblPr.find(qn('w:tblCellMar'))
    for side in ['left', 'right']:
        margins.find(qn('w:' + side)).set(qn('w:w'), '20')
    labels = ['Throughput*\n(token/s)', 'On-chip energy\u2020\n(J/token)', 'On-chip + DDR\nenergy\u2020 (J/token)']
    expected = [[], [], []]
    for i, label in enumerate(labels, 2):
        cell_text(table.cell(i, 0), label, left=True)
    for m, row in enumerate(rows):
        for k, phase in enumerate(['prefill', 'decode']):
            j = 1 + 2 * m + k
            speed_key = 'estimated_input_tok_s_to_logits' if phase == 'prefill' else 'decode_tok_s'
            values = [f"{row['speed'][speed_key]:.3f}"]
            for scope in ['on_chip', 'on_chip_plus_ddr']:
                low, high = row['windows'][phase]['scopes'][scope]['energy_j_per_token']
                assert low <= high
                values.append(f'{low:.4f}')
            for i, value in enumerate(values, 2):
                cell_text(table.cell(i, j), value)
                expected[i - 2].append(value)
    note(doc, '* Prefill throughput is estimated for 512 input tokens, including one final output head; decode throughput uses the interval between two token retirements after a 512-token history. The prefill estimate follows the current per-token schedule and has not been independently validated over the full sequence; linear approximation is retained where sampled behavior is nonlinear.')
    p = note(doc, '\u2020 Prefill energy refers to the two-token short-prefill window, not the 512-token throughput case. All energy values are the lower endpoints of the existing calibration ranges. Both scopes are covered subtotals; read DMA, uncalibrated special arithmetic and remaining control/clock/interconnect contributions, DDR PHY and board energy are excluded. Wire parasitics are omitted.')
    p.runs[0].text = '\u2020 Prefill energy refers to the two-token short-prefill window, not the 512-token throughput case. '
    p.runs[0].bold = True
    extra = p.add_run('All energy values are the lower endpoints of the existing calibration ranges. Both scopes are covered subtotals; read DMA, uncalibrated special arithmetic and remaining control/clock/interconnect contributions, DDR PHY and board energy are excluded. Wire parasitics are omitted.')
    from build_dac_tables import font
    font(extra, size=7.5)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    assert sha(REFERENCE) == 'e5881fac9aebcbf4b047d0a0dcf35276d3e943747161e5479054b39626d5e9bf'
    receipt = {'source_sha256': sha(SOURCE), 'reference_sha256': sha(REFERENCE), 'output_sha256': sha(OUTPUT),
               'output': str(OUTPUT.relative_to(ROOT)), 'model_order': ORDER, 'phase_order': ['prefill', 'decode'],
               'values_by_row': expected, 'energy_endpoint': 'lower', 'prefill_throughput_tokens': 512,
               'prefill_energy_tokens': 2, 'full_prefill512_independent_validation': False,
               'source_commit': '31d6e0011f3f06c8d0bf1106db2fc9cec95b0c0c', 'table_width_twips': 10426}
    (TASK / 'merged-table-manifest.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    build()
