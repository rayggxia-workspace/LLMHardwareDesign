read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_pin_retention/r01/routed.odb}
if {[[ord::get_db_block] getDbUnitsPerMicron]!=2000} {error "Source units differ from verified model"}
set ::env(PINXY_PATCH_OUT) {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/native_patch_audit/r03/llaccel_13093/patch_rectangles.tsv}
set ::env(PINXY_PATCH_COUNTS) {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/native_patch_audit/r03/llaccel_13093/patch_counts.tsv}
source {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/drivers/deadline-ll13093-rect-r03/export_patch_rects.tcl}
