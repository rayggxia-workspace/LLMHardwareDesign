"""Verify rounded native Word cells and their visible PDF rendering against frozen data."""
import argparse
import hashlib
import json
import platform
import zipfile
from pathlib import Path

import docx
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('--pdf', type=Path, default=TASK / 'tmp/word-tables/final-render/tables-final.pdf')
a = p.parse_args()
source = TASK / 'combined-results.json'
rows = json.loads(source.read_text(encoding='utf-8'))['models']
path = ROOT / 'output/docx/seven-model-dac-tables.docx'
payload = path.read_bytes()
document = docx.Document(path)
assert len(document.tables) == 2
speed, energy = document.tables
assert (len(speed.rows), len(speed.columns)) == (4, 8)
assert (len(energy.rows), len(energy.columns)) == (5, 9)
for table, start in [(speed, 1), (energy, 2)]:
    for j, row in enumerate(rows, start):
        assert table.cell(0, j).text.replace('\n', '') == row['name']
for i, key in enumerate(['short_prefill_input_tok_s', 'estimated_input_tok_s_to_logits', 'decode_tok_s'], 1):
    for j, row in enumerate(rows, 1):
        assert speed.cell(i, j).text == f"{row['speed'][key]:.3f}"
specs = [('on_chip', 'decode'), ('on_chip', 'prefill'), ('on_chip_plus_ddr', 'decode'), ('on_chip_plus_ddr', 'prefill')]
for i, (scope, phase) in enumerate(specs, 1):
    for j, row in enumerate(rows, 2):
        low, high = row['windows'][phase]['scopes'][scope]['energy_j_per_token']
        assert energy.cell(i, j).text == f'{low:.4f}\u2013{high:.4f}'
for table in document.tables:
    assert sum(c.width.twips for c in table.columns) == 10426
    assert not table._tbl.xpath('.//w:trHeight')
    assert len(table._tbl.xpath('.//w:tblHeader')) == 1
    assert len(table._tbl.xpath('.//w:cantSplit')) == len(table.rows)
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    assert run.font.name == 'Times New Roman' and run.font.size.pt == 8
assert len(energy._tbl.xpath('.//w:vMerge[@w:val="restart"]')) == 2
reader = PdfReader(a.pdf)
assert len(reader.pages) == 1
compact = ''.join(reader.pages[0].extract_text().split())
for table, start in [(speed, 1), (energy, 2)]:
    for row in table.rows[1:]:
        for cell in row.cells[start:]:
            assert ''.join(cell.text.split()) in compact
for text in ['schedule-based estimates', 'not independently validated', 'energy subtotals', 'DDR PHY', 'two-token short-prefill window']:
    assert ''.join(text.split()) in compact
reference = Path('D:/Download/v2-IEEE-integrated.docx')
assert hashlib.sha256(reference.read_bytes()).hexdigest() == '93859d49268877883a61d5fbddaf07692406588d76dc0ec5b5c11a8d4b2b409f'
with zipfile.ZipFile(path) as z:
    assert not any(n.startswith(('word/media/', 'customXml/')) for n in z.namelist())
result = {
    'status': 'passed', 'editable_tables': 2, 'models': 7, 'speed_cells': 21,
    'energy_ranges': 28, 'energy_endpoints': 56, 'pdf_pages': 1,
    'reference_unchanged': True, 'simulation_rerun': False,
    'data_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'docx_sha256': hashlib.sha256(payload).hexdigest(),
    'docx_git_blob_sha1': hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest(),
    'python': platform.python_version(), 'python_docx': docx.__version__,
    'renderer': 'Microsoft Word 16.0 read-only ExportAsFixedFormat; Poppler PNG',
    'render_note': 'Bundled render_docx.py lacked LibreOffice. Approved hidden Word COM used. Existing first PDF could not be overwritten; final export used a distinct filename. Poppler reported unused Symbol/ArialUnicode font-map warnings; displayed content inspected separately.',
    'visual_review_record': 'See WORD_TABLES.md; this script does not perform visual inspection.',
}
(TASK / 'word-tables-qa.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
