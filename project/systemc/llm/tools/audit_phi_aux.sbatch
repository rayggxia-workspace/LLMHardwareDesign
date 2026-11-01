#!/bin/bash
#SBATCH --job-name=yzl-sc153-auxaudit
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:10:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
python3 - "$ROOT" <<'PY'
import pathlib,hashlib,json,subprocess
r=pathlib.Path(__import__('sys').argv[1]);base=json.loads((r/'continuation-r8/final-audit-r13.json').read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(16*1024*1024),b''):h.update(b)
 return dict(bytes=p.stat().st_size,sha256=h.hexdigest())
run=r/'run-phi-fused-r13';d=json.loads((run/'validation.json').read_text());receipt=json.loads((run/'systemc_receipt.json').read_text())
assert len(d['steps'])==3 and len(receipt['generated'])==3 and receipt['norm_adapter']=='fused-scaled-gamma'
paths=[run/name for name in ('validation.json','systemc_receipt.json','run-inputs.sha256','systemc_hidden.bin','systemc_logits.bin')]
paths.extend(sorted((r/'run-phi-r13').glob('stage-*.bin')))
paths.extend([r/'run-phi-r13/stage-diagnostic.json',r/'systemc-src-r13.tar.gz',r/'build-r13/llm_bench',r/'phi-r8/weights.bin'])
files={str(p):sha(p)for p in paths}
for p,h in d['hashes'].items():
 if p in files:assert files[p]['sha256']==h
for p in ('systemc-src-r13.tar.gz','build-r13/llm_bench'):assert files[str(r/p)]==base['files'][str(r/p)]
assert files[str(r/'phi-r8/weights.bin')]==base['models'][0]['files'][str(r/'phi-r8/weights.bin')]
result=dict(scope='additional Phi fused Norm comparison and conditional layer30 diagnostics; not model-quality acceptance',files=files,
 top1_equal=sum(s['top1_equal']for s in d['steps']),logits_cosines=[s['logits']['cosine']for s in d['steps']],
 slurm=subprocess.check_output(['sacct','-j94515,94516,94518,94519,94520,94521,94522,94525,94526,94528,94529','-n','-X','-o','JobID,State,ExitCode,Elapsed,NodeList'],universal_newlines=True))
with (r/'continuation-r8/aux-audit-r13.json').open('x')as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items()if k!='files'}),flush=True)
PY
