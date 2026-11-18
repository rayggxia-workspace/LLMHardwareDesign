"""Select only this round's code, measured receipts and formal report for review."""
from pathlib import Path
from hashlib import sha1, sha256
import json,re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=ROOT/'output/pdf/seven-model-sync/2026-11-18-r4'
assert json.loads((HERE/'rollup-check.json').read_bytes())['passed']
assert json.loads((OUT/'bundle-receipt.json').read_bytes())['isolated_rollup_pass']
formal=ROOT/'docs/experiments/recurrent-state-first-round-200mhz.pdf'
formal.write_bytes((OUT/'200mhz-power.pdf').read_bytes())
excluded={'public-files.json'}
files=[p for p in HERE.iterdir() if p.is_file() and p.name not in excluded]
files+=list((HERE/'rtl').glob('*.sv'))
for key in ('qwen35','falcon-wide','full-pin-preflight','signed-graph-audit'):
    directory=HERE/'results'/key
    files += [p for p in directory.rglob('*') if p.is_file() and p.name not in ('build.log','generate.log')]
files += [formal,ROOT/'docs/handoffs/2026-11-18-issue-280-recurrent-first-round.md']
manifest=[]
for p in sorted(set(files)):
    raw=p.read_bytes()
    if p.suffix in ('.py','.sv','.sbatch','.md','.json','.txt','.log'):
        assert not re.search(rb'-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}',raw)
    manifest.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),
        sha256=sha256(raw).hexdigest(),git_blob_sha1=sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()))
(HERE/'public-files.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PUBLIC_SCOPE_PREPARED',len(manifest),sum(x['bytes'] for x in manifest))
