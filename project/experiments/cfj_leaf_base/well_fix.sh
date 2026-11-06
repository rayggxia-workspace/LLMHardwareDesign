#!/usr/bin/env bash
set -euo pipefail
original=$1
run=$2
runner=$3
pair=$4
slot=$SLURM_ARRAY_TASK_ID
sites=$((1+2*slot))
out="$run/sites$sites/$pair"
mkdir -p "$out"
cp "$original/"{inventory.json,input.sdc,cut-links.json,config.mk} "$out/"
sealed=$(find "$original/flow/results" -name 6_final.odb -printf '%h\n')
relative=${sealed#"$original/"}
result="$out/$relative"
mkdir -p "$result"
cp "$sealed/5_route.sdc" "$result/"
sha256sum "$sealed"/{5_route.odb,6_final.gds,6_final.v} > "$out/source.sha256"
export SINGULARITYENV_CFJ_WELL_SOURCE="$sealed/5_route.odb"
export SINGULARITYENV_CFJ_WELL_TARGET="$result/5_route.odb"
export SINGULARITYENV_CFJ_WELL_EDITS="$run/taps-$pair.tsv"
export SINGULARITYENV_CFJ_WELL_SITES="$sites"
cpus=$SLURM_CPUS_PER_TASK
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
   set -eu
   source /OpenROAD-flow-scripts/env.sh
   openroad -no_init -exit "$1/well_fix.tcl"
   for target in do-finish do-gds; do
     make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$2/config.mk" WORK_HOME="$2/flow" NUM_CORES="$3" "$target"
   done
   sha256sum -c "$2/source.sha256"
   cmp "$4/6_final.v" "$5/6_final.v"
   klayout -b -r "$1/well_probe.drc" -rd "in_gds=$5/6_final.gds" -rd "report_file=$2/well-probe.lyrdb"
   python3 -c "import sys,xml.etree.ElementTree as ET; n=len(ET.parse(sys.argv[1]).findall(\".//items/item\")); print(n); sys.exit(n!=0)" "$2/well-probe.lyrdb"
 ' bash "$runner" "$out" "$cpus" "$sealed" "$result"
