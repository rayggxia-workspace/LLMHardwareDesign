#!/usr/bin/env bash
#SBATCH --job-name=zny-dramcdc
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
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
    748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766 "$config" | sha256sum -c -
sha256sum "$image" "$dram/libdramsim3.so" "$config" > tools.sha256
(
    cd "$dram"
    find src ext -type f -print0 | sort -z | xargs -0 sha256sum
) > upstream-build-inputs.sha256
printf '%s  %s\n' 1f65700e5738dcdc4d5ddd33b791e4db1d2aabf607bca13b4cdf061dd6986ba4 \
    upstream-build-inputs.sha256 | sha256sum -c -
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu "$image" bash -s -- "$root" "$dram" "$config" "$SLURM_CPUS_PER_TASK" <<'RUN'
set -euo pipefail
export LC_ALL=C
cd "$1"
g++ --version > compiler-version.txt
python3 --version > python-version.txt
cmake --version > cmake-version.txt
python3 -B patch_dramsim_write.py "$2" "$PWD/dramsim-src" "$3" "$PWD/unified.ini"
cmake -S dramsim-src -B dramsim-build -DCMAKE_BUILD_TYPE=Release -DCMD_TRACE=ON > configure.log 2>&1
cmake --build dramsim-build --target dramsim3 -j "$4" > library-build.log 2>&1
test -f dramsim-src/libdramsim3.so
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$2/src" dramsim_bridge.cpp \
    -L"$2" -Wl,-rpath,"$2" -ldramsim3 -o bridge-stock > stock-build.log 2>&1
g++ -std=c++17 -O2 -Wall -Wextra -Werror -DISSUE265_WRITE_COMMIT -Idramsim-src/src dramsim_bridge.cpp \
    -Ldramsim-src -Wl,-rpath,"$PWD/dramsim-src" -ldramsim3 -o bridge-write > bridge-build.log 2>&1
python3 -B check_dram_write_cdc.py --stock ./bridge-stock --stock-config "$3" \
    --binary ./bridge-write --config ./unified.ini --output results > result.json
python3 -B audit_dram_write_cdc.py result.json results > audit.json
sha256sum result.json audit.json unified.ini dramsim-src/libdramsim3.so bridge-stock bridge-write \
    configure.log library-build.log stock-build.log bridge-build.log compiler-version.txt python-version.txt \
    cmake-version.txt tools.sha256 source.sha256 upstream-build-inputs.sha256 \
    results/*/dramsim3.json > output.sha256
find results -name '*cmd.trace' -type f -print0 | sort -z | xargs -0 -r sha256sum >> output.sha256
RUN
