#!/bin/bash
#SBATCH --job-name=lrz-cpupilot
#SBATCH --partition=debug
#SBATCH --cpus-per-task=32
#SBATCH --time=00:20:00
set -euo pipefail
root=/public/home/yuzelu/RuizhiLiang/issue53-cpu-pilot-20261023
cd "$root/run01"
export TMPDIR="$root/tmp" HF_HOME="$root/cache" TORCH_HOME="$root/cache"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 MKL_DYNAMIC=FALSE
test "${SLURM_CPUS_PER_TASK}" -eq 32
hostname > host.txt
lscpu > lscpu.txt
free -k > memory-before.txt
printf 'dtype\tthreads\texit\n' > exits.tsv
fail=0
for dtype in float32 bfloat16; do
    for threads in 8 16 32; do
        rc=0
        OMP_NUM_THREADS="$threads" MKL_NUM_THREADS="$threads" \
        "$root/venv/bin/python" -B source/pilot.py --model-dir "$root/model" \
            --inputs inputs.json --binding binding.json --threads "$threads" --dtype "$dtype" \
            --out "${dtype}-${threads}" > "${dtype}-${threads}.log" 2>&1 || rc=$?
        printf '%s\t%s\t%s\n' "$dtype" "$threads" "$rc" >> exits.tsv
        if [ "$rc" -ne 0 ]; then fail=1; fi
    done
done
free -k > memory-after.txt
exit "$fail"
