set_thread_count 8
puts [info commands odb::*Access*]
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base/6_final.odb
set b [ord::get_db_block]
set inst [$b findInst {services.store.leaf}]
set it [$inst findITerm {req_data[74]}]
puts "TARGET $it"
set net [$it getNet]
set w [$net getWire]
puts "NET [$net getName] WIRE $w ID [$w getId]"
foreach method {getAccessPoints getPrefAccessPoint} {puts "$method [catch {$it $method} result] $result"}
write_def before.def
$w detach
puts "DETACHED [$net getWire] [$w getNet]"
$w attach $net
puts "ATTACHED [$net getWire] [$w getNet] ID [$w getId]"
write_def after.def
exec cmp before.def after.def
puts DETACH_ATTACH_EXACT_DEF_PASS
