#!/usr/bin/env bash
set -euo pipefail
source_run=$1
run=$2
hold_margin=${3:-}
slew_margin=${4:-}
native_edge_guard=${5:-}
prefab_repair=${6:-}
slot=$SLURM_ARRAY_TASK_ID
pair=$((2*(slot/2)))
methods=(cugr guide)
method=${methods[slot%2]}
original="$source_run/$pair"
out="$run/$method/$pair"
mkdir -p "$out"
for f in inventory.json input.sdc cut-links.json; do cp "$original/$f" "$out/$f"; done
if [[ -s "$original/control64-source.json" ]]; then
  cp "$original/control64-source.json" "$out/control64-source.json"
fi
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
if [[ -n "$slew_margin" ]]; then
  [[ "$slew_margin" =~ ^[0-9]+$ ]]
  sed -i '/^export SLEW_MARGIN = /d' "$out/config.mk"
  printf 'export SLEW_MARGIN = %s\n' "$slew_margin" >> "$out/config.mk"
fi
printf 'export GLOBAL_ROUTE_ARGS = %s\n' "$args" >> "$out/config.mk"
if [[ -n "$native_edge_guard" || -n "$prefab_repair" ]]; then
  printf 'source {%s/route-capacity.tcl}\n' "$original" > "$out/pre-global-route.tcl"
  if [[ -n "$native_edge_guard" ]]; then
    [[ -s "$native_edge_guard" ]]
    cp "$native_edge_guard" "$out/native-edge-guard.tcl"
    printf 'source {%s/native-edge-guard.tcl}\n' "$out" >> "$out/pre-global-route.tcl"
  fi
  if [[ -n "$prefab_repair" ]]; then
    [[ -s "$prefab_repair" ]]
    cp "$prefab_repair" "$out/prefab-repair.tcl"
    printf 'source {%s/prefab-repair.tcl}\n' "$out" >> "$out/pre-global-route.tcl"
  fi
  sed -i '/^export PRE_GLOBAL_ROUTE_TCL = /d' "$out/config.mk"
  printf 'export PRE_GLOBAL_ROUTE_TCL = %s/pre-global-route.tcl\n' "$out" >> "$out/config.mk"
fi
cpus=$SLURM_CPUS_PER_TASK
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
   set -eu
   source /OpenROAD-flow-scripts/env.sh
   extra=()
   if [[ -s "$1/control64-source.json" ]]; then
     extra+=("DONT_USE_CELLS=TAPCELL_X1 FILLCELL_X1 AOI211_X1 OAI211_X1 OAI221_X4")
   fi
   for target in do-route do-finish do-gds; do
     make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$1/config.mk" WORK_HOME="$1/flow" NUM_CORES="$2" "${extra[@]}" "$target"
   done
   sha256sum -c "$1/source-cts.sha256"
 ' bash "$out" "$cpus"
