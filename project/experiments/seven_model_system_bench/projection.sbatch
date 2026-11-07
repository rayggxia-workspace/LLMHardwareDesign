#!/bin/bash
#SBATCH --job-name=hpy-seven-m
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --cpus-per-task=6
set -euo pipefail
root=$(realpath "$1")
inputs=$(realpath "$2")
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c projection-upload.sha256
mkdir projection-tmp
export PYTHONDONTWRITEBYTECODE=1
export SINGULARITYENV_TMPDIR="$root/projection-tmp"
export SINGULARITYENV_XDG_CACHE_HOME="$root/projection-tmp"
python3 -B prepare_projection.py "$root/frozen-systemc.json" "$inputs" \
    "$inputs/cd-full-20261102-03" "$root/projection-results"
out="$root/projection-results"
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv
     --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
verilator=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
"${sim[@]}" "$verilator" --version >"$out/version.txt"
"${sim[@]}" "$verilator" --lint-only -Wall "$root/block_v2_m.sv" >"$out/lint.log" 2>&1
"${sim[@]}" "$verilator" --cc --exe --build -j "$SLURM_CPUS_PER_TASK" \
    --top-module block_v2_m --Mdir "$out/obj" \
    -CFLAGS '-std=c++17 -O1 -Wall -Wextra -Werror' \
    "$root/block_v2_m.sv" "$root/projection.cpp" >"$out/build.log" 2>&1
for run in "$out"/*/vectors.json; do
    folder=${run%/*}
    for fixture in "$folder"/*.txt; do
        for case in 'serial 0' 'prefetch 0' 'prefetch 4'; do
            read -r schedule hold <<<"$case"
            "${sim[@]}" "$out/obj/Vblock_v2_m" "$fixture" "$schedule" "$hold" \
                >"${fixture%.txt}-$schedule-$hold.json"
        done
    done
done
(cd "$out"; sha256sum -- */*.json */*.txt version.txt obj/Vblock_v2_m >results.sha256)
