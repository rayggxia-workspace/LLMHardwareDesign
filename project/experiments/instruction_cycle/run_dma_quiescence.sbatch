#!/usr/bin/env bash
#SBATCH --job-name=zny-dmaqui
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.out
set -euo pipefail

root=$PWD
sha256sum -c - <<'PINS'
a4d99306602159de041d0f52402d95452cfdb53825bf51b16a4e106ac6382e0c  mc_dma_fabric_typed_p.sv
97703ef2b1fda30e9e4e2c9178990d3fb9681babd404027d3342ce5a4096304b  tb_transport_quiescent.sv
PINS
sha256sum mc_dma_fabric_typed_p.sv tb_transport_quiescent.sv run_dma_quiescence.sbatch > source.sha256
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
verilator=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
sha256sum "$image" "$verilator" > tools.sha256
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu "$image" bash -s -- "$root" "$verilator" "$SLURM_CPUS_PER_TASK" <<'RUN'
set -euo pipefail
cd "$1"
"$2" --version > verilator-version.txt
"$2" --binary --timing --assert -Wno-fatal --top-module tb_transport_quiescent \
    -j "$3" --Mdir "$PWD/obj" mc_dma_fabric_typed_p.sv tb_transport_quiescent.sv > build.log 2>&1
./obj/Vtb_transport_quiescent > quiescence.log 2>&1
grep -Fx 'PASS typed DMA transport_quiescent' quiescence.log
sha256sum quiescence.log verilator-version.txt build.log tools.sha256 source.sha256 > output.sha256
RUN
