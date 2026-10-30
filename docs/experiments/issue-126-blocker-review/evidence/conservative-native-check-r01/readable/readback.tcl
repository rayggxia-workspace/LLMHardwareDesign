read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/upper_layer_probe/r01/model/research12.tech.lef}
read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef
read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_low_views/r01/p126_act.lef}
read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_low_views/r01/p126_mxu.lef}
read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_low_views/r01/p126_opentpu_aux.lef}
read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_low_views/r01/p126_gemm.lef}
read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_low_views/r01/p126_vector.lef}
read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_low_views/r01/p126_llaccel_aux.lef}
set m [[ord::get_db] findMaster {p126_act}];if {$m eq "NULL"} {error "Expected current macro missing"}
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/act.pins.tsv} w];puts $f "pin\tdirection\tuse\tlayer\tx0\ty0\tx1\ty1"
foreach mt [$m getMTerms] {foreach p [$mt getMPins] {foreach z [$p getGeometry] {puts $f [join [list [$mt getName] [$mt getIoType] [$mt getSigType] [[$z getTechLayer] getName] [$z xMin] [$z yMin] [$z xMax] [$z yMax]] "\t"]}}};close $f
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/act.OBS_counts.tsv} w];set counts [dict create];foreach z [$m getObstructions] {dict incr counts [[$z getTechLayer] getName]};dict for {layer n} $counts {puts $f "$layer\t$n"};close $f
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/act.size.tsv} w];puts $f [list [$m getWidth] [$m getHeight]];close $f

set m [[ord::get_db] findMaster {p126_mxu}];if {$m eq "NULL"} {error "Expected current macro missing"}
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/mxu.pins.tsv} w];puts $f "pin\tdirection\tuse\tlayer\tx0\ty0\tx1\ty1"
foreach mt [$m getMTerms] {foreach p [$mt getMPins] {foreach z [$p getGeometry] {puts $f [join [list [$mt getName] [$mt getIoType] [$mt getSigType] [[$z getTechLayer] getName] [$z xMin] [$z yMin] [$z xMax] [$z yMax]] "\t"]}}};close $f
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/mxu.OBS_counts.tsv} w];set counts [dict create];foreach z [$m getObstructions] {dict incr counts [[$z getTechLayer] getName]};dict for {layer n} $counts {puts $f "$layer\t$n"};close $f
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/mxu.size.tsv} w];puts $f [list [$m getWidth] [$m getHeight]];close $f

set m [[ord::get_db] findMaster {p126_opentpu_aux}];if {$m eq "NULL"} {error "Expected current macro missing"}
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/opentpu_aux.pins.tsv} w];puts $f "pin\tdirection\tuse\tlayer\tx0\ty0\tx1\ty1"
foreach mt [$m getMTerms] {foreach p [$mt getMPins] {foreach z [$p getGeometry] {puts $f [join [list [$mt getName] [$mt getIoType] [$mt getSigType] [[$z getTechLayer] getName] [$z xMin] [$z yMin] [$z xMax] [$z yMax]] "\t"]}}};close $f
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/opentpu_aux.OBS_counts.tsv} w];set counts [dict create];foreach z [$m getObstructions] {dict incr counts [[$z getTechLayer] getName]};dict for {layer n} $counts {puts $f "$layer\t$n"};close $f
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/opentpu_aux.size.tsv} w];puts $f [list [$m getWidth] [$m getHeight]];close $f

set m [[ord::get_db] findMaster {p126_gemm}];if {$m eq "NULL"} {error "Expected current macro missing"}
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/gemm.pins.tsv} w];puts $f "pin\tdirection\tuse\tlayer\tx0\ty0\tx1\ty1"
foreach mt [$m getMTerms] {foreach p [$mt getMPins] {foreach z [$p getGeometry] {puts $f [join [list [$mt getName] [$mt getIoType] [$mt getSigType] [[$z getTechLayer] getName] [$z xMin] [$z yMin] [$z xMax] [$z yMax]] "\t"]}}};close $f
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/gemm.OBS_counts.tsv} w];set counts [dict create];foreach z [$m getObstructions] {dict incr counts [[$z getTechLayer] getName]};dict for {layer n} $counts {puts $f "$layer\t$n"};close $f
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/gemm.size.tsv} w];puts $f [list [$m getWidth] [$m getHeight]];close $f

set m [[ord::get_db] findMaster {p126_vector}];if {$m eq "NULL"} {error "Expected current macro missing"}
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/vector.pins.tsv} w];puts $f "pin\tdirection\tuse\tlayer\tx0\ty0\tx1\ty1"
foreach mt [$m getMTerms] {foreach p [$mt getMPins] {foreach z [$p getGeometry] {puts $f [join [list [$mt getName] [$mt getIoType] [$mt getSigType] [[$z getTechLayer] getName] [$z xMin] [$z yMin] [$z xMax] [$z yMax]] "\t"]}}};close $f
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/vector.OBS_counts.tsv} w];set counts [dict create];foreach z [$m getObstructions] {dict incr counts [[$z getTechLayer] getName]};dict for {layer n} $counts {puts $f "$layer\t$n"};close $f
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/vector.size.tsv} w];puts $f [list [$m getWidth] [$m getHeight]];close $f

set m [[ord::get_db] findMaster {p126_llaccel_aux}];if {$m eq "NULL"} {error "Expected current macro missing"}
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/llaccel_aux.pins.tsv} w];puts $f "pin\tdirection\tuse\tlayer\tx0\ty0\tx1\ty1"
foreach mt [$m getMTerms] {foreach p [$mt getMPins] {foreach z [$p getGeometry] {puts $f [join [list [$mt getName] [$mt getIoType] [$mt getSigType] [[$z getTechLayer] getName] [$z xMin] [$z yMin] [$z xMax] [$z yMax]] "\t"]}}};close $f
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/llaccel_aux.OBS_counts.tsv} w];set counts [dict create];foreach z [$m getObstructions] {dict incr counts [[$z getTechLayer] getName]};dict for {layer n} $counts {puts $f "$layer\t$n"};close $f
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_conservative_native_check/r01/llaccel_aux.size.tsv} w];puts $f [list [$m getWidth] [$m getHeight]];close $f

