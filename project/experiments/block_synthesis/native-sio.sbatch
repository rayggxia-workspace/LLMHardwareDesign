#!/bin/bash
#SBATCH --job-name=yzl-syn-sio
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
source=$(realpath "$2")/source
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-*) ;; *) exit 2;; esac
cd "$root"
bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
files=(native_s_io.sv "$source/project/rtl/s_sram/local_s_base.sv" "$source/project/rtl/s_sram/local_s_p.sv"
 "$source/project/rtl/s_sram/block_feed_s16k_sram.sv" "$source/project/rtl/block_feed_v1/block_feed_loader.sv" "$bank")
sha256sum "${files[@]}" > input.sha256
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
"${sim[@]}" /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --binary --timing --assert -j "$SLURM_CPUS_PER_TASK" \
 --top-module native_s_io --Mdir "$root/obj" "${files[@]}" > build.log 2>&1
for initial in 0 1 2; do
 "${sim[@]}" "$root/obj/Vnative_s_io" +verilator+rand+reset+$initial > native-$initial.log 2>&1
 grep -q NATIVE_S_IO_PASS native-$initial.log
done
sha256sum native-*.log > output.sha256
