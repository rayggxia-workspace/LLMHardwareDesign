#!/bin/bash
#SBATCH -J yzl-C-snapshot-isolated
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-snapshot-isolated-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/audit/cached-ff-snapshot-isolated
mkdir "$out"
python3 - "$root" "$out" <<'PY'
from pathlib import Path
import sys
r,o=map(Path,sys.argv[1:]);s=(r/'audit/cached-dff-binding/map.ys').read_text();lines=[]
for line in s.splitlines():
 if line.startswith('write_json '):lines+=['design -push-copy',line,'design -pop']
 else:lines.append(line)
(o/'map.ys').write_text('\n'.join(lines)+'\n')
PY
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; yosys -s map.ys > map.log 2>&1'
sha256sum "$out/mapped.v" "$root/cu/loader-fast3-cached/mapped.v"
cmp "$out/mapped.v" "$root/cu/loader-fast3-cached/mapped.v"
