#!/bin/bash
#SBATCH -J yzl-C-A-stageproof
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-A-stageproof-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/audit/C-A-loader-stageproof
mkdir "$out"
python3 - "$root" "$out" <<'PY'
from pathlib import Path
import sys
r,o=map(Path,sys.argv[1:]);s=(r/'audit/C-cached-shared-diagnostic-v2/A-map/map.ys').read_text();lines=[]
for line in s.splitlines():
 if line.startswith('dfflibmap '):lines+=['design -push-copy','write_json before-dff.json','design -pop',line,'design -push-copy','write_json after-dff.json','design -pop']
 elif line.startswith('abc '):lines.append(line.replace('abc ','abc -nocleanup -showtmp ',1))
 else:lines.append(line)
(o/'map.ys').write_text('\n'.join(lines)+'\n')
PY
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -e; source /OpenROAD-flow-scripts/env.sh; yosys -s map.ys > map.log 2>&1; cmp mapped.v "$1/audit/C-cached-shared-diagnostic-v2/A-map/mapped.v"; python3 "$1/audit/verify_loader_dffmap_init.py" "$2"; python3 "$1/audit/run_cached_cec.py" "$2"' _ "$root" "$out"
