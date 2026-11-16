#!/usr/bin/env bash
#SBATCH --job-name=mdt-280msta
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
    sha256sum -c inputs.sha256
    image=$HOME/LLMHardware/opt/orfs-current-repacked.rootfs
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$bundle" "$image" bash "$bundle/run_bscc_t6_c639_m_sta.sbatch" \
        inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi

source /OpenROAD-flow-scripts/env.sh
export M300_BUNDLE=$2
export M300_OUT=$2/sta-$3
mkdir "$M300_OUT"
cat > "$M300_OUT/report.tcl" <<'TCL'
set data $::env(M300_BUNDLE)
set out $::env(M300_OUT)
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db $data/6_final.odb
read_sdc $data/6_final.sdc
read_spef $data/6_final.spef
set_propagated_clock [all_clocks]
report_worst_slack -max -digits 6
report_worst_slack -min -digits 6
report_tns -max -digits 6
report_tns -min -digits 6
report_checks -to [get_ports a_ready] -path_delay max -format full_clock_expanded -fields {slew cap fanout nets} -group_path_count 8 -digits 6 > $out/a-ready.rpt
report_checks -path_delay min -format full_clock_expanded -fields {slew cap fanout nets} -group_path_count 8 -digits 6 > $out/hold.rpt
puts "C639_M_TIMING_PATHS_READY"
TCL
openroad -no_init -threads "$4" -exit "$M300_OUT/report.tcl" > "$M300_OUT/sta.log" 2>&1
grep -Fq C639_M_TIMING_PATHS_READY "$M300_OUT/sta.log"
cd "$M300_OUT"
sha256sum report.tcl sta.log a-ready.rpt hold.rpt > results.sha256
sha256sum -c results.sha256
