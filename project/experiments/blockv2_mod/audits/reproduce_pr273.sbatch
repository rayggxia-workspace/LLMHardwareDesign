#!/bin/bash
#SBATCH --job-name=yzl-273-audit
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:30:00
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$PWD/audits/pr273-source-048e741:$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join(d["module_roots"]+d["extra_python_roots"]))')"
out="evidence/range-integration/pr273-$SLURM_JOB_ID";mkdir -p "$out"
"$python" audits/pr273-source-048e741/test_tile_frontier.py > "$out/tests.log" 2>&1
bench=audits/pr273-source-048e741/benchmark_tile_frontier.py
archive=evidence/full-algo1-113543/hardware.json
"$python" "$bench" "$archive" --columns 128 --width 32 --sram-rate 64 --ddr-rate 16 --output "$out/128-shared.json" > "$out/128-shared.log" 2>&1 &
a=$!
"$python" "$bench" "$archive" --columns 2048 --width 32 --sram-rate 64 --ddr-rate 16 --output "$out/2048-shared.json" > "$out/2048-shared.log" 2>&1 &
b=$!
"$python" "$bench" "$archive" --columns 2048 --width 32 --sram-rate 64 --ddr-rate 16 --bank-bytes 16384 --bank-rate 64 --accumulator-bytes 8 --max-group-outputs 1024 --multi-groups 4 --output "$out/2048-bank.json" > "$out/2048-bank.log" 2>&1 &
c=$!
wait "$a";wait "$b";wait "$c"
