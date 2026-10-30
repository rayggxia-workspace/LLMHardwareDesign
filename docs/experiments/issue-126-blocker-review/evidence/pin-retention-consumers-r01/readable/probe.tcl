read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/upper_adaptation_trial/r02/opentpu/placed_adapter_NOT_SYSTEM.odb}
set b [ord::get_db_block];set layer [[ord::get_db_tech] findLayer metal5]
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/pin_retention_consumers/r01/method_status.tsv} w];puts $f "method\tfailed\tmessage"
foreach method {POINT_PAIR NONZERO_ZEROEXT} {
 set n [odb::dbNet_create $b HPY_RETAIN_$method];set w [odb::dbWire_create $n]
 set enc [odb::dbWireEncoder];$enc begin $w;$enc newPath $layer ROUTED
 set failed [catch {
  if {$method eq "POINT_PAIR"} {$enc addPoint 200000 200000;$enc addPoint 200000 200000} else {$enc addPoint 239860 200000 0;$enc addPoint 240140 200000 0}
 } message];catch {$enc end}
 puts $f [join [list $method $failed [string map [list \n { | } \t { }] $message]] "\t"]
};close $f
set ::env(PINXY_ACCESS_NET_NAMES) {HPY_RETAIN_POINT_PAIR HPY_RETAIN_NONZERO_ZEROEXT}
set ::env(PINXY_ACCESS_OUT) {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/pin_retention_consumers/r01/native_shapes.tsv}
source {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/drivers/deadline-pin-retain-r01/export_access.tcl}
write_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/pin_retention_consumers/r01/probe_NOT_LEAF.odb}
write_def {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/pin_retention_consumers/r01/probe_NOT_LEAF.def}
write_abstract_lef -bloat_factor 0 {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/pin_retention_consumers/r01/probe_detailed.lef}
