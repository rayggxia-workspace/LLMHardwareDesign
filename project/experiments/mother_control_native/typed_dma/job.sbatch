#!/bin/bash
#SBATCH --job-name=yl-250TypedDMA
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
tb=project/experiments/mother_control_native/typed_dma/typed.cpp
mkdir -p build results
sha256sum "$rtl" "$tb" > results/source.sha256
srun --exclusive --ntasks=1 --cpus-per-task=10 \
 "$RUNTIME" exec --cleanenv --bind /public/home/yuzelu "$SIF" "$VERILATOR" --cc --exe --build \
 --Wall --assert -j 10 --x-initial unique --x-assign unique --top-module mc_dma_fabric_typed_p \
 --Mdir "$PWD/build" "$rtl" "$PWD/$tb" > results/build.log 2>&1
for init in 0 1 2;do
 pids=()
 for seed in 1 2 3 4 5 6;do
  srun --exclusive --ntasks=1 --cpus-per-task=10 \
    "$RUNTIME" exec --cleanenv --bind /public/home/yuzelu "$SIF" "$PWD/build/Vmc_dma_fabric_typed_p" \
    "$seed" "$init" "$PWD/results/typed-${seed}-${init}.csv" > "results/typed-${seed}-${init}.log" 2>&1 &
  pids+=("$!")
 done
 status=0
 for task in "${pids[@]}";do wait "$task"||status=1;done
 if [ "$status" != 0 ];then exit "$status";fi
done

