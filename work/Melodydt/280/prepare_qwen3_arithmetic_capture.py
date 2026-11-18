"""Reuse the accepted Qwen3 runner and the byte-matched, tested RMS instrument."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

root, bundle, out = map(Path, sys.argv[1:])
original = root / 'no-wire-extension-01/qwen3-38825995'
llama = root / 'six-model-energy-01/run-38820601-llama'
probe = root / 'common-arithmetic-capture-01/run-38828362'
if (original/'runner/qwen3_rms.py').read_bytes() != (llama/'runner/qwen3_rms.py').read_bytes():
    raise ValueError('Qwen3 and Llama RMS source differ; explicit adaptation required')
if not json.loads((probe/'prefill/acceptance.json').read_text())['passed']:
    raise ValueError('tested RMS probe not accepted')
manifest = json.loads((probe/'instrumented-source.json').read_text())
if sha256((probe/'runner/qwen3_rms.py').read_bytes()).hexdigest() != manifest['qwen3_rms.py']:
    raise ValueError('tested RMS probe changed')
out.mkdir()
runner = out/'runner'
shutil.copytree(str(original/'runner'),str(runner))
for name in ('arithmetic_observation.py','six_model_observation.py','qwen3_arithmetic_observation.py'):
    shutil.copy2(str(bundle/name),str(runner/name))
shutil.copy2(str(probe/'runner/qwen3_rms.py'),str(runner/'qwen3_rms.py'))
qwen = runner/'qwen3_short.py'
text = qwen.read_text()
anchor = 'from ordinary_m_observation import Observation'
if text.count(anchor) != 1:
    raise ValueError('Qwen3 observer anchor changed')
qwen.write_text(text.replace(anchor,'from qwen3_arithmetic_observation import Observation'))
for name in ('ddr-dma-probe.so','projection_math.so'):
    (out/name).symlink_to(original/name)
hashes = {p.name:sha256(p.read_bytes()).hexdigest() for p in runner.iterdir() if p.is_file()}
(out/'instrumented-source.json').write_text(json.dumps(hashes,indent=2)+'\n')
(out/'capture-provenance.json').write_text(json.dumps(dict(
    original=str(original), source_manifest_sha256=sha256((original/'results.sha256').read_bytes()).hexdigest(),
    tested_probe=str(probe), probe_commit=(bundle/'source-commit.txt').read_text().strip(),
    original_rms_sha256=sha256((original/'runner/qwen3_rms.py').read_bytes()).hexdigest(),
    libraries={n:sha256((out/n).read_bytes()).hexdigest() for n in ('ddr-dma-probe.so','projection_math.so')}
),indent=2)+'\n')
