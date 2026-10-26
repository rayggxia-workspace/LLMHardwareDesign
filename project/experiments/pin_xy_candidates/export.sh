#!/bin/bash
#SBATCH --job-name=hpy-pinxy
#SBATCH --partition=c64
#SBATCH --cpus-per-task=1
#SBATCH --time=00:20:00
set -euo pipefail
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
cd /public/home/yuzelu/PingyangHuang/pin-xy-candidates-20261026
export TMPDIR=$PWD/tmp SINGULARITY_CACHEDIR=$PWD/cache SINGULARITY_TMPDIR=$PWD/tmp
for c in act gemm; do
 if [ "$c" = act ]; then d=parallel_opentpu_act; else d=parallel_llaccel_gemm; fi
 src=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06/$c-cap20/flow/results/nangate45/$d/base/6_final.odb
 stat "$src" > data/$c-source-stat-before.txt
 sha256sum "$src" > data/$c-source.sha256
 singularity exec --cleanenv --env PINXY_CASE=$c,PINXY_ODB=$src,PYTHONDONTWRITEBYTECODE=1,OMP_NUM_THREADS=1 --bind /public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro --home $PWD/home --pwd $PWD /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -threads 1 -no_init -exit export_odb.tcl > data/$c-export.log 2>&1
 stat "$src" > data/$c-source-stat-after.txt
 gzip -n data/$c/*.tsv
 done
printf 'READ_ONLY_EXPORT_COMPLETE\n'
