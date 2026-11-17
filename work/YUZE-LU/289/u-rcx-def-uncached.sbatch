#!/bin/bash
#SBATCH --job-name=yzl-289-rcxdef
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/u-rcx-def-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$root/cu/runs/U-v15-guardant-f67-h3-u1.2
out=$root/u-physical/rcx-def-uncached-$SLURM_JOB_ID
mkdir "$out"
cp "$root/u-rcx-normalized.tcl" "$out/"
export SINGULARITYENV_PROBE_LEFS=$(sed -n 's/^export ADDITIONAL_LEFS = //p' "$run/config.mk")
test -n "$SINGULARITYENV_PROBE_LEFS"
pids=()
for mode in normal original; do
 work=$out/$mode
 mkdir "$work"
 input=$root/u-physical/rcx-normalized-119778/normalized.def
 if [[ $mode == original ]]; then input=$run/flow/results/nangate45/u-overlay-current/base/6_final.def; fi
 if [[ $mode == normal && $# -ge 1 ]]; then input=$1; fi
 if [[ $mode == original && $# -ge 2 ]]; then input=$2; fi
 sha256sum "$input" > "$work/source.sha256"
 srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$work" --env PROBE_UNCACHED=1,PROBE_IMPORT="$mode",PROBE_DEF="$input",PROBE_RCX_VERSION=1.0 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$out/u-rcx-normalized.tcl" > "$work/run.log" 2>&1 &
 pids+=("$!")
done
rc=0
for p in "${pids[@]}"; do wait "$p" || rc=1; done
exit "$rc"
