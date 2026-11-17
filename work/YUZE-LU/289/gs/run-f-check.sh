#!/bin/bash
set -euo pipefail
stage=${1:?physical/formal}; candidate=${2:?absolute candidate directory}
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs
case "$candidate" in "$root"/candidate-S-hold08-v3/parent-F-eco-*) ;; *) exit 2;; esac
case "$stage" in
 physical) script=f-qualify.py ;;
 formal) script=f-formal.py ;;
 *) exit 2 ;;
esac
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$candidate" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 "$1/$2" "$3"; if [ "$2" = f-formal.py ]; then python3 "$1/f-state-preservation.py" F "$3"; fi' bash "$root" "$script" "$candidate" > "$candidate/$stage-worker.log" 2>&1
