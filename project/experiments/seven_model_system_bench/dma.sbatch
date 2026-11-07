#!/bin/bash
#SBATCH --job-name=hpy-seven-dma
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c dma-upload.sha256
mkdir source-dma dma-results dma-tmp
tar -xf dma-source.tar -C source-dma
rtl="$root/source-dma/project/rtl"
fixture="$root/source-dma/project/experiments/hbm_feed"
out="$root/dma-results"
export SINGULARITYENV_TMPDIR="$root/dma-tmp"
export SINGULARITYENV_XDG_CACHE_HOME="$root/dma-tmp"
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv
     --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
verilator=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
sources=("$rtl"/hbm_feed/*.sv "$rtl"/block_feed_v1/block_feed_s16k.sv
         "$rtl"/block_feed_v1/block_feed_loader.sv "$rtl"/block_feed_v1/block_feed_s_macro.sv "$rtl"/block_v2/block_v2_m.sv
         "$fixture"/hbm_s_pool.sv "$fixture"/hbm_dma_system.sv)
"${sim[@]}" "$verilator" --version >"$out/version.txt"
"${sim[@]}" "$verilator" --cc --exe --build -j "$SLURM_CPUS_PER_TASK" --assert \
    --x-initial unique --x-assign unique --top-module hbm_dma_system \
    --Mdir "$out/obj" -CFLAGS '-std=c++17 -O1 -Wall -Wextra -Werror' \
    "${sources[@]}" "$fixture/test_dma.cpp" >"$out/build.log" 2>&1
binary="$out/obj/Vhbm_dma_system"
for spec in '5 1' '6 0' '6 1' '10 3' '15 2'; do
    read -r period phase <<<"$spec"
    "${sim[@]}" "$binary" +verilator+rand+reset+2 +verilator+seed+181 \
        "--period=$period" "--phase=$phase" >"$out/clock-$period-$phase.json"
done
for credits in 1 2 4 8; do
    "${sim[@]}" "$binary" +verilator+rand+reset+2 +verilator+seed+181 \
        --groups=4 --per=2 --channels=4 --queue=32 "--credits=$credits" >"$out/credit-$credits.json"
done
(cd "$out"; sha256sum -- *.json version.txt obj/Vhbm_dma_system >results.sha256)
