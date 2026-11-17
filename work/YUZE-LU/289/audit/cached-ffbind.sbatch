#!/bin/bash
#SBATCH -J yzl-cache-ffbind
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/cache-ffbind-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/audit/cached-dff-binding
mkdir "$out"
python3 - "$root/cu/loader-fast3-cached/map.ys" "$out/map.ys" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text().splitlines();o=[]
for line in s:
 if line.startswith('dfflibmap '):o+=['write_json before-dff.json',line,'write_json after-dff.json']
 else:o.append(line)
Path(sys.argv[2]).write_text('\n'.join(o)+'\n')
PY
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; yosys -s map.ys > map.log 2>&1; cmp mapped.v "$1/cu/loader-fast3-cached/mapped.v"; sha256sum mapped.v "$1/cu/loader-fast3-cached/mapped.v" > actual-binding.sha256' _ "$root"
