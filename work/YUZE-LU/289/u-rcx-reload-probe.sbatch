#!/bin/bash
#SBATCH --job-name=yzl-289-rcxprobe
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/u-rcx-reload-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/u-physical/rcx-reload-$SLURM_JOB_ID
mkdir "$out"
cp "$root/u-rcx-reload-probe.tcl" "$out/"
cd "$out"
pids=()
for fraction in f50-h2 f67-h3; do
 for spacing in 1.0 1.2 1.4; do
  name=U-v15-guardant-$fraction-u$spacing
  src=$root/cu/runs/$name/flow/results/nangate45/u-overlay-current/base
  mkdir "$name"
  (
   cd "$name"
   sha256sum "$src/6_final.odb" "$src/6_final.def" > source.sha256
   srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" --env OMP_NUM_THREADS=8,PROBE_ODB="$src/6_final.odb" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$out/u-rcx-reload-probe.tcl" > isolated.log 2>&1
   cmp before.def after.def
   sha256sum isolated.spef before.def after.def > isolated.sha256
   if [[ -s "$src/6_final.spef" ]]; then
    # Ignore only SPEF metadata date, never parasitic record or value changes.
    diff -q <(rg -v '^\*DATE ' isolated.spef) <(rg -v '^\*DATE ' "$src/6_final.spef") > compare-spef.log || true
   fi
   sha256sum -c source.sha256
  ) &
  pids+=("$!")
 done
done
rc=0
for p in "${pids[@]}"; do wait "$p" || rc=1; done
exit "$rc"
