#!/bin/bash
#SBATCH --job-name=yzl-sc153-repair-aux-audit
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=6
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
python3 - "$ROOT" <<'PY'
import pathlib,sys,json,hashlib,concurrent.futures,subprocess
root=pathlib.Path(sys.argv[1])
cases=('qwen25-p15-r18','falcon-old-scale-r22','falcon-p15-scale-r22','qwen35-extra-r24','granite-extra-r25')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(16*1024*1024),b''):h.update(b)
 return {'sha256':h.hexdigest(),'bytes':p.stat().st_size}
def audit(case):
 cp=root/case;run=root/('run-'+case)
 export=json.loads((cp/'export_receipt.json').read_text());validation=json.loads((run/'validation.json').read_text());receipt=json.loads((run/'systemc_receipt.json').read_text())
 assert len(receipt['inputs'])==len(validation['steps'])==3
 assert len(receipt['generated'])==3
 files=[cp/n for n in ('weights.bin','weights.index','metadata.txt','prompt.txt','export_receipt.json','reference_hidden.bin','reference_logits.bin')]
 files += [p for p in run.iterdir()if p.is_file()]
 logfile={'qwen25-p15-r18':'weight15-r18-94550.out','granite-extra-r25':'extra-granite-r25-94575.out'}.get(case,'run-'+case+'.log')
 files += [root/'logs'/logfile]
 hashes={str(p):sha(p)for p in files}
 assert hashes[str(cp/'weights.bin')]['sha256']==export['weights_sha256']
 for p,h in validation['hashes'].items():assert hashes[p]['sha256']==h
 for line in (run/'run-inputs.sha256').read_text().splitlines():
  h,p=line.split(maxsplit=1);p=pathlib.Path(p)
  if not p.is_absolute():p=root/p
  p.relative_to(root)
  hashes[str(p)]=sha(p)
  assert hashes[str(p)]['sha256']==h
 return {'case':case,'files':hashes,'top1_equal':sum(s['top1_equal']for s in validation['steps']),
         'same_reference_prefix':validation['same_prefix_as_original_greedy_reference'],
         'logits':[s['logits']for s in validation['steps']],
         'max_hidden_relative_l2':max(h['relative_l2']for s in validation['steps']for h in s['hidden'])}
with concurrent.futures.ThreadPoolExecutor(max_workers=5)as pool:reports=list(pool.map(audit,cases))
extras=[root/('run-falcon-'+r)/'timestep-diagnostic.json'for r in ('r17','r19','r20')]
extras += [root/'continuation-r8'/n for n in ('diagnose_quantized_model-r17.py','requantize_checkpoint-r18.py','diagnose_falcon_timestep-r20.py','repair_falcon_metadata-r22.py','prepare_prompt_case-r24.py','prepare_prompt_case-r25.py','repair-aux-r26.sbatch','diagnose_quantized_model-r26.py')]
extras += [root/'logs/repair-aux-r25-94577.out']
extras += [root/'diagnostic-granite-quant-r26'/n for n in ('systemc_receipt.json','quantized-model-diagnostic.json')]
extras += [root/'logs/run-granite-extra-r24.log']
extras += [pathlib.Path('/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/lib/python3.12/site-packages/transformers/models/falcon_h1/modeling_falcon_h1.py')]
result={'scope':'actual auxiliary numerical repair evidence; no hardware or general quality qualification',
        'cases':reports,'extra_files':{str(p):sha(p)for p in extras},
        'slurm':subprocess.check_output(['sacct','-j94550,94560,94562,94569,94572,94575,94577','-n','-X','-o','JobID,State,ExitCode,Elapsed,NodeList'],universal_newlines=True)}
with (root/'continuation-r8/repair-aux-audit-r26.json').open('x')as f:json.dump(result,f,indent=2)
print(json.dumps({r['case']:r['top1_equal']for r in reports}),flush=True)
PY
