#!/bin/bash
#SBATCH --job-name=yzl-289-U-guardant
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=08:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-guardant-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$root/audit/U-antenna/candidate-guard-ant-v1
mkdir "$run"
cp "$root/cu/runs/U-v13-electrical-f50-x4/config.mk" "$run/config.mk"
cp "$root/audit/u-ant-edit.tcl" "$root/audit/u-ant-route.tcl" "$root/audit/u-ant-fresh-source.tcl" "$root/audit/U-antenna/insert-diodes-v1.tcl" "$run/"
export U_RESULTS=$run/flow/results/nangate45/u-overlay-current/base
for kind in results logs reports objects; do mkdir -p "$run/flow/$kind/nangate45/u-overlay-current/base"; done
export U_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
sha256sum "$root/u-physical/candidate-guard-v1/guarded-before-route.odb" "$root/cu/runs/U-v13-electrical-f50-x4/flow/results/nangate45/u-overlay-current/base/6_final.sdc" "$root/audit/U-antenna/antenna-net-map.json" "$root/audit/U-antenna/diode-model.json" "$run/"*.tcl > "$run/inputs.sha256"
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$run" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit u-ant-edit.tcl > edit.log 2>&1; openroad -no_init -exit u-ant-route.tcl > implementation.log 2>&1; rc=0; openroad -no_init -exit u-ant-fresh-source.tcl > fresh-gate.log 2>&1 || rc=$?; printf "%s\n" "$rc" > fresh-exit-code; make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$PWD/config.mk" WORK_HOME="$PWD/flow" NUM_CORES=8 do-gds > gds.log 2>&1; klayout -b -r /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-antenna/antenna-only-v2.lydrc -rd in_gds="$U_RESULTS/6_final.gds" -rd report_file="$PWD/antenna-diagnostic.lyrdb" > antenna-diagnostic.log 2>&1; echo ANTENNA_CANDIDATE_DIAGNOSTIC_FINISHED_NOT_ACCEPTED'
