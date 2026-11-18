#!/bin/bash
#SBATCH --job-name=yzl-C-receiver-six
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-receiver-six-%j.log
set -uo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
python3 "$root/audit/c-receiver-probe-prepare.py" || exit 1
libs=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$root/cu/runs/C-v27-joint-e20-h30/config.mk" | tail -1)
pids=()
for size in 1 2 4; do
 for tag in short larger; do
  out="$root/audit/C-receiver-probe-v1/b${size}-${tag}"
  srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "CU_LIBS=$libs,PROBE_SIZE=$size" --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/audit/c-receiver-probe.tcl" > "$out/job.log" 2>&1 &
  pids+=("$!")
 done
done
rc=0
for p in "${pids[@]}"; do wait "$p" || rc=1; done
exit "$rc"
