#!/bin/bash
#SBATCH --job-name=lrz-i61-replay
#SBATCH --partition=c96
#SBATCH --cpus-per-task=8
#SBATCH --time=00:20:00
set -euo pipefail
root=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023
run=${1:-run01}
test ! -e "$root/$run"
mkdir "$root/$run"
cd "$root/$run"
export TMPDIR="$root/tmp" HF_HOME="$root/cache" TORCH_HOME="$root/cache"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
test "${SLURM_CPUS_PER_TASK}" -eq 8
hostname > host.txt
lscpu > lscpu.txt
free -b > memory-before.txt
if command -v nvidia-smi >/dev/null 2>&1; then nvidia-smi > gpu.txt; else printf 'No nvidia-smi available\n' > gpu.txt; fi
python=/public/home/yuzelu/RuizhiLiang/issue53-cpu-pilot-20261023/venv/bin/python
"$python" -B "$root/source/replay.py" --mode partials --input "$root/input/qwen25-partials.pt.gz" \
 --sha256 ab6b0d8c527aad005a45b6f5b14d6281e3d435cd03dde4dbf02c33dbbba7be98 --binding "$root/binding.json" --out qwen25-partials.json > qwen25.log 2>&1 &
p1=$!
"$python" -B "$root/source/replay.py" --mode partials --input "$root/input/qwen35-partials.pt.gz" \
 --sha256 bd06f4c23026d955ca3e1df2f846fe31a39c32ab1c092d81d9b835f3f0f68e5a --binding "$root/binding.json" --out qwen35-partials.json > qwen35.log 2>&1 &
p2=$!
"$python" -B "$root/source/replay.py" --mode states --input "$root/input/qwen35-states.pt.gz" \
 --sha256 049c1cf4e81044fdc740dd1e65701a86293f31293d4b0ee2c554daecfef4e91a --binding "$root/binding.json" --out qwen35-states.json > states.log 2>&1 &
p3=$!
rc=0
wait "$p1" || rc=1
wait "$p2" || rc=1
wait "$p3" || rc=1
free -b > memory-after.txt
printf '%s\n' "$rc" > exit.txt
exit "$rc"
