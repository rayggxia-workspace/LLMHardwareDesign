#!/usr/bin/env bash
#SBATCH --job-name=zny-qwenddr
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=3
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.out
set -euo pipefail

sha256sum -c source.sha256
shared=/public/home/yuzelu/project-circuit
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
basis=$shared/issue234-algo1-ffn-chain-20261112-01
dram=$basis/dramsim3
config=$basis/DDR4-single-channel.ini
qkv=$shared/issue260-product-archived-qkv3-0s7UrbHi/replay-106093
rms=$shared/issue260-decode638-live-product-next-rms-u8Z2olTH/replay-105530
kv=$shared/LLMHardwareDesign/issue-234-systemc-benchmark/sequence-range-segments-OT8GaRTa
printf '%s  %s\n' \
    40bebfe479208bd6660c7619bb55735678c6b2751fc309e4f700e94b407bd3b1 "$dram/libdramsim3.so" \
    b750651e5fc871df216570cfa1687894f9242a16a26fb69bf1099a97f5080e4b "$dram/src/memory_system.h" \
    748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766 "$config" | sha256sum -c -
sha256sum "$image" "$dram/libdramsim3.so" "$dram/src/memory_system.h" "$config" > tools.sha256
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu "$image" bash -s -- "$dram" "$config" "$qkv" "$rms" "$kv" <<'RUN'
set -euo pipefail
export LC_ALL=C
g++ --version > compiler-version.txt
python3 --version > python-version.txt
g++ -std=c++17 -O2 -Wall -Wextra -Werror -isystem "$1/src" -isystem "$1/ext/headers" \
    replay_native_ddr.cpp -L"$1" -Wl,-rpath,"$1" -ldramsim3 -o replay_native_ddr > build.log 2>&1
python3 -B qwen_native_ddr.py archived_qkv "$3" ./replay_native_ddr "$2" archived-qkv > archived-qkv.json &
qkv_pid=$!
python3 -B qwen_native_ddr.py next_rms "$4" ./replay_native_ddr "$2" next-rms > next-rms.json &
rms_pid=$!
python3 -B qwen_kv_reference.py "$5" --case 2 --case 3 > kv-reference.json &
kv_pid=$!
failed=0
for pid in "$qkv_pid" "$rms_pid" "$kv_pid"; do wait "$pid" || failed=1; done
test "$failed" -eq 0
sha256sum archived-qkv.json next-rms.json kv-reference.json tools.sha256 source.sha256 \
    compiler-version.txt python-version.txt replay_native_ddr > output.sha256
RUN
