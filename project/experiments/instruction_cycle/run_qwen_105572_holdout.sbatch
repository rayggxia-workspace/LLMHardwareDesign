#!/usr/bin/env bash
#SBATCH --job-name=zny-qwenhold
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
sha256sum -c source.sha256
root=/public/home/yuzelu/project-circuit
archive=$root/issue260-decode638-live-product-c639-pWbjIwaZ/replay-105572
embedding=$root/LLMHardwareDesign/issue-234-systemc-benchmark/native-model-constants-mC0bSR2w/image/0000.s32le
basis=$root/issue234-algo1-ffn-chain-20261112-01
config=$basis/DDR4-single-channel.ini
dram=$basis/dramsim3
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
printf '%s  %s\n' \
    40bebfe479208bd6660c7619bb55735678c6b2751fc309e4f700e94b407bd3b1 "$dram/libdramsim3.so" \
    748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766 "$config" \
    49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a "$image" \
    1b4ab04710b5328016aed55bc0d37d396875b210996d6dd5b757b9208ec5e9ac "$archive/proof.sha256" > inputs.sha256
sha256sum -c inputs.sha256
stage=${1:?run predict before compare}
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu "$image" bash -s -- "$stage" "$dram" "$config" "$archive" "$embedding" "${2:-}" "${3:-}" <<'RUN'
set -euo pipefail
stage=$1 dram=$2 config=$3 archive=$4 embedding=$5
export LC_ALL=C
case "$stage" in
    predict)
        g++ --version > compiler-version.txt
        python3 --version > python-version.txt
        g++ -std=c++17 -O2 -Wall -Wextra -Werror -isystem "$dram/src" dramsim_bridge.cpp \
            -L"$dram" -Wl,-rpath,"$dram" -ldramsim3 -o bridge-read > build.log 2>&1
        for mode in 0 1; do
            python3 -B qwen_heldout_cycle.py predict "$archive" ./bridge-read "$config" \
                "device-$mode" "$embedding" --mode "$mode" > "prediction-$mode.json"
        done
        sha256sum prediction-{0,1}.json > prediction.sha256
        sha256sum source.sha256 inputs.sha256 bridge-read compiler-version.txt python-version.txt \
            prediction.sha256 prediction-{0,1}.json > model-output.sha256
        ;;
    compare)
        estimates=("$6" "$7")
        sha256sum -c prediction.sha256
        for mode in 0 1; do
            python3 -B qwen_heldout_cycle.py compare "$archive" "prediction-$mode.json" "${estimates[mode]}" \
                > "heldout-comparison-$mode.json"
        done
        sha256sum heldout-comparison-{0,1}.json prediction.sha256 > output.sha256
        sha256sum -c output.sha256
        ;;
    *) exit 2 ;;
esac
RUN
