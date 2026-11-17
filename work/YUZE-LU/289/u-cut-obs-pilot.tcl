set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
read_db $root/cu/runs/U-v13-electrical-f50-x4/flow/results/nangate45/u-overlay-current/base/6_final.odb
set master [[ord::get_db] findMaster local_s_base]
set layer [[ord::get_db_tech] findLayer via9]
set n [llength [$master getObstructions]]
set test [odb::dbBox_create $master $layer 0 0 10 10]
if {[llength [$master getObstructions]]!=$n+1} {error "Master obstruction API failed"}
puts CUT_OBSTRUCTION_API_PROBE_ONLY_NO_OUTPUT_DB
