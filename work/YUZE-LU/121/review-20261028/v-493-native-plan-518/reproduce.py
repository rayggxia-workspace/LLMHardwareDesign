"""Reproduce the sealed planning result; does not edit any database or file."""
from pathlib import Path
import base64
import gzip
import json
import sys

folder = Path(__file__).resolve().parent
root = folder.parents[4]
sys.path.insert(0, str(root / 'project/experiments/block_v1'))
from revision300_via_realization import plan

records = {name: base64.b64decode(value).decode() for name, value in
           json.loads(gzip.decompress((folder / 'records.json.gz').read_bytes())).items()}
report = next((folder.parent / 'v-494-native-drc-512').rglob('native-whole-drc.rpt')).read_text()
result = plan(report, records, (folder / 'native.tech.lef').read_text())
actual = (json.dumps(result, indent=2) + '\n').encode()
assert actual == gzip.decompress((folder / 'via-plan.json.gz').read_bytes())
print('PASS sealed planning bytes:', len(result['proposals']), 'proposals;',
      len(result['rejected']), 'rejected; no physical qualification')
