#!/usr/bin/env bash
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
sha256sum -c source.sha256
p=/public/home/yuzelu/project-circuit
asset=$p/issue234-native-fixed-skip-request-H2gY5uiN
srun --exact -n1 -c1 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH="$p/issue260-tlm-joint-9BiJdfEg/systemc_benchmark:$p/issue260-tlm-joint-9BiJdfEg/block_local_native" LD_LIBRARY_PATH="$p/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001" \
 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python run_native_tlm_request.py \
 "$asset/request-runtime-archived" "$asset/request-memory-archived/ddr-initial.tsv" "$p/issue260-tlm-joint-9BiJdfEg/dram-106937.so" \
 "$p/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini" "run-$SLURM_JOB_ID" \
 74078b0b40fdeb73aeae71e3091db3e6a25fc5f27bc03c9981214bfef92b39ef \
 --prefill-tokens 2 --pipeline-memory "${@:2}" --dma-fabric-budget --kv-read-window 8 --sram-port-bits 512

python3 audit_prefill.py run-$SLURM_JOB_ID 2 > run-$SLURM_JOB_ID/timing-audit.json
