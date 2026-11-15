#!/bin/bash
set -euo pipefail
p=/public/home/yuzelu/project-circuit
native=$p/issue260-product-retirement-V6JR7Km4/source/project/experiments
exec srun --exact -n1 -c1 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH="$PWD/tlm:$PWD/compiler:$native/block_local_native:$native/native_s32_n:$p/issue260-tlm-request-Xuwu5O" LD_LIBRARY_PATH="$p/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001" \
 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python -B tlm/run_native_package.py \
 "$1" "$p/issue260-tlm-joint-9BiJdfEg/dram-106937.so" \
 "$p/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini" "$native/w8a16_g/reference.py" \
 "evidence/native-execution-$SLURM_JOB_ID" --scene diagnostic-zero --core-ps 1000
