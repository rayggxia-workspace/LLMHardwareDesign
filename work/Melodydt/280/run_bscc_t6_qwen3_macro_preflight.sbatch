#!/usr/bin/env bash
#SBATCH --job-name=mdt-280macrophys
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
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
        bash "$bundle/run_bscc_t6_qwen3_macro_preflight.sbatch" inside \
        "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
archive=$(dirname "$bundle")/incoming/macro-views
out=$bundle/preflight-$3
mkdir "$out"
(cd "$archive/source" && sha256sum --quiet -c ../source-files.sha256)
(cd "$archive/mother128" && sha256sum --quiet -c ../mother-subset.sha256)
export BASE_LIB=/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
export SRAM_LIB=$archive/source/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib
openroad -version > "$out/tool.txt"
cat > "$out/physical.tcl" <<'TCL'
read_liberty $::env(BASE_LIB)
read_liberty $::env(SRAM_LIB)
read_db $::env(VIEW)/6_final.odb
read_sdc $::env(VIEW)/6_final.sdc
read_spef $::env(VIEW)/6_final.spef
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
set count 0
foreach inst [$block getInsts] {
    set master [$inst getMaster]
    if {[$master getName] eq "s_sram_256x128_freepdk45"} {
        incr count
        puts "MACRO [$inst getName] [$master getName]"
    }
}
if {$count != 4 || [llength [all_clocks]] != 1} {
    error "expected four SRAM banks and one source clock"
}
report_clock_properties [all_clocks]
report_worst_slack -max
report_worst_slack -min
help report_power
help set_power_activity
report_power -digits 9
puts MACRO_PHYSICAL_PREFLIGHT_OK
TCL
for entry in \
    "s-p:$archive/source/issue-200-compact-local-s/run10-delay1/results/4/flow/results/nangate45/local_s_p/base" \
    "s-base:$archive/source/issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base" \
    "mother:$archive/mother128/physical"; do
    export VIEW=${entry#*:}
    name=${entry%%:*}
    log=$out/$name.log
    openroad -no_init -threads "$4" -exit "$out/physical.tcl" > "$log" 2>&1
    grep '^MACRO_PHYSICAL_PREFLIGHT_OK$' "$log"
    if grep -qE '^(\[ERROR|Error:)' "$log"; then
        cat "$log"
        exit 1
    fi
done
cd "$out"
sha256sum "$archive/source-files.sha256" "$archive/mother-subset.sha256" \
    "$BASE_LIB" tool.txt physical.tcl *.log > results.sha256
sha256sum -c results.sha256
