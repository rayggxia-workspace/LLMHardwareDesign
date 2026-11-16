#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$PWD}"
if [[ ${1:-} != inner ]]; then
exec srun --exact -n1 -c1 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$SLURM_SUBMIT_DIR/rtl.sbatch" inner "$SLURM_JOB_ID"
fi
export PATH=/public/home/yuzelu/opt/eda/verilator-5.042/bin:$PATH
verilator --binary --timing --assert -j 1 --top-module test_s128_ddr_range_load_pipeline --Mdir "obj-$2" s128_ddr_range_load.sv test_s128_ddr_range_load_pipeline.sv
"obj-$2/Vtest_s128_ddr_range_load_pipeline"
