#!/usr/bin/env bash
#SBATCH --job-name=mdt-280mexec300
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail

if [[ ${1:-} != inside ]]; then
    bundle=${SLURM_SUBMIT_DIR:?}
    cd "$bundle"
    sha256sum --quiet -c inputs.sha256
    opt=$HOME/LLMHardware/opt
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" "$opt/orfs-current-repacked.rootfs" \
        bash "$bundle/run_bscc_t6_m_exec_physical.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/physical-$3
candidate=$root/m-exec-ready/check-38784054/source/project/rtl/w8a16_v1
mkdir "$out"
rtl=(m_native_leaf_s32 m_native_s32 weight_records m_group_s32 projection_context_s32 scale_group_s32)
sources=()
for name in "${rtl[@]}"; do sources+=("$candidate/$name.sv"); done
openroad -version > "$out/openroad-version.txt"
yosys -V > "$out/yosys-version.txt"
sed '/^set_propagated_clock /d' "$root/m-sta/6_final.sdc" > "$out/target.sdc"
grep -Fq -- '-period 3.3333' "$out/target.sdc"
cat > "$out/config.mk" <<EOF
export PLATFORM = nangate45
export DESIGN_NAME = m_native_leaf_s32
export DESIGN_NICKNAME = m_exec_ready_300
export SYNTH_HDL_FRONTEND = slang
export SYNTH_MEMORY_MAX_BITS = 36864
export VERILOG_FILES = ${sources[*]}
export SDC_FILE = $out/target.sdc
export DIE_AREA = 0 0 1390 1390
export CORE_AREA = 14 14 1376 1376
export PLACE_DENSITY = 0.55
export SETUP_SLACK_MARGIN = 0.100
export HOLD_SLACK_MARGIN = 0.030
EOF
sha256sum "${sources[@]}" "$out/"{config.mk,target.sdc,openroad-version.txt,yosys-version.txt} > "$out/physical-source.sha256"
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$out/config.mk" WORK_HOME="$out/flow" \
    NUM_CORES="$4" finish > "$out/flow.log" 2>&1
key=nangate45/m_exec_ready_300/base
cd "$out"
sha256sum physical-source.sha256 "flow/results/$key/"6_final.{v,odb,sdc,spef} "flow/logs/$key/6_report.json" > physical.sha256
sha256sum -c physical.sha256
