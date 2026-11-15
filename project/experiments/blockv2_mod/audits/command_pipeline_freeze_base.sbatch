#!/bin/bash
#SBATCH --job-name=yzl-pipeline-base
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/compiler:$PWD/hardware"
control="$1";assembly="$2";seed="$3";out="$4";shift 4
mkdir -p "$out"
"$python" audits/command_pipeline_seal.py --assembly-receipt "$assembly/receipt.json" --evidence "$@" --output "$out/capacity.json"
"$python" hardware/build_shared_memory_inventory.py --seed "$seed" --assembly-receipt "$assembly/receipt.json" --control-receipt "$control/receipt.json" --control-xml-directory "$control" --capacity-evidence "$out/capacity.json" --output "$out/hardware.json"
export PIPELINE_ASSEMBLY="$assembly" PIPELINE_OUTPUT="$out"
"$python" - <<'PY'
from pathlib import Path
import json,hashlib,os
r=Path.cwd();receipt=Path(os.environ['PIPELINE_ASSEMBLY'])/'receipt.json';assembly=json.loads(receipt.read_text());p=Path('hardware/service-controller-contracts.json');d=json.loads(p.read_text())
retained=[];excluded=[]
for service in d['services']:
 f=(r/service['rtl']).resolve()
 if str(f) not in assembly['source_sha256']:
  excluded.append(service['module']);continue
 h=hashlib.sha256(f.read_bytes()).hexdigest()
 if h!=assembly['source_sha256'][str(f)]:raise ValueError('stale service')
 retained.append(service)
 service['rtl_sha256']=h
 service['structural_admission_receipt']=str(receipt.resolve())
d['services']=retained
print('not present in this base',excluded)
(Path(os.environ['PIPELINE_OUTPUT'])/'services.json').write_text(json.dumps(d,indent=2)+'\n')
print('service hashes',len(d['services']))
PY
