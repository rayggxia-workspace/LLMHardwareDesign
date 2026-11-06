#!/usr/bin/env bash
set -euo pipefail
bundle=$1
out=$2
top=$3
mkdir -p "$out"
cd "$out"
bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
native="$bundle/staged/native"
design="$bundle/design"
sha256sum "$native"/*.sv "$design"/*.sv > sources.sha256
runtime=(srun --exact --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores
 /public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator \
 --binary --timing --assert --timescale-override 1ns/1ns -Wno-fatal --top-module "$top" \
 -j "$SLURM_CPUS_PER_TASK" --Mdir "$PWD/obj" -I"$native" "$native/native_r.vlt" \
 "$native"/*.sv "$design"/"$top".sv "$design"/{block_cfj_cf,block_cfj_j,cfj_s_port,cfj_e_port}.sv \
 "$bundle/staged/pj/project/rtl/block_pj_v1"/{pj_sram_client,pj_mem_port}.sv \
 "$bundle/staged/pj/project/rtl/block_v1/transaction6k.sv" "$bank" > compile.log 2>&1
"${runtime[@]}" "./obj/V$top"
