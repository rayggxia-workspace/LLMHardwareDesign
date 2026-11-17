"""Check the PDF against the frozen HTML; this is document QA only."""
import hashlib
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
PDF = ROOT.parents[2]/'output/pdf/seven-model-speed-evaluation.pdf'


def normalized(value):
    value = value.replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-').replace('⚠', '注意：')
    return re.sub(r'\s+', '', value)


html = ROOT/'seven-model-speed-report.html'
soup = BeautifulSoup(html.read_text(encoding='utf-8'), 'html.parser')
reader = PdfReader(PDF)
texts = [p.extract_text() for p in reader.pages]
joined = normalized(''.join(texts))
cells = soup.find_all(['td', 'th'])
missing = [x.get_text() for x in cells if normalized(x.get_text()) not in joined]
assert not missing, missing
warnings = soup.select('div.warning')
for warning in warnings:
    assert normalized(warning.get_text()) in joined, warning.get_text()
models = json.loads((ROOT/'seven-model-speed-results.json').read_text(encoding='utf-8'))['models']
for result in models.values():
    assert normalized(result['name']) in joined
    for key in ('short_prefill_ms', 'estimated_prefill_to_logits_s', 'decode_tok_s'):
        assert format(result[key], '.6f') in joined
assert all('独立序列验证暂缓' in normalized(t) for t in texts)
assert all(len(t) > 200 for t in texts)
assert all('\ufffd' not in t for t in texts)
links = [a.get_object() for p in reader.pages for a in p.get('/Annots', [])]
external_links = [x for x in links if x.get('/A', {}).get('/URI')]
assert len(external_links) == 2
receipt = dict(status='passed', pages=len(reader.pages), table_cells_checked=len(cells),
    warning_boxes_checked=len(warnings), models_checked=len(models), external_links=len(external_links),
    source_html_sha256=hashlib.sha256(html.read_bytes()).hexdigest(),
    pdf_sha256=hashlib.sha256(PDF.read_bytes()).hexdigest(),
    validation_scope='Document content and format checks only; no new simulation or independent sequence validation.')
(ROOT/'pdf-validation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(receipt, ensure_ascii=False))
