#!/bin/bash
#SBATCH --job-name=yzl-289-ndrprobe
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/u-ndr-pg-probe-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/u-physical/ndr-pg-probe-$SLURM_JOB_ID
mkdir "$out"
cp "$root/u-ndr-pg-probe.tcl" "$out/"
pids=()
for mode in base create assign rip final finalstrip; do
 source=$root/audit/U-antenna/candidate-guard-ant-v1/flow/results/nangate45/u-overlay-current/base/6_final.odb
 if [[ "$mode" == final* ]]; then source=$root/cu/runs/U-v15-guardant-f67-h3-u1.2/flow/results/nangate45/u-overlay-current/base/6_final.odb; fi
 sha256sum "$source" >> "$out/source-sha256.txt"
 srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8,PROBE_SOURCE="$source",PROBE_MODE="$mode" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$out/u-ndr-pg-probe.tcl" > "$out/$mode.log" 2>&1 &
 pids+=("$!")
done
rc=0
for p in "${pids[@]}"; do wait "$p" || rc=1; done
exit "$rc"
