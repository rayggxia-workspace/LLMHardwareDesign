#!/bin/bash
#SBATCH --job-name=yzl-sc240
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=4
#SBATCH --time=00:30:00
set -euo pipefail
cd "$1"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
prefix=/public/home/yuzelu/opt/systemc-3.0.2-issue219
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
mkdir -p generated
sha256sum extract.py model.cpp run.sbatch tb_m_timing.sv block_v2_m.sv sweep.py smoke.py validate.py kernel_probe.cpp check_kernels.py "$prefix/lib/libsystemc.so" > source.sha256
"$python" -B extract.py > extract.log 2>&1
"${sim[@]}" /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --binary --timing -Wno-fatal -j 4 --top-module tb_m_timing --Mdir obj_m tb_m_timing.sv block_v2_m.sv > native-build.log 2>&1
"${sim[@]}" ./obj_m/Vtb_m_timing > m-profile.log 2>&1
grep -q M_PROFILE_PASS m-profile.log
"${sim[@]}" g++ -std=c++17 -O2 -Wall -Wextra -Werror model.cpp -I"$prefix/include" -L"$prefix/lib" -Wl,-rpath,"$prefix/lib" -lsystemc -o model > build.log 2>&1
"${sim[@]}" g++ -std=c++17 -O2 -Wall -Wextra -Werror kernel_probe.cpp -o kernel_probe > kernel-build.log 2>&1
"$python" -B check_kernels.py > kernels.log 2>&1
"$python" -B validate.py > validation.log 2>&1
"$python" -B smoke.py > smoke.log 2>&1
if [ "${2:-full}" != smoke ]; then "$python" -B sweep.py > sweep.log 2>&1; fi
sha256sum generated/* *.log > output.sha256
