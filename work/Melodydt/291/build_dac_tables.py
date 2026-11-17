"""Build editable manuscript-compatible tables from the frozen seven-model report."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Twips

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
ORDER = ['qwen3', 'llama', 'phi', 'gemma', 'granite', 'qwen35', 'falcon']
HEADERS = ['Qwen3-\n0.6B', 'Llama3.2-\n1B', 'Phi4-\nmini', 'Gemma3-\n4B', 'Granite3.1-\n3B-A800M', 'Qwen3.5-\n4B', 'Falcon-H1-\n3B']
WIDTH = 10426
DATA_WIDTHS = [1203] * 6 + [1208]


def element(tag, **attrs):
    e = OxmlElement('w:' + tag)
    for k, v in attrs.items():
        e.set(qn('w:' + k), str(v))
    return e


def font(run, size=8, bold=False, small_caps=False):
    run.font.name = 'Times New Roman'
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.small_caps = small_caps
    rf = run._r.get_or_add_rPr().rFonts
    for attr in ('ascii', 'hAnsi', 'eastAsia', 'cs'):
        rf.set(qn('w:' + attr), 'Times New Roman')


def paragraph(p, style='table copy', size=8, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER):
    p.style = style
    pf = p.paragraph_format
    pf.alignment = align
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = 1.0
    pf.keep_with_next = False
    pf.widow_control = True
    pf.left_indent = Pt(0)
    pf.right_indent = Pt(0)
    pf.first_line_indent = Pt(0)
    num = p._p.get_or_add_pPr().get_or_add_numPr()
    num.append(element('numId', val=0))
    for r in p.runs:
        font(r, size, bold)


def cell_text(cell, value, header=False, left=False):
    cell.text = value
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    paragraph(cell.paragraphs[0], 'table col head' if header else 'table copy',
              bold=header, align=WD_ALIGN_PARAGRAPH.LEFT if left else WD_ALIGN_PARAGRAPH.CENTER)


def rule(cell, edge, size=4):
    pr = cell._tc.get_or_add_tcPr()
    borders = pr.find(qn('w:tcBorders'))
    if borders is None:
        borders = element('tcBorders')
        pr.append(borders)
    borders.append(element(edge, val='single', sz=size, color='000000'))


def make_table(doc, nrows, widths, headers):
    table = doc.add_table(rows=nrows, cols=len(widths))
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    pr = table._tbl.tblPr
    for tag in ('tblW', 'tblBorders', 'tblCellMar', 'tblLayout', 'tblInd', 'tblLook'):
        for old in list(pr.findall(qn('w:' + tag))):
            pr.remove(old)
    pr.append(element('tblW', w=sum(widths), type='dxa'))
    pr.append(element('tblLayout', type='fixed'))
    pr.append(element('tblInd', w=0, type='dxa'))
    borders = element('tblBorders')
    for edge in ('top', 'bottom'):
        borders.append(element(edge, val='single', sz=8, color='000000'))
    for edge in ('left', 'right', 'insideH', 'insideV'):
        borders.append(element(edge, val='nil'))
    pr.append(borders)
    margins = element('tblCellMar')
    for edge, val in [('top', 70), ('bottom', 70), ('left', 35), ('right', 35)]:
        margins.append(element(edge, w=val, type='dxa'))
    pr.append(margins)
    for col, width in zip(table.columns, widths):
        col.width = Twips(width)
    for row in table.rows:
        row._tr.get_or_add_trPr().append(element('cantSplit'))
        for c, width in zip(row.cells, widths):
            c.width = Twips(width)
    table.rows[0]._tr.get_or_add_trPr().append(element('tblHeader'))
    for c, value in zip(table.rows[0].cells, headers):
        cell_text(c, value, header=True)
        rule(c, 'bottom')
    return table


def caption(doc, number, title, first=False):
    p = doc.add_paragraph(style='table head')
    p.add_run('TABLE ' + number + '\n' + title)
    paragraph(p, 'table head')
    p.paragraph_format.space_before = Pt(0 if first else 15)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    for r in p.runs:
        font(r, small_caps=True)


def note(doc, text):
    p = doc.add_paragraph(text)
    paragraph(p, size=7.5, align=WD_ALIGN_PARAGRAPH.LEFT)
    p.paragraph_format.space_before = Pt(4)
    return p


def build(reference, source, output):
    before = hashlib.sha256(reference.read_bytes()).hexdigest()
    raw = json.loads(source.read_text(encoding='utf-8'))
    indexed = {r['model']: r for r in raw['models']}
    rows = [indexed[m] for m in ORDER]
    doc = Document(reference)
    section = copy.deepcopy(doc._element.body.sectPr)
    for child in list(doc._element.body):
        doc._element.body.remove(child)
    doc._element.body.append(section)
    cols = section.find(qn('w:cols'))
    if cols is None:
        cols = element('cols')
        section.append(cols)
    for child in list(cols):
        cols.remove(child)
    cols.set(qn('w:num'), '1')
    cols.set(qn('w:space'), '360')
    sect_type = section.find(qn('w:type'))
    if sect_type is not None:
        section.remove(sect_type)
    # Omit reference illustrations and bibliography/custom XML from this table-only insert.
    for rid, rel in list(doc.part.rels.items()):
        if rel.reltype.endswith(('/image', '/customXml')):
            doc.part.drop_rel(rid)
    for rid, rel in list(doc.part.package.rels.items()):
        if rel.reltype.endswith('/custom-properties'):
            del doc.part.package.rels[rid]
    props = doc.core_properties
    props.title = 'Seven-model throughput and covered energy per token'
    props.author = 'Melodydt'
    props.last_modified_by = 'Melodydt'
    props.subject = 'Editable full-width tables for the current manuscript'
    props.comments = 'Frozen simulation results; estimates and coverage limits are stated in table notes.'
    props.keywords = 'TLM; throughput; energy; seven models'
    caption(doc, 'II', 'Full-Layer System-Level Throughput (token/s)', first=True)
    st = make_table(doc, 4, [2000] + DATA_WIDTHS, ['Phase'] + HEADERS)
    speed_specs = [
        ('Short prefill', 'short_prefill_input_tok_s'),
        ('512-token prefill*', 'estimated_input_tok_s_to_logits'),
        ('Decode', 'decode_tok_s'),
    ]
    speed_expected = []
    for i, (label, key) in enumerate(speed_specs, 1):
        cell_text(st.cell(i, 0), label, left=True)
        values = [f"{r['speed'][key]:.3f}" for r in rows]
        speed_expected.append(values)
        for j, value in enumerate(values, 1):
            cell_text(st.cell(i, j), value)
    note(doc, 'System-level TLM evaluation at a nominal 300 MHz with 512-bit SRAM. Prefill throughput counts input tokens; decode throughput counts output tokens. Short prefill executes all layers for two input tokens and excludes the final output head. Decode measures the interval between two token retirements after a 512-token history.')
    note(doc, '* The 512-token prefill values are schedule-based estimates including one final output head, not independently validated full-sequence measurements. Linear approximation is retained for models with nonlinear sampled behavior; no measured full-sequence error bound is available.')
    caption(doc, 'III', 'Covered Energy per Token (J/token)')
    et = make_table(doc, 5, [1120, 880] + DATA_WIDTHS, ['Scope', 'Phase'] + HEADERS)
    energy_expected = []
    for first_row, scope, label in [(1, 'on_chip', 'On-chip'), (3, 'on_chip_plus_ddr', 'On-chip\n+ DDR')]:
        group = et.cell(first_row, 0).merge(et.cell(first_row + 1, 0))
        cell_text(group, label, left=True)
        for offset, phase in enumerate(['decode', 'prefill']):
            i = first_row + offset
            cell_text(et.cell(i, 1), phase.capitalize(), left=True)
            values = []
            for j, r in enumerate(rows, 2):
                low, high = r['windows'][phase]['scopes'][scope]['energy_j_per_token']
                value = f'{low:.4f}\u2013{high:.4f}'
                values.append(value)
                cell_text(et.cell(i, j), value)
            energy_expected.append(values)
    for c in et.rows[3].cells:
        rule(c, 'top')
    note(doc, 'Prefill energy refers to the two-token short-prefill window, not the estimated 512-token case. Values are low\u2013high calibration endpoints, not confidence intervals or complete uncertainty bounds.')
    note(doc, 'Both scopes are covered energy subtotals. Uncalibrated read-DMA contributions, special arithmetic, and remaining control/clock/interconnect contributions are excluded; wire parasitics are omitted. The DDR scope adds DDR-chip energy and excludes DDR PHY and board energy.')
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    assert hashlib.sha256(reference.read_bytes()).hexdigest() == before
    return {'reference': str(reference), 'reference_sha256': before,
            'source': str(source.relative_to(ROOT)), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'output': str(output.relative_to(ROOT)), 'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'model_order': ORDER, 'speed_values': speed_expected, 'energy_ranges': energy_expected,
            'table_width_twips': WIDTH, 'font': 'Times New Roman', 'table_font_pt': 8,
            'original_manuscript_unchanged': True, 'full_prefill512_independent_validation': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--reference', type=Path, default=Path('D:/Download/v2-IEEE-integrated.docx'))
    p.add_argument('--source', type=Path, default=TASK / 'combined-results.json')
    p.add_argument('--output', type=Path, default=ROOT / 'output/docx/seven-model-dac-tables.docx')
    a = p.parse_args()
    receipt = build(a.reference, a.source, a.output)
    (TASK / 'word-tables-manifest.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('speed_values', 'energy_ranges')}, ensure_ascii=False, indent=2))
