read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef
read_lef /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/lef-refinement-001/bank.lef
set master [[ord::get_db] findMaster s_sram_256x128_freepdk45]
set f [open /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/lef-refinement-001/native-m4.tsv w]
foreach box [$master getObstructions] {
 if {[[$box getTechLayer] getName] eq "metal4"} {puts $f "[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"}
}
close $f
exit
