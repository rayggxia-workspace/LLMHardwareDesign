#!/usr/bin/env bash
#SBATCH --job-name=zny-dramlive
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.out
set -euo pipefail

root=$PWD
sha256sum -c source.sha256
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
reference=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/strict-dram-repeat-ZyprDHdt
dram=$reference/raw/dramsim3-source-001
config=$reference/systemc-dram-001/results-002/native.ini
printf '%s  %s\n' \
    2aa0b2c81b1943065fbbb56620774333313bf1b1d7009343b37af5cbdeba15ef "$dram/libdramsim3.so" \
    1727137ebfc02836855f0efe91ac6accaa089711d2124e0d0720704527787d3b "$dram/src/dramsim3.h" \
    748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766 "$config" | sha256sum -c -
sha256sum "$image" "$dram/libdramsim3.so" "$dram/src/dramsim3.h" "$config" > tools.sha256
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu "$image" bash -s -- "$root" "$dram" "$config" <<'RUN'
set -euo pipefail
export LC_ALL=C
cd "$1"
g++ --version > compiler-version.txt
python3 --version > python-version.txt
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$2/src" dramsim_bridge.cpp \
    -L"$2" -Wl,-rpath,"$2" -ldramsim3 -o dramsim_bridge > build.log 2>&1
python3 -B check_dma_ddr.py --binary ./dramsim_bridge --config "$3" --output results > result.json
sha256sum result.json build.log compiler-version.txt python-version.txt tools.sha256 source.sha256 \
    results/{reference,coupled}/dramsim3.json > output.sha256
RUN
