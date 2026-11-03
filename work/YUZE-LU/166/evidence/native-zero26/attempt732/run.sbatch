#!/bin/bash
#SBATCH --job-name=yzl-r166-stage732
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=1
#SBATCH --time=0
#SBATCH --mem=0
#SBATCH --exclude=node16,node19,node20,node21,node25,node26
set -euo pipefail
cd "${1}"
sha256sum -c FILES.sha256 > source-check.log
printf '%s  %s\n' 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif | sha256sum -c -
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "${1}" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; exec python3 -c '"'"'from pathlib import Path
import json,hashlib,sys
sys.path.insert(0,'"'"'"'"'"'"'"'"'project/experiments/r_local_state'"'"'"'"'"'"'"'"')
from receive_native import receive
B=Path('"'"'"'"'"'"'"'"'/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state'"'"'"'"'"'"'"'"');S=B/'"'"'"'"'"'"'"'"'attempt718/physical'"'"'"'"'"'"'"'"';R=S/'"'"'"'"'"'"'"'"'flow/results/nangate45/r166_1024/base'"'"'"'"'"'"'"'"';L=S/'"'"'"'"'"'"'"'"'flow/logs/nangate45/r166_1024/base'"'"'"'"'"'"'"'"'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert json.loads((S/'"'"'"'"'"'"'"'"'receipt.json'"'"'"'"'"'"'"'"').read_text())['"'"'"'"'"'"'"'"'exit'"'"'"'"'"'"'"'"']==0
m=json.loads((L/'"'"'"'"'"'"'"'"'6_report.json'"'"'"'"'"'"'"'"').read_text());assert m['"'"'"'"'"'"'"'"'finish__timing__setup__ws'"'"'"'"'"'"'"'"']>=0 and m['"'"'"'"'"'"'"'"'finish__timing__hold__ws'"'"'"'"'"'"'"'"']>=0
assert all(m[k]==0 for k in ['"'"'"'"'"'"'"'"'finish__timing__drv__setup_violation_count'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'finish__timing__drv__hold_violation_count'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'finish__timing__drv__max_cap'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'finish__timing__drv__max_slew'"'"'"'"'"'"'"'"'])
assert sha(S/'"'"'"'"'"'"'"'"'input.sdc'"'"'"'"'"'"'"'"')==sha(Path('"'"'"'"'"'"'"'"'project/experiments/r_local_state/physical.sdc'"'"'"'"'"'"'"'"'))
assert sha(R/'"'"'"'"'"'"'"'"'6_final.odb'"'"'"'"'"'"'"'"')=='"'"'"'"'"'"'"'"'1d848b36183b6fb15fb1cce7b7fe6116119a889030720685133344d039ec2b44'"'"'"'"'"'"'"'"'
for phase in ['"'"'"'"'"'"'"'"'before-detail'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'after-detail'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'final'"'"'"'"'"'"'"'"']:assert json.loads((S/('"'"'"'"'"'"'"'"'CLOCK_AUDIT_'"'"'"'"'"'"'"'"'+phase+'"'"'"'"'"'"'"'"'.json'"'"'"'"'"'"'"'"')).read_text())['"'"'"'"'"'"'"'"'passed'"'"'"'"'"'"'"'"']
proof=receive(B/'"'"'"'"'"'"'"'"'attempt730/native-complete'"'"'"'"'"'"'"'"',R/'"'"'"'"'"'"'"'"'6_final.odb'"'"'"'"'"'"'"'"')
assert proof['"'"'"'"'"'"'"'"'passed'"'"'"'"'"'"'"'"'] and proof['"'"'"'"'"'"'"'"'geometry_identity_rechecked'"'"'"'"'"'"'"'"'] and proof['"'"'"'"'"'"'"'"'negative_controls_received'"'"'"'"'"'"'"'"'] and proof['"'"'"'"'"'"'"'"'native_drc_count'"'"'"'"'"'"'"'"']==0
files=[S/'"'"'"'"'"'"'"'"'receipt.json'"'"'"'"'"'"'"'"',S/'"'"'"'"'"'"'"'"'input.sdc'"'"'"'"'"'"'"'"',L/'"'"'"'"'"'"'"'"'6_report.json'"'"'"'"'"'"'"'"',R/'"'"'"'"'"'"'"'"'6_final.odb'"'"'"'"'"'"'"'"',B/'"'"'"'"'"'"'"'"'attempt730/native-complete/receipt.json'"'"'"'"'"'"'"'"',Path('"'"'"'"'"'"'"'"'project/experiments/r_local_state/receive_native.py'"'"'"'"'"'"'"'"'),Path('"'"'"'"'"'"'"'"'project/experiments/r_local_state/native_interchange.py'"'"'"'"'"'"'"'"')]
Path('"'"'"'"'"'"'"'"'NATIVE_GATE_RECEIPT.json'"'"'"'"'"'"'"'"').write_text(json.dumps(dict(passed=True,native_gate_received=True,qualification=False,physical=str(S),complete_native=str(B/'"'"'"'"'"'"'"'"'attempt730/native-complete'"'"'"'"'"'"'"'"'),proof=proof,inputs={str(f):sha(f)for f in files},scope='"'"'"'"'"'"'"'"'Unmodified original exact-final native gate receiver rechecks all actual complete rules, all controls, original pinned tool/source, whole technology/geometry/connection roundtrip, restored grids and source hashes. 730 ran after successful complete718 production; runtime thread count1 is a resource choice, never a waived rule. This is the full native gate only; original full GDS/independent physical/function/192 cases/local full package still mandatory.'"'"'"'"'"'"'"'"'),indent=2))
print('"'"'"'"'"'"'"'"'UNMODIFIED_NATIVE_GATE_RECEIVER_PASS'"'"'"'"'"'"'"'"')
'"'"''
