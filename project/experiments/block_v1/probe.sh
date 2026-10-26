#!/usr/bin/env bash
set -euo pipefail
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
date -u +%FT%TZ
hostname
scontrol show job -o "$SLURM_JOB_ID"
cat /proc/meminfo | head -n 5
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
sha256sum "$image"
singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" "$image" bash -c '
set -eu
source /OpenROAD-flow-scripts/env.sh
python3 --version
for tool in openroad yosys verilator iverilog klayout; do
  if command -v "$tool"; then
    sha256sum "$(command -v "$tool")"
    case "$tool" in
      openroad) openroad -version ;;
      yosys) yosys -V ;;
      verilator) verilator --version ;;
      iverilog) iverilog -V 2>&1 | head -n 3 ;;
      klayout) klayout -v ;;
    esac
  else printf "NOT_IN_PATH %s\n" "$tool"; fi
done
base=/OpenROAD-flow-scripts/flow/platforms/nangate45
mkdir platform
for relative in lef/NangateOpenCellLibrary.tech.lef config.mk make_tracks.tcl setRC.tcl rcx_patterns.rules lib/NangateOpenCellLibrary_typical.lib; do
  sha256sum "$base/$relative"
  mkdir -p "platform/$(dirname "$relative")"
  cp "$base/$relative" "platform/$relative"
done
printf "NATIVE_LAYERS\n"
grep -E "^LAYER |LayerCount|MAX_ROUTING_LAYER" "$base/lef/NangateOpenCellLibrary.tech.lef" "$base/rcx_patterns.rules" "$base/config.mk"
printf "HOST_VERILATOR\n"
for path in /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator /public/home/yuzelu/opt/eda/verilator-5-042-repro01/bin/verilator; do
  if test -f "$path"; then "$path" --version; fi
done
'
