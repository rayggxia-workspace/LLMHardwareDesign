#!/bin/bash
#SBATCH --job-name=hpy-offchip-build
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=00:15:00
set -euo pipefail
root=$(realpath "$1")
archive=$(realpath "$2")
systemc=$(realpath "$3")
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-offchip-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c upload.sha256
expected=$(awk '$2 == "systemc-source.tar" {print $1}' "$(dirname "$archive")/systemc-upload.sha256")
printf '%s  %s\n' "$expected" "$archive" | sha256sum -c
mkdir "$root/source" "$root/build-tmp"
export TMPDIR="$root/build-tmp" XDG_CACHE_HOME="$root/build-tmp"
tar -xf "$archive" -C "$root/source"
(
  cd "$root/source"
  llm=project/systemc/llm
  # The frozen archive was staged by a Windows checkout. Normalize only the
  # three copied inputs, then bind the patch to their original Git blob IDs.
  sed -i 's/\r$//' "$llm"/{runtime.hpp,recurrent.hpp,llm_bench.cpp}
  test "$(git hash-object "$llm/runtime.hpp")" = 604091428ade34181c196f56aaca2825a45e7cbf
  test "$(git hash-object "$llm/recurrent.hpp")" = 8cad71e0c37badffedd3a791be59259e213fe423
  test "$(git hash-object "$llm/llm_bench.cpp")" = be7b82b3ba34d2f289d03ff52d74b9091a76d63f
  git apply --unidiff-zero --check "$root/external_memory.patch"
  git apply --unidiff-zero "$root/external_memory.patch"
  cp "$root/external_memory.hpp" project/systemc/llm/
)
cat > "$root/source/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.16)
project(llm_offchip LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
find_package(SystemCLanguage CONFIG REQUIRED)
add_executable(llm_offchip project/systemc/llm/llm_bench.cpp)
target_include_directories(llm_offchip PRIVATE project/systemc/include project/systemc/llm)
target_link_libraries(llm_offchip PRIVATE SystemC::systemc)
target_compile_options(llm_offchip PRIVATE -Wall -Wextra -Werror)
CMAKE
cmake -S "$root/source" -B "$root/build" -DCMAKE_PREFIX_PATH="$systemc" -DCMAKE_BUILD_TYPE=Release
cmake --build "$root/build" -j "$SLURM_CPUS_PER_TASK"
unset LLM_LINK LLM_OFFCHIP LLM_FLOW_DIR
LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1 LLM_ACCURATE_SILU=1 \
  "$root/build/llm_offchip" --selftest > "$root/macro-selftest.log" 2>&1
grep 'LLM_ADAPTER_SELFTEST PASS' "$root/macro-selftest.log"
{
  c++ --version
  cmake --version
  grep '^SystemCLanguage_DIR:' "$root/build/CMakeCache.txt"
} > "$root/tools.txt"
sha256sum -- build/llm_offchip source/project/systemc/llm/{runtime.hpp,recurrent.hpp,llm_bench.cpp,external_memory.hpp} \
  macro-selftest.log tools.txt > build.sha256
