#!/bin/bash
#SBATCH -J yzl-C-fillk-proof
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 01:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-fillk-proof-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit
out=$root/C-A-fillk-retry
mkdir "$out"
python3 - "$root" "$out" <<'PY'
from pathlib import Path
import sys,json,hashlib
r,o=map(Path,sys.argv[1:]);w=r/'C-v21-shared-A-live-state-generic-views/proof-work';source=w/'strategies/cfj_group_c_memory_legacy.formal_live_state_165/pdr/cfj_group_c_memory_legacy.formal_live_state_165.sby';s=source.read_text();assert s.count('timeout 90')==1;s=s.replace('timeout 90','timeout 1800').replace('../../../../../partitions/',str(w/'partitions')+'/');(o/'proof.sby').write_text(s)
files=[source,w/'partitions/cfj_group_c_memory_legacy.formal_live_state_165.sv',w/'partitions/cfj_group_c_memory_legacy.formal_live_state_165.il'];(o/'input-binding.json').write_text(json.dumps({'only_change':'timeout90→1800 and absolute paths to exact same partition sources; no assumption/model/engine change','hashes':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}},indent=2))
PY
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; export PATH=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/eqy-install-v068/bin:$PATH; sby -d proof-work proof.sby'
