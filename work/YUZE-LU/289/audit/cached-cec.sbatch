#!/bin/bash
#SBATCH -J yzl-cache-cec
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/cache-cec-%j.log
set -euo pipefail
base=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$base/audit/cached-abc-cec
mkdir "$out"
sed 's/^abc /abc -nocleanup /' "$base/cu/loader-fast3-cached/map.ys" > "$out/map.ys"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; yosys -s map.ys > map.log 2>&1; sha256sum mapped.v "$1/cu/loader-fast3-cached/mapped.v" > mapped-hashes.txt; cmp mapped.v "$1/cu/loader-fast3-cached/mapped.v"; python3 "$1/audit/run_cached_cec.py" "$2"' _ "$base" "$out"
