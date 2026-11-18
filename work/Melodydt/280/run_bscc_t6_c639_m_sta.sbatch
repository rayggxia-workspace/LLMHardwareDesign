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
    sizing=${1:-baseline}
    cd "$bundle"
    sha256sum -c inputs.sha256
    image=$HOME/LLMHardware/opt/orfs-current-repacked.rootfs
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$bundle" "$image" bash "$bundle/run_bscc_t6_c639_m_sta.sbatch" \
        inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK" "$sizing"
fi

source /OpenROAD-flow-scripts/env.sh
export M300_BUNDLE=$2
export M300_OUT=$2/sta-$3
export M300_SIZING=$5
mkdir "$M300_OUT"
cat > "$M300_OUT/report.tcl" <<'TCL'
set data $::env(M300_BUNDLE)
set out $::env(M300_OUT)
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db $data/6_final.odb
if {$::env(M300_SIZING) == "trace"} {
    set block [ord::get_db_block]
    foreach name {{$auto$ff.cc:337:slice$118564} {$auto$ff.cc:337:slice$121693}} {
        set inst [$block findInst $name]
        if {$inst == "NULL"} {error "cannot find reported flop $name"}
        foreach term [$inst getITerms] {
            set net [$term getNet]
            if {$net != "NULL"} {puts "C639_M_TIMING_PIN $name [[$term getMTerm] getName] [$net getName]"}
        }
    }
    set net [[$block findBTerm a_ready] getNet]
    foreach term [$net getITerms] {
        puts "C639_M_READY_ENDPOINT [[$term getInst] getName] [[$term getMTerm] getName]"
    }
}
if {$::env(M300_SIZING) == "sizing"} {
    set db [ord::get_db]
    set block [ord::get_db_block]
    foreach {name before after} {
        place111308 BUF_X1 BUF_X4
        place117713 BUF_X1 BUF_X2
        place117711 BUF_X1 BUF_X2
        place114355 BUF_X1 BUF_X2
    } {
        set inst [$block findInst $name]
        if {$inst == "NULL" || [[$inst getMaster] getName] != $before} {error "unexpected path buffer $name"}
        set replacement "NULL"
        foreach lib [$db getLibs] {
            set match [$lib findMaster $after]
            if {$match != "NULL"} {set replacement $match; break}
        }
        if {$replacement == "NULL" || ![$inst swapMaster $replacement]} {error "no equivalent drive variant $after"}
        puts "C639_M_BUFFER_SIZING $name $before $after"
    }
}
read_sdc $data/6_final.sdc
read_spef $data/6_final.spef
set_propagated_clock [all_clocks]
report_worst_slack -max -digits 6
report_worst_slack -min -digits 6
report_tns -max -digits 6
report_tns -min -digits 6
report_checks -to [get_ports a_ready] -path_delay max -format full_clock_expanded -fields {slew cap fanout} -group_path_count 8 -digits 6 > $out/a-ready.rpt
report_checks -path_delay min -format full_clock_expanded -fields {slew cap fanout} -group_path_count 8 -digits 6 > $out/hold.rpt
puts "C639_M_TIMING_PATHS_READY"
TCL
openroad -no_init -threads "$4" -exit "$M300_OUT/report.tcl" > "$M300_OUT/sta.log" 2>&1
grep -Fq C639_M_TIMING_PATHS_READY "$M300_OUT/sta.log"
cd "$M300_OUT"
sha256sum report.tcl sta.log a-ready.rpt hold.rpt > results.sha256
sha256sum -c results.sha256
