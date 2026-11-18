"""Verify collected files and the final report without rerunning simulations."""
from pathlib import Path
from hashlib import sha256
import ast
import json
import subprocess
import sys
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / 'output/pdf/seven-model-sync/2026-11-18-r4'
read = lambda path: json.loads(path.read_bytes())
hash_file = lambda path: sha256(path.read_bytes()).hexdigest()
jobs = read(HERE / 'job-final-status.json')
assert jobs['selected_completed'] and not jobs['active_in_this_round']
assert read(HERE / 'rollup-check.json')['passed']
collected = 0
for key in ('qwen35', 'falcon-wide'):
    folder = HERE / 'results' / key
    receipt = read(folder / 'collection.json')
    for name, digest in receipt['sha256'].items():
        assert hash_file(folder / name) == digest, (key, name)
        collected += 1
    assert (folder / 'power/calibration.json').read_bytes() == (HERE / (key + '-calibration.json')).read_bytes()
    chosen = next(j for j in jobs['jobs'] if j['JobID'] == receipt['jobs']['power_job'])
    assert chosen['State'] == 'COMPLETED' and chosen['ExitCode'] == '0:0'
    assert chosen['Timelimit'] == 'UNLIMITED'
python_files = list(HERE.glob('*.py'))
for path in python_files:
    ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
pdf = OUT / '200mhz-power.pdf'
pages = PdfReader(pdf).pages
assert len(pages) == 9
candidate_pages = PdfReader(OUT / 'recurrent-state-first-round.pdf').pages
historical_pages = PdfReader(ROOT / 'output/pdf/seven-model-sync/2026-11-18-r3/200mhz-power.pdf').pages
for i, source in enumerate(list(candidate_pages) + list(historical_pages)):
    assert pages[i].extract_text() == source.extract_text(), i
assert hash_file(pdf) == read(OUT / 'combined-receipt.json')['combined_pdf_sha256']
visual = read(HERE / 'pdf-visual-review.json')
assert visual['pdf_sha256'] == hash_file(pdf) and visual['all_pages_visually_passed']
assert visual['pages_reviewed'] == list(range(1, 10))
management = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/check_project.py')],
                            cwd=ROOT, text=True, capture_output=True, check=True)
result = dict(passed=True, python_version=sys.version, collected_files_sha256_checked=collected,
              python_ast_files=len(python_files), pdf_pages=9,
              combined_pdf_sha256=hash_file(pdf), frozen_appendix_text_unchanged=True,
              selected_jobs_complete=True, active_jobs_in_this_round=[],
              rollup_verification='rollup-check.json', visual_verification='pdf-visual-review.json',
              management_command='python -B scripts/check_project.py',
              management_output=management.stdout.strip(),
              limits='Management structure is not product/physical acceptance. No new complete-model RTL or physical signoff was run.')
(HERE / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
print('DELIVERY_VALIDATION_PASS', collected, 'collected SHA; 9 PDF pages; Python AST and management structure')
