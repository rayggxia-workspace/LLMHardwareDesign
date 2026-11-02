#!/bin/bash
#SBATCH --job-name=yzl-sc153-repair-followup-audit
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:15:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
python3 - "$ROOT" <<'PY'
import pathlib,sys,json,hashlib,subprocess,concurrent.futures
r=pathlib.Path(sys.argv[1]);paths=set()
for group in ('router','norm','experts'):
 d=r/('diagnostic-granite-'+group+'-r27')
 paths.update(d.iterdir());paths.add(r/('logs/granite-'+group+'-r27.log'))
paths.update(r/'continuation-r8'/n for n in ('diagnose_quantized_model-r27.py','granite-groups-r27.sbatch','repair-followup-r29.sbatch'))
paths.add(r/'granite-r1/weights.bin');paths.add(r/'granite-r1/export_receipt.json')
for family in ('phi3','gemma3_text','qwen3_5_text','falcon_h1'):
 run=r/('run-'+family+'-fixture-r28');cp=r/(family+'-fixture-g8-r28')
 paths.update(run.iterdir());paths.update(cp.iterdir())
 paths.add(r/('logs/run-'+family+'-fixture-r28.log'))
 v=json.loads((run/'validation.json').read_text())
 paths.update(pathlib.Path(p) for p in v['hashes'])
 for line in (run/'run-inputs.sha256').read_text().splitlines():
  _,p=line.split(maxsplit=1);p=pathlib.Path(p);paths.add(p if p.is_absolute() else r/p)
paths.add(r/'src-r28/project/systemc/llm/tools/requantize_groups.py')
paths.add(r/'src-r28/project/systemc/llm/tools/repair_falcon_metadata.py')
paths.update((r/'logs').glob('*94585*'));paths.update((r/'logs').glob('*94588*'))
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(16*1024*1024),b''):h.update(b)
 return str(p),{'sha256':h.hexdigest(),'bytes':p.stat().st_size}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:files=dict(pool.map(digest,sorted(paths)))
for family in ('phi3','gemma3_text','qwen3_5_text','falcon_h1'):
 run=r/('run-'+family+'-fixture-r28')
 for p,h in json.loads((run/'validation.json').read_text())['hashes'].items():assert files[p]['sha256']==h
 for line in (run/'run-inputs.sha256').read_text().splitlines():
  h,p=line.split(maxsplit=1);p=pathlib.Path(p);p=p if p.is_absolute() else r/p
  assert files[str(p)]['sha256']==h
result={'scope':'independent diagnostic and explicitly synthetic fixture evidence; no real-model acceptance from fixtures',
        'files':files,'slurm':subprocess.check_output(['sacct','-j94580,94585,94588','-n','-X','-o','JobID,State,ExitCode,Elapsed'],universal_newlines=True)}
with (r/'continuation-r8/repair-followup-audit-r29.json').open('x') as f:json.dump(result,f,indent=2)
print('FOLLOWUP_AUDIT',len(files),'files verified')
PY
