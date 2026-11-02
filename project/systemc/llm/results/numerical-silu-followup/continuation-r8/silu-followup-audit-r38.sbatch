#!/bin/bash
#SBATCH --job-name=yzl-sc153-silu-audit
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=3
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
python3 - "$ROOT" <<'PY'
import pathlib,sys,json,hashlib,concurrent.futures,subprocess,os
root=pathlib.Path(sys.argv[1])
cases={
 'oracle-granite-r32':'granite-residual-r32',
 'firstbad-qwen25-r31-r34':'qwen25-r2',
 'firstbad-qwen25-r33-r34':'qwen25-r2',
 'oracle-qwen25-hidden-r34':'qwen25-r2',
 'firstbad-qwen25-r35-r37':'qwen25-r2',
 'run-qwen25-extra-r36':'qwen25-extra-r36',
 'run-granite-extra-r36':'granite-extra-r36'}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(16*1024*1024),b''):h.update(b)
 return {'sha256':h.hexdigest(),'bytes':p.stat().st_size}
files=set()
for name,cpname in cases.items():
 run=root/name;cp=root/cpname
 files.update(p for p in run.iterdir()if p.is_file())
 files.update(cp/n for n in ('weights.bin','weights.index','metadata.txt','prompt.txt','export_receipt.json','reference_hidden.bin','reference_logits.bin'))
 if (cp/'weights.scales').exists():files.add(cp/'weights.scales')
 files.add(root/'logs'/(name+'.log'))
 if (run/'run-inputs.sha256').exists():
  for line in (run/'run-inputs.sha256').read_text().splitlines():
   h,p=line.split(maxsplit=1);p=pathlib.Path(p)
   if not p.is_absolute():p=root/p
   p.relative_to(root);files.add(p)
extras=('diagnose_dense_layer-r34.py','diagnose_quantized_model-r34.py','diagnose_first_bad-r34.sbatch','silu-layer-r37.sbatch','extra-prompts-r36.sbatch','accurate-silu-r35.sbatch','expert-residuals-r32.sbatch','block-scales-r33.sbatch','audit-r35.sbatch','audit-r35b.sbatch','silu-followup-audit-r38.sbatch')
files.update(root/'continuation-r8'/n for n in extras)
files.update(root/'logs'/n for n in ('expert-residuals-r32-94614.out','firstbad-r34-94624.out','silu-layer-r37-94641.out','prepare-prompts-r36-94637.out','run-prompts-r36-94646.out','prepare-qwen25-extra-r36.log','prepare-granite-extra-r36.log','audit-r35-94638.out','audit-r35b-94647.out'))
with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:
 hashes=dict(zip(map(str,sorted(files)),pool.map(sha,sorted(files))))
for name,cpname in cases.items():
 run=root/name;cp=root/cpname;ex=json.loads((cp/'export_receipt.json').read_text())
 assert hashes[str(cp/'weights.bin')]['sha256']==ex['weights_sha256']
 if (cp/'weights.scales').exists():assert hashes[str(cp/'weights.scales')]['sha256']==ex['weight_scales_sha256']
 if (run/'validation.json').exists():
  v=json.loads((run/'validation.json').read_text());rc=json.loads((run/'systemc_receipt.json').read_text())
  assert len(v['steps'])==len(rc['inputs'])==len(ex['reference_inputs'])==3
  for p,h in v['hashes'].items():assert hashes[p]['sha256']==h
 if (run/'run-inputs.sha256').exists():
  for line in (run/'run-inputs.sha256').read_text().splitlines():
   h,p=line.split(maxsplit=1);p=pathlib.Path(p)
   if not p.is_absolute():p=root/p
   assert hashes[str(p)]['sha256']==h
result={'scope':'allocated-node audit of SiLU causal controls and additional short inputs; all negative controls retained','cases':cases,'files':hashes,'audit_job':os.environ['SLURM_JOB_ID'],
 'slurm':subprocess.check_output(['sacct','-j94614,94617,94620,94624,94634,94637,94638,94641,94646,94647','-n','-X','-o','JobID,State,ExitCode,Elapsed,NodeList'],universal_newlines=True)}
with (root/'continuation-r8/silu-followup-audit-r38.json').open('x')as f:json.dump(result,f,indent=2)
print('Audited',len(cases),'cases and',len(hashes),'files',flush=True)
PY
