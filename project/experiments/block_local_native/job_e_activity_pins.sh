#!/usr/bin/env bash
#SBATCH --job-name=yzl-e-vcdpin
#SBATCH --partition=c96
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=12
#SBATCH --nodes=1
#SBATCH --time=00:09:00
set -euo pipefail
r="$SLURM_SUBMIT_DIR"
src=/public/home/yuzelu/project-circuit/issue250-ephys-20261111-06/energy
scontrol show job "$SLURM_JOB_ID" > "$r/allocation.txt"
(cd "$src"; sha256sum active-tt300.vcd idle-tt300.vcd active-power.tcl idle-power.tcl) > "$r/input.sha256"
(cd "$r"; sha256sum e_activity_pin_replay.py job.sh) > "$r/source.sha256"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
echo "49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image" | sha256sum -c
srun --exact -n1 -c12 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu "$image" bash -c '
 set -euo pipefail
 source /OpenROAD-flow-scripts/env.sh
 python3 "$1/e_activity_pin_replay.py" --input "$2" --output "$1"
 for n in active idle active-clock-only; do
   openroad -no_init -exit "$1/$n-pins.tcl" > "$1/$n-pins.log" 2>&1
 done
' bash "$r" "$src"
