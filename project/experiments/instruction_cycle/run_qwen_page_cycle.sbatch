#!/usr/bin/env bash
#SBATCH --job-name=zny-qwenpage
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.out
set -euo pipefail

sha256sum -c source.sha256
shared=/public/home/yuzelu/project-circuit
basis=$shared/issue234-algo1-ffn-chain-20261112-01
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
archive=$shared/issue260-decode638-live-product-next-rms-u8Z2olTH/replay-105530
embedding=$shared/LLMHardwareDesign/issue-234-systemc-benchmark/native-model-constants-mC0bSR2w/image/0000.s32le
dram=$basis/dramsim3
config=$basis/DDR4-single-channel.ini
probe=$(realpath "${1:?verified 108208 edge directory required}")
shift
printf '%s  %s\n' \
    40bebfe479208bd6660c7619bb55735678c6b2751fc309e4f700e94b407bd3b1 "$dram/libdramsim3.so" \
    748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766 "$config" | sha256sum -c -
sha256sum "$image" "$config" "$dram/libdramsim3.so" "$dram/src/dramsim3.h" > tools.sha256
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu "$image" bash -s -- "$dram" "$config" "$archive" "$embedding" "$probe" "$@" <<'RUN'
set -euo pipefail
export LC_ALL=C
g++ --version > compiler-version.txt
python3 --version > python-version.txt
dram=$1 config=$2 archive=$3 embedding=$4 probe=$5
shift 5
g++ -std=c++17 -O2 -Wall -Wextra -Werror -isystem "$dram/src" dramsim_bridge.cpp \
    -L"$dram" -Wl,-rpath,"$dram" -ldramsim3 -o bridge-read > build.log 2>&1
for mode in 0 1; do
    python3 -B qwen_page_cycle.py predict "$archive" ./bridge-read "$config" "device-$mode" "$embedding" --mode "$mode" "$@" \
        > "prediction-$mode.json"
done
sha256sum prediction-{0,1}.json > prediction.sha256
for mode in 0 1; do
    python3 -B qwen_page_cycle.py compare "$archive" "prediction-$mode.json" "$probe/edges-$mode.log" "$@" \
        > "comparison-$mode.json"
done
sha256sum -c prediction.sha256
sha256sum prediction-?.json comparison-?.json prediction.sha256 tools.sha256 source.sha256 \
    compiler-version.txt python-version.txt bridge-read > output.sha256
RUN
