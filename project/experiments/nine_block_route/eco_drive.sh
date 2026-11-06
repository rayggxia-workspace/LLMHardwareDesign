#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base="$PWD"
i="${SLURM_ARRAY_TASK_ID:?}"
kind=(P C U P C U)
strength=(32 32 32 16 16 16)
k=${kind[$i]}
s=${strength[$i]}
lib="/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib"
if [[ $k == P ]]; then
  pj="$(realpath ../../issue-187-p16-j16)"
  d="$pj/139-p-final-gates/final/P/flow/results/nangate45/block_p16/base"
  lib="$lib $pj/005-leaf-views/views/p4/leaf.lib $pj/005-leaf-views/views/M/leaf.lib $pj/005-leaf-views/views/G/leaf.lib"
else
  d="$(realpath "../../issue-188-ucf16/accepted-ucf16-01/${k}16")"
  lib="$lib $d/s_sram_256x128_freepdk45_TT_1p1V_25C.lib"
fi
out="eco-$SLURM_ARRAY_JOB_ID-$i"
mkdir "$out"
cd "$out"
export ECO_ODB="$d/6_final.odb" ECO_SDC="$d/6_final.sdc" ECO_LIBS="$lib" ECO_STRENGTH="$s" ECO_PORTS="$base/$k-load.tsv"
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu)
"${runtime[@]}" --env "ECO_ODB=$ECO_ODB,ECO_SDC=$ECO_SDC,ECO_LIBS=$ECO_LIBS,ECO_STRENGTH=$ECO_STRENGTH,ECO_PORTS=$ECO_PORTS,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; exec openroad -no_init -exit "$1"' _ "$base/eco_drive.tcl"
