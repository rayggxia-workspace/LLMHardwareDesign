#!/usr/bin/env bash
set -euo pipefail
cd "$1"
graph="$2"
input="$3"
root=/public/home/yuzelu/project-circuit
code="$root/issue260-native-sram512-full-zrXP7jjS"
joint="$root/issue260-tlm-joint-9BiJdfEg"
(cd "$code" && sha256sum -c --quiet source.sha256)
srun --exact -n1 -c1 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 \
 PYTHONPATH="$PWD:$code:$joint/systemc_benchmark" \
 LD_LIBRARY_PATH="$root/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001" \
 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python -B verify_indexed_dma.py \
 "$graph/r4/rows/row-0/embedding" "$input" "$graph/request-memory-r2/ddr-initial.tsv" \
 "$root/issue234-native-rope-ddr-assets-20261112-01/run-103592/layout.json" "$joint/dram-106937.so" \
 "$root/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini" "format-$SLURM_JOB_ID"
sha256sum indexed_dma_records.py verify_indexed_dma.py "format-$SLURM_JOB_ID/report.json" > "format-$SLURM_JOB_ID.sha256"
