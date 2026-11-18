read_db /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt252/delivery/native/6_final.odb
set b [ord::get_db_block]
set tech [[ord::get_db] getTech]
set f [open leaf-layers.tsv w]
foreach l [$tech getLayers] {puts $f "[$l getName]\t[$l getWidth]"};close $f
set f [open leaf-vias.tsv w]
foreach v [concat [$tech getVias] [$b getVias]] {foreach box [$v getBoxes] {puts $f "[$v getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"}};close $f
write_def leaf-readback.def
