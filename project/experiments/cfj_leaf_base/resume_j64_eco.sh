#!/usr/bin/env bash
set -euo pipefail
root=$1
source_run="$root/physical04/cugr/4"
out="$root/${2:-physical06}/cugr/4"
eco_source=${3:-"$root/compact64_j_hold_eco.tcl"}
repair_reference=${4:-}
mkdir -p "$out"
for f in inventory.json input.sdc cut-links.json control64-source.json; do
  cp "$source_run/$f" "$out/$f"
done
sealed=$(find "$source_run/flow/results" -name 5_1_grt.odb -printf '%h\n')
[[ -s "$sealed/5_1_grt.sdc" ]]
result="$out/${sealed#"$source_run/"}"
mkdir -p "$result"
for f in "$sealed"/[1234]_*; do
  if [[ -f "$f" ]]; then cp "$f" "$result/"; fi
done
# Explicitly restart routing with the repaired post-GRT state as its input;
# the provenance receipt records the real source, rather than calling it CTS.
cp "$sealed/5_1_grt.odb" "$result/4_cts.odb"
cp "$sealed/5_1_grt.sdc" "$result/4_cts.sdc"
sha256sum "$sealed"/5_1_grt.{odb,sdc} > "$out/source-cts.sha256"
printf '{"source_stage":"physical04 post-global-route", "source":"%s", "eco_source":"%s"}\n' "$sealed" "$eco_source" > "$out/eco-origin.json"
cp "$eco_source" "$out/hold-eco.tcl"
if [[ "$eco_source" == *compact64_j_rx_hold_eco.tcl ]]; then
  cp "$root/rx-hold-targets.tsv" "$out/"
fi
# Diodes and routing obstructions are already present in the source database.
# Reapply only router capacity settings, without duplicating physical objects.
printf 'set_global_routing_layer_adjustment metal2-metal6 0.20\nset_global_routing_layer_adjustment metal7-metal10 0.0\nsource {%s/hold-eco.tcl}\n' "$out" > "$out/pre-global-route.tcl"
sed '/^export PRE_GLOBAL_ROUTE_TCL = /d' "$source_run/config.mk" > "$out/config.mk"
printf 'export PRE_GLOBAL_ROUTE_TCL = %s/pre-global-route.tcl\nexport SKIP_INCREMENTAL_REPAIR = 1\nexport RECOVER_POWER = 0\n' "$out" >> "$out/config.mk"
if [[ -n "$repair_reference" ]]; then
  [[ -s "$repair_reference" ]]
  cp "$repair_reference" "$out/repair-reference.spef"
  sha256sum "$repair_reference" > "$out/repair-reference.sha256"
  cp "$root/compact64_j_post_grt_repair.tcl" "$out/"
  printf 'set cfj_repair_reference {%s/repair-reference.spef}\nsource {%s/compact64_j_post_grt_repair.tcl}\n' "$out" "$out" > "$out/post-global-route.tcl"
  printf 'export POST_GLOBAL_ROUTE_TCL = %s/post-global-route.tcl\n' "$out" >> "$out/config.mk"
fi
exec srun --exact --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
   set -eu
   source /OpenROAD-flow-scripts/env.sh
   for target in do-route do-finish do-gds; do
     make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$1/config.mk" WORK_HOME="$1/flow" NUM_CORES="$2" \
       "DONT_USE_CELLS=TAPCELL_X1 FILLCELL_X1 AOI211_X1 OAI211_X1 OAI221_X4" "$target"
   done
   sha256sum -c "$1/source-cts.sha256"
 ' bash "$out" "$SLURM_CPUS_PER_TASK"
