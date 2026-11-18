#!/bin/bash
#SBATCH -J yzl-C-fillk-induct
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 00:20:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-fillk-induct-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit
out=$root/C-A-fillk-induct32
mkdir "$out"
python3 - "$root" "$out" <<'PY'
from pathlib import Path
import sys,json,hashlib
r,o=map(Path,sys.argv[1:]);w=r/'C-v21-shared-A-live-state-generic-views/proof-work';src=w/'strategies/cfj_group_c_memory_legacy.formal_live_state_165/simple/run.ys';s=src.read_text();assert s.count('-maxsteps 5 -timeout 60')==1;s=s.replace('-maxsteps 5 -timeout 60','-maxsteps 32 -timeout 300').replace('../../../partitions/',str(w/'partitions')+'/');(o/'proof.ys').write_text(s);(o/'input-binding.json').write_text(json.dumps({'original_strategy_sha':hashlib.sha256(src.read_bytes()).hexdigest(),'only_changes':'maxsteps5→32, timeout60→300, absolute exact partition paths; no model or assumptions changed'},indent=2))
PY
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; yosys -s proof.ys > proof.log 2>&1'
grep -q 'Induction step proven: SUCCESS' "$out/proof.log"
