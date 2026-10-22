"""Package already-finished run01 without modifying its scientific payloads."""
from pathlib import Path
import hashlib
import json
import zipfile

task = Path('D:/Projects/Codex/qwen3-inference-20261022')
repo = Path('D:/Projects/LLMHardwareDesign-inference')
source = task / 'results/run-01'
target = repo / 'project/experiments/qwen3_trace/results/issue-23-run01'
target.mkdir(parents=True, exist_ok=False)
manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
if json.loads((source / 'summary.json').read_text())['status'] != 'PASS':
    raise ValueError('Packaging does not hide a failed summary')
files = sorted(p for p in source.iterdir() if p.is_file())
index = []
archive = target / 'evidence.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
    for path in files:
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if path.name != 'manifest.json' and manifest['artifacts'][path.name] != digest:
            raise ValueError(f'Manifest mismatch: {path.name}')
        entry = zipfile.ZipInfo(path.name, date_time=(1980, 1, 1, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = 0o100644 << 16
        output.writestr(entry, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        index.append({'file': path.name, 'bytes': len(content), 'sha256': digest})
with zipfile.ZipFile(archive) as check:
    for row in index:
        if hashlib.sha256(check.read(row['file'])).hexdigest() != row['sha256']:
            raise ValueError('Archive readback mismatch')
receipt = {'source_commit': manifest['source_commit'], 'archive': archive.name,
           'bytes': archive.stat().st_size, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
           'members': index, 'scope': 'Finished run01 scientific evidence; no model weights.',
           'packaging_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(target / 'archive-sha256.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
for name in ('summary.json', 'manifest.json'):
    (target / name).write_bytes((source / name).read_bytes())
print(json.dumps({'bytes': receipt['bytes'], 'sha256': receipt['sha256'], 'members': len(index)}))
