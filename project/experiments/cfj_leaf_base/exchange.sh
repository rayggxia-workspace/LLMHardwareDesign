#!/usr/bin/env bash
set -euo pipefail
src=$1
root=$2
out=$3
mkdir -p "$out"
python3.12 "$src/project/experiments/cfj_leaf_base/stage_regression.py" \
 "$root/issue-193-local-control/acceptance-02/bundle.tar.gz" "$out/bundle" controller
cp "$src/project/experiments/cfj_leaf_base/tb_cfj_exchange.sv" "$out/bundle/design/"
if [[ -n ${4:-} ]]; then
 cp "$4" "$out/bundle/design/block_cfj_cf.sv"
fi
cd "$out"
exec srun --exact --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
  set -eu
  source /OpenROAD-flow-scripts/env.sh
  base="$1/bundle"
  bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
  echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
  sha256sum "$base"/design/*.sv "$base"/staged/native/*.sv "$bank" > source-sha256.txt
  /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --binary --timing --assert \
   --timescale-override 1ns/1ns -Wno-fatal --top-module tb_cfj_exchange \
   -j "$2" --Mdir "$1/obj" -I"$base/staged/native" \
   "$base/staged/native/native_r.vlt" "$base/design/"*.sv \
   "$base/staged/native/"*.sv "$bank" \
   "$base/staged/pj/project/rtl/block_pj_v1/"*.sv \
   "$base/staged/pj/project/rtl/block_v2/block_v2_m.sv" \
   "$base/staged/pj/project/rtl/block_v1/transaction6k.sv" > compile.log 2>&1
  ./obj/Vtb_cfj_exchange > simulation.log 2>&1
  cat simulation.log
 ' bash "$out" "$SLURM_CPUS_PER_TASK"
