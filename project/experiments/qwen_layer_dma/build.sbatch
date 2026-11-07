#!/bin/bash
#SBATCH --job-name=hpy-layer-build
#SBATCH --partition=c96
#SBATCH --cpus-per-task=6
#SBATCH --time=00:45:00
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-rtl-layer-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c upload.sha256
mkdir "$root/tmp" "$root/rtl" "$root/obj"
export TMPDIR="$root/tmp" XDG_CACHE_HOME="$root/tmp" PYTHONDONTWRITEBYTECODE=1
python3 -B -I -S prepare.py "$root" \
 /public/home/yuzelu/PingyangHuang/issue-197-long-gzQzpiwn \
 /public/home/yuzelu/PingyangHuang/issue-197-offchip-CZAeok0o/source/project/systemc
tar -xf rtl-source.tar -C rtl
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
vl=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
rtl="$root/rtl/project/rtl"
for macro in block_v2_m block_v2_n block_v2_e block_v2_g r_stream_local layer_dma; do
 args=()
 case "$macro" in
  block_v2_n) inputs=("$rtl/block_v2/block_v2_n.sv" "$rtl/block_v2/block_v2_n_group.sv");;
  block_v2_*) inputs=("$rtl/block_v2/$macro.sv");;
  r_stream_local) inputs=("$rtl/r_local_state/r_stream_local.sv" "$rtl/r_local_state/r_state_store.sv")
    args=(-GWORDS=1024 "$root/rtl/project/experiments/control_v1/native_r_lint.vlt" "$root/r1024_lint.vlt");;
  layer_dma) inputs=("$root/layer_dma.sv" "$rtl/hbm_feed/hbm_group_dma.sv" "$rtl/block_feed_v1/block_feed_s16k.sv");;
 esac
 "${sim[@]}" "$vl" --cc --build -j "$SLURM_CPUS_PER_TASK" --assert \
   --top-module "$macro" --Mdir "$root/obj/$macro" \
   -I"$rtl/block_v2" "${args[@]}" "${inputs[@]}" > "$root/build-$macro.log" 2>&1
done
systemc=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153/install
includes=("-I$root/source/include/blocks" "-I$root/source/include" "-I$root/source/llm" "-I$systemc/include"
 "-isystem" "/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator/include")
libraries=()
for macro in block_v2_m block_v2_n block_v2_e block_v2_g r_stream_local layer_dma; do
 includes+=("-I$root/obj/$macro");libraries+=("$root/obj/$macro/V${macro}__ALL.a")
done
"${sim[@]}" g++ -std=c++17 -O2 -DSC_ALLOW_DEPRECATED_IEEE_API -Wall -Wextra -Werror "${includes[@]}" \
 "$root/source/llm/llm_bench.cpp" -L"$systemc/lib64" -Wl,-rpath,"$systemc/lib64" -lsystemc -pthread \
 -o "$root/systemc-layer" > "$root/link-systemc.log" 2>&1
"${sim[@]}" g++ -std=c++17 -O2 -DSC_ALLOW_DEPRECATED_IEEE_API -Wall -Wextra -Werror -DUSE_NATIVE_RTL "${includes[@]}" \
 "$root/source/llm/llm_bench.cpp" "${libraries[@]}" \
 "$root/obj/layer_dma/libverilated.a" \
 -L"$systemc/lib64" -Wl,-rpath,"$systemc/lib64" -lsystemc -pthread -latomic \
 -o "$root/native-layer" > "$root/link-native.log" 2>&1
sha256sum systemc-layer native-layer generated-inputs.json > build.sha256
