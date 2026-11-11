"""Server entry point for the historical whole-result replay."""
import argparse
import json
from pathlib import Path
import platform
import re
import subprocess
import traceback
from replay_legacy import replay, sha

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
a = p.parse_args()
root = a.root.resolve()
manifest = json.loads((root / 'inputs.json').read_text())
if not re.fullmatch('[0-9a-f]{40}', manifest['source_commit']):
    raise ValueError('source commit missing')
for name, expected in manifest['code_sha256'].items():
    if sha(root / 'source' / name) != expected:
        raise ValueError('deployed source drift: ' + name)
for name, expected in manifest['input_sha256'].items():
    if sha(root / name) != expected:
        raise ValueError('deployed input drift: ' + name)
out = root / 'results'
out.mkdir(exist_ok=False)
result = dict(passed=False, source_commit=manifest['source_commit'],
              scope='historical conditional SystemC whole-result replay; not native RTL token/s',
              versions=dict(python=platform.python_version(), SystemC='3.0.2',
                            gcc=subprocess.check_output(['g++', '--version'], text=True).splitlines()[0]))
try:
    result['legacy'] = replay(root / 'inputs', out / 'legacy', root / 'run05-result.json')
    result['passed'] = True
except Exception as error:
    result['error'] = repr(error)
    result['traceback'] = traceback.format_exc()
finally:
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
if not result['passed']:
    raise RuntimeError(result['error'])
print('NATIVE_TOKEN_LEGACY_REPLAY_PASS', flush=True)
