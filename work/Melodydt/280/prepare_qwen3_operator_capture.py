"""Extend the accepted Qwen3 RMS runner with softmax/native RoPE observation."""
from hashlib import sha256
import json
from pathlib import Path
import runpy
import shutil
import sys

root,bundle,out=map(Path,sys.argv[1:])
runpy.run_path(str(bundle/'prepare_qwen3_arithmetic_capture.py'),run_name='__main__')
runner=out/'runner'
shutil.copy2(str(bundle/'operator_observation.py'),str(runner/'operator_observation.py'))
p=runner/'qwen3_arithmetic_observation.py'
text=p.read_text();old='from arithmetic_observation import ArithmeticObservation'
if text.count(old)!=1:raise ValueError('observer anchor changed')
p.write_text(text.replace(old,'from operator_observation import OperatorObservation as ArithmeticObservation'))
probe=root/'operator-capture-02/run-38830188'
for phase in ('prefill','decode'):
    if not json.loads((probe/phase/'acceptance.json').read_text())['passed']:raise ValueError('probe not accepted')
source=probe/'runner/native_tlm_u.py'
manifest=json.loads((probe/'instrumented-source.json').read_text())
if sha256(source.read_bytes()).hexdigest()!=manifest[source.name]:raise ValueError('native U probe changed')
shutil.copy2(str(source),str(runner/source.name))
hashes={p.name:sha256(p.read_bytes()).hexdigest() for p in runner.iterdir() if p.is_file()}
(out/'instrumented-source.json').write_text(json.dumps(hashes,indent=2)+'\n')
(out/'operator-provenance.json').write_text(json.dumps(dict(scope='Qwen3 softmax/native RoPE and existing RMS only; no arithmetic/event changes',
    native_u_probe=str(source),native_u_sha256=manifest[source.name],files=hashes),indent=2)+'\n')
