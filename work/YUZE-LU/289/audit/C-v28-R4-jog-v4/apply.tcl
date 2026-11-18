set_thread_count 8
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base/6_final.odb
write_def /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v28-R4-jog-v4/before.def
write_verilog /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v28-R4-jog-v4/before.v
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v28-R4-jog-v4/hook.tcl
write_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v28-R4-jog-v4/patched.odb
write_def /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v28-R4-jog-v4/patched.def
write_verilog /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v28-R4-jog-v4/patched.v

set b [ord::get_db_block]
set tech [[ord::get_db] getTech]
set f [open vias.tsv w]
foreach v [concat [$tech getVias] [$b getVias]] {foreach box [$v getBoxes] {puts $f "[$v getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"}}
close $f
