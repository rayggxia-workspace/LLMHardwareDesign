#!/bin/bash
#SBATCH --job-name=yzl-phase-survey
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
cd "$root"
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps
prefix=/public/home/yuzelu/opt/systemc-3.0.2-issue219
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
sha256sum *.py systemc_phase.cpp "$2" "$prefix/lib/libsystemc.so" > input.sha256
"$python" -B -m unittest discover -p 'test_*.py' -q > tests.log 2>&1
"$python" -u -B phase_survey.py "$2" generated > survey.log 2>&1
"${sim[@]}" g++ -std=c++17 -O2 -Wall -Wextra -Werror systemc_phase.cpp -I"$prefix/include" -L"$prefix/lib" -Wl,-rpath,"$prefix/lib" -lsystemc -o systemc-phase > build.log 2>&1
for mode in whole-service descriptor-phases; do
    "${sim[@]}" "$root/systemc-phase" generated/probe.txt "$mode" > "$mode.log" 2>&1
done
"$python" -B verify_phase_trace.py generated/reference.json whole-service.log descriptor-phases.log verification.json
sha256sum generated/* *.log verification.json systemc-phase > output.sha256
