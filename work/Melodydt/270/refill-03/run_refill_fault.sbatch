#!/bin/bash
#SBATCH --job-name=zny-att1-wfault
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:06:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
run=$PWD/fault-$SLURM_JOB_ID
mkdir "$run"
export ATT1_FAULT_RUN=$run
srun --exact -n1 -c2 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "ATT1_FAULT_RUN=$run" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -s <<'CHECK'
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
"$v" --version
sha256sum test_refill_fault.sv source/project/rtl/block_local_native/s128_ddr_response_load.sv > "$ATT1_FAULT_RUN/inputs.sha256"
"$v" --binary --timing --assert -Wall -j 2 --top-module test_refill_fault --Mdir "$ATT1_FAULT_RUN/obj" test_refill_fault.sv source/project/rtl/block_local_native/s128_ddr_response_load.sv > "$ATT1_FAULT_RUN/build.log" 2>&1
for mode in 0 1 2; do
    "$ATT1_FAULT_RUN/obj/Vtest_refill_fault" "+MODE=$mode" | tee "$ATT1_FAULT_RUN/mode-$mode.log"
done
cd "$ATT1_FAULT_RUN"
sha256sum inputs.sha256 mode-*.log > output.sha256
sha256sum -c output.sha256
CHECK

