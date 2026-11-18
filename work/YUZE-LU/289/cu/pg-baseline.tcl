read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/U-v6-ctsdelay-x8-seed0/flow/results/nangate45/u-overlay-current/base/5_1_grt.odb
foreach rail {VDD VSS} {
 set code [catch {check_power_grid -net $rail} reason]
 puts "BASELINE_PG $rail code=$code result=$reason"
}
