#!/usr/bin/env bash
#SBATCH --job-name=yzl-g-power
#SBATCH --partition=c96
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=12
#SBATCH --nodes=1
#SBATCH --time=00:15:00
set -euo pipefail
r="$SLURM_SUBMIT_DIR"
scontrol show job "$SLURM_JOB_ID" > "$r/allocation.txt"
(cd "$r"; sha256sum *.py delivery.json job.sh) > "$r/source.sha256"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
echo "49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image" | sha256sum -c
mkdir -p "$r/tmp"
srun --exact -n1 -c12 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 --env "TMPDIR=$r/tmp,OMP_NUM_THREADS=12,OPENBLAS_NUM_THREADS=1" "$image" bash -c '
 set -euo pipefail
 source /OpenROAD-flow-scripts/env.sh
 unset VERILATOR_ROOT
 r=$1
 old=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-250-g-physical-20261111-06
 python3 "$r/g_activity.py" --source "$old/source/project/experiments/w8a16_g/test_g_s32.sv" --prior "$old/function" --delivery "$r" --out "$r"
 vlt=/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator
 "$vlt" --binary --timing --assert --timescale-override 1ns/1ps -Wno-fatal --trace-vcd --trace-underscore \
  --x-initial unique --x-assign unique --top-module test_g_s32 -j 12 --Mdir "$r/obj" "$r/test_g_s32_activity.sv" \
  "$old/function/physical-functional.v" "$old/function/cells.v" > "$r/build.log" 2>&1
 for mode in active idle; do
  extra=()
  if [[ $mode == idle ]]; then extra=(+activity_idle); fi
  "$r/obj/Vtest_g_s32" "+vectors=$r/actual-model-vectors.txt" +mode=0 +verilator+seed+143 +verilator+rand+reset+2 \
    "+activity=$r/$mode.vcd" "${extra[@]}" > "$r/$mode-simulation.log" 2>&1
 done
 grep -q "G_S32_PASS mode=0 packets=256" "$r/active-simulation.log"
 python3 "$r/g_activity.py" --out "$r" --normalize
 python3 "$r/e_activity_pin_replay.py" --input "$r" --output "$r" --scope test_g_s32/dut --provider G --minimum-gate-pins 50000
 for mode in active idle active-clock-only; do
  openroad -no_init -exit "$r/$mode-pins.tcl" > "$r/$mode-pins.log" 2>&1
  grep -Eq "^unannotated +0$" "$r/$mode-pins.log"
 done
' bash "$r"
