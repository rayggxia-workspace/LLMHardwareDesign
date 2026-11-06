#!/usr/bin/env bash
set -euo pipefail
source_run=$1
run=$2
hold_margin=${3:-}
slot=$SLURM_ARRAY_TASK_ID
pair=$((2*(slot/2)))
methods=(cugr guide)
method=${methods[slot%2]}
original="$source_run/$pair"
out="$run/$method/$pair"
mkdir -p "$out"
for f in inventory.json input.sdc cut-links.json; do cp "$original/$f" "$out/$f"; done
sealed=$(find "$original/flow/results" -name 4_cts.odb -printf '%h\n')
[[ -n "$sealed" && -s "$sealed/4_cts.sdc" ]]
relative=${sealed#"$original/"}
result="$out/$relative"
mkdir -p "$result"
for f in "$sealed"/[1234]_*; do
  if [[ -f "$f" ]]; then cp "$f" "$result/"; fi
done
sha256sum "$sealed"/4_cts.{odb,sdc} > "$out/source-cts.sha256"
if [[ "$method" == cugr ]]; then
  args="-use_cugr -verbose"
else
  # Carry congested coarse guides into legal track search. Zero detailed
  # violations, full native GDS DRC and extracted timing are still required.
  args="-congestion_iterations 30 -allow_congestion -verbose"
fi
sed -e '/^export GLOBAL_ROUTE_ARGS = /d' "$original/config.mk" > "$out/config.mk"
if [[ -n "$hold_margin" ]]; then
  [[ "$hold_margin" =~ ^0[.][0-9]+$ ]]
  sed -i '/^export HOLD_SLACK_MARGIN = /d' "$out/config.mk"
  printf 'export HOLD_SLACK_MARGIN = %s\n' "$hold_margin" >> "$out/config.mk"
fi
printf 'export GLOBAL_ROUTE_ARGS = %s\n' "$args" >> "$out/config.mk"
cpus=$SLURM_CPUS_PER_TASK
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
   set -eu
   source /OpenROAD-flow-scripts/env.sh
   for target in do-route do-finish do-gds; do
     make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$1/config.mk" WORK_HOME="$1/flow" NUM_CORES="$2" "$target"
   done
   sha256sum -c "$1/source-cts.sha256"
 ' bash "$out" "$cpus"
