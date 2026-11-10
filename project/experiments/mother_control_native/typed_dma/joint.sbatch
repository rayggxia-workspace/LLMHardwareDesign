#!/bin/bash
#SBATCH --job-name=yl-250DmaStage3
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${CONTROL_TYPED_DMA_DIR:?archived job root}"
SIF=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
VERILATOR=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
RUNTIME=/public/software/singularity-ce-4.3.4/bin/singularity
rtl=project/rtl/mother_control_native/mc_dma_fabric_typed_p.sv
tb=project/experiments/mother_control_native/typed_dma/joint.cpp
wrap=project/experiments/mother_control_native/typed_dma/mc_dma_stage64_joint.sv
stage=project/rtl/native_s32_dot/dot_s32_stage64.sv
s=upstream/local_s_base.sv
s_impl=upstream/block_feed_s16k_sram.sv
bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
test "$(sha256sum "$bank" | cut -d' ' -f1)" = 6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7
mkdir -p build results
sha256sum "$rtl" "$tb" "$wrap" "$stage" "$s" "$s_impl" "$bank" > results/source.sha256
srun --exclusive --ntasks=1 --cpus-per-task=10 \
 "$RUNTIME" exec --cleanenv --bind /public/home/yuzelu "$SIF" "$VERILATOR" --cc --exe --build \
 --Wall --assert -j 10 --x-initial unique --x-assign unique --timing --timescale-override 1ns/1ps --top-module mc_dma_stage64_joint \
 --Mdir "$PWD/build" upstream/native_s_lint.vlt "$rtl" "$wrap" "$stage" "$s" "$s_impl" "$bank" "$PWD/$tb" > results/build.log 2>&1
for init in 0 1 2;do
 pids=()
 for seed in 1 2 3 4 5 6;do
  srun --exclusive --ntasks=1 --cpus-per-task=10 \
    "$RUNTIME" exec --cleanenv --bind /public/home/yuzelu "$SIF" "$PWD/build/Vmc_dma_stage64_joint" \
    "$seed" "$init" "$PWD/results/joint-${seed}-${init}.csv" > "results/joint-${seed}-${init}.log" 2>&1 &
  pids+=("$!")
 done
 status=0
 for task in "${pids[@]}";do wait "$task"||status=1;done
 if [ "$status" != 0 ];then exit "$status";fi
done

