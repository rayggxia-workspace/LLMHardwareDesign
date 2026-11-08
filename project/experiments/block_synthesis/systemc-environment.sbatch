#!/bin/bash
#SBATCH --job-name=yzl-systemc-env
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
cd "$root"
prefix=/public/home/yuzelu/opt/systemc-3.0.2-issue219
# Never replace another installation or attempt's source/build directories.
test ! -e "$prefix"
url=https://github.com/accellera-official/systemc/archive/refs/tags/3.0.2.tar.gz
printf '%s\n' "$url" > source-url.txt
if test ! -f systemc-3.0.2.tar.gz; then
    curl --fail --location --connect-timeout 15 --max-time 120 "$url" -o systemc-3.0.2.tar.gz
fi
sha256sum systemc-3.0.2.tar.gz systemc_environment.cpp > input.sha256
mkdir source
tar -xzf systemc-3.0.2.tar.gz --strip-components=1 -C source
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
"${sim[@]}" cmake -S source -B build -DCMAKE_CXX_STANDARD=17 -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib -DENABLE_EXAMPLES=OFF > configure.log 2>&1
"${sim[@]}" cmake --build build --parallel "$SLURM_CPUS_PER_TASK" > build.log 2>&1
"${sim[@]}" cmake --install build > install.log 2>&1
"${sim[@]}" g++ -std=c++17 -Wall -Wextra -Werror systemc_environment.cpp -I"$prefix/include" -L"$prefix/lib" -Wl,-rpath,"$prefix/lib" -lsystemc -o systemc-environment > application-build.log 2>&1
"${sim[@]}" "$root/systemc-environment" > smoke.log 2>&1
sha256sum smoke.log "$prefix/lib/libsystemc.so" "$prefix/include/sysc/kernel/sc_ver.h" > output.sha256
