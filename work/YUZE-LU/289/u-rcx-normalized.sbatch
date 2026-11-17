#!/bin/bash
#SBATCH --job-name=yzl-289-rcxnorm
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/u-rcx-normalized-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$root/cu/runs/U-v15-guardant-f67-h3-u1.2
src=$run/flow/results/nangate45/u-overlay-current/base
out=$root/u-physical/rcx-normalized-$SLURM_JOB_ID
mkdir "$out"
cp "$root/u-rcx-ndr-normalize.py" "$root/u-rcx-normalized.tcl" "$out/"
sha256sum "$src/6_final.odb" "$src/6_final.def" > "$out/source.sha256"
python3 "$out/u-rcx-ndr-normalize.py" "$src/6_final.def" "$out/normalized.def"
export PROBE_LEFS=$(sed -n 's/^export ADDITIONAL_LEFS = //p' "$run/config.mk")
pids=()
for mode in odb normal original; do
 for version in 1.0 2.0; do
  work=$out/$mode-$version
  mkdir "$work"
  input=$out/normalized.def
  if [[ $mode == original ]]; then input=$src/6_final.def; fi
  export SINGULARITYENV_PROBE_LEFS="$PROBE_LEFS"
  srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$work" --env OMP_NUM_THREADS=8,PROBE_ODB="$src/6_final.odb",PROBE_DEF="$input",PROBE_IMPORT="$mode",PROBE_RCX_VERSION="$version" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$out/u-rcx-normalized.tcl" > "$work/run.log" 2>&1 &
  pids+=("$!")
 done
done
rc=0
for p in "${pids[@]}"; do wait "$p" || rc=1; done
sha256sum -c "$out/source.sha256"
exit "$rc"
