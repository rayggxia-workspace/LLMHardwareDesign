#!/bin/bash
#SBATCH --job-name=yzl-sc234-tools
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:30:00
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/toolchain-*) ;; *) exit 2;; esac
cd "$root"
printf '%s  %s\n' 832aeb58d105de1cabc7b982dd2c65de0610f7377df48ae8fc2dd8e97420a15c LLVM-23.1.1-Linux-X64.tar.xz | sha256sum --check
mkdir extracted-001
tar -xJf LLVM-23.1.1-Linux-X64.tar.xz -C extracted-001
llvm=$(realpath extracted-001/LLVM-23.1.1-Linux-X64)
export OMP_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10 MKL_NUM_THREADS=10
run=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
for name in clang clang++ mlir-opt mlir-translate llvm-config ld.lld; do
  "$run" exec --cleanenv --bind /public/home/yuzelu "$image" bash -c '
    tool="$1/bin/$2"
    printf "TOOL %s\n" "$tool"
    sha256sum "$tool"
    ldd "$tool" || true
    "$tool" --version
  ' tool-probe "$llvm" "$name" >"$name.log" 2>&1 &
done
failed=0
for pid in $(jobs -p); do wait "$pid" || failed=1; done
printf 'probe_failed=%s\n' "$failed" >result.txt
find "$llvm/lib/cmake" -maxdepth 2 -name '*Config.cmake' -print >cmake-packages.txt
sha256sum *.log result.txt cmake-packages.txt >output.sha256
exit "$failed"
