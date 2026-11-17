"""Check the merged table against frozen data and its actual Word-rendered PDF."""
import hashlib
import json
import platform
from pathlib import Path

import docx
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
source = TASK / 'combined-results.json'
rows = json.loads(source.read_text(encoding='utf-8'))['models']
path = ROOT / 'output/docx/seven-model-dac-combined-table.docx'
data = path.read_bytes()
document = docx.Document(path)
assert len(document.tables) == 1
table = document.tables[0]
assert (len(table.rows), len(table.columns)) == (5, 15)
assert len(table._tbl.xpath('.//w:gridSpan[@w:val="2"]')) == 7
assert len(table._tbl.xpath('.//w:vMerge[@w:val="restart"]')) == 1
assert len(table._tbl.xpath('.//w:tblHeader')) == 2
assert len(table._tbl.xpath('.//w:cantSplit')) == 5
assert not table._tbl.xpath('.//w:trHeight')
assert sum(c.width.twips for c in table.columns) == 10426
expected = []
for m, row in enumerate(rows):
    j = 1 + 2 * m
    assert table.cell(0, j).text.replace('\n', '') == row['name']
    for k, phase in enumerate(['prefill', 'decode']):
        assert table.cell(1, j + k).text == phase.capitalize()
        key = 'estimated_input_tok_s_to_logits' if phase == 'prefill' else 'decode_tok_s'
        vals = [f"{row['speed'][key]:.3f}"]
        for scope in ['on_chip', 'on_chip_plus_ddr']:
            vals.append(f"{row['windows'][phase]['scopes'][scope]['energy_j_per_token'][0]:.4f}")
        for i, val in enumerate(vals, 2):
            assert table.cell(i, j + k).text == val
            expected.append(val)
for row in table.rows:
    for cell in row.cells:
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                assert run.font.name == 'Times New Roman' and run.font.size.pt == 8
pdf = TASK / 'tmp/combined-table-render/combined-table.pdf'
reader = PdfReader(pdf)
assert len(reader.pages) == 1
text = ''.join(reader.pages[0].extract_text().split())
for val in expected:
    assert val in text
for phrase in ['512 input tokens', 'two-token short-prefill window', 'lower endpoints', 'covered subtotals', 'Wire parasitics are omitted']:
    assert ''.join(phrase.split()) in text
for filename, digest in [
    (source, '741b593914265932c88c1b9924bdd80d8e8ae3e78e1652741cd66b4c3bf200e9'),
    (ROOT / 'output/docx/seven-model-dac-tables.docx', 'e5881fac9aebcbf4b047d0a0dcf35276d3e943747161e5479054b39626d5e9bf'),
    (Path('D:/Download/v2-IEEE-integrated.docx'), '93859d49268877883a61d5fbddaf07692406588d76dc0ec5b5c11a8d4b2b409f'),
]:
    assert hashlib.sha256(filename.read_bytes()).hexdigest() == digest
receipt = {
    'status': 'passed', 'editable_tables': 1, 'header_rows': 2, 'model_spans': 7,
    'phase_columns': 14, 'metric_rows': 3, 'numeric_cells': len(expected), 'pdf_pages': 1,
    'energy_endpoint': 'lower', 'prefill_throughput_tokens': 512, 'prefill_energy_tokens': 2,
    'originals_unchanged': True, 'new_simulations': False,
    'docx_sha256': hashlib.sha256(data).hexdigest(),
    'docx_git_blob_sha1': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest(),
    'python': platform.python_version(), 'python_docx': docx.__version__,
    'renderer': 'Microsoft Word 16.0 read-only ExportAsFixedFormat and Poppler PNG',
    'canonical_renderer': 'Attempted; FileNotFoundError: LibreOffice soffice.exe was not found on PATH',
    'visual_review_record': 'See MERGED_WORD_TABLE.md; script does not perform visual inspection.',
}
(TASK / 'merged-table-qa.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps(receipt, indent=2))
