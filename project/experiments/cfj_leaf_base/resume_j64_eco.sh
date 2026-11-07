#!/usr/bin/env bash
set -euo pipefail
root=$1
source_run="$root/physical04/cugr/4"
out="$root/physical06/cugr/4"
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
printf '{"source_stage":"physical04 post-global-route", "source":"%s", "eco":"two BUF_X1 on rx data bit 65"}\n' "$sealed" > "$out/eco-origin.json"
cp "$root/compact64_j_hold_eco.tcl" "$out/hold-eco.tcl"
printf 'source {%s/pre-global-route.tcl}\nsource {%s/hold-eco.tcl}\n' "$source_run" "$out" > "$out/pre-global-route.tcl"
sed '/^export PRE_GLOBAL_ROUTE_TCL = /d' "$source_run/config.mk" > "$out/config.mk"
printf 'export PRE_GLOBAL_ROUTE_TCL = %s/pre-global-route.tcl\nexport SKIP_INCREMENTAL_REPAIR = 1\nexport RECOVER_POWER = 0\n' "$out" >> "$out/config.mk"
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
