read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-805/tasks/revision300-final-source-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
set f [open pins.tsv w]
foreach p [[ord::get_db_block] getBTerms] {if {[$p getSigType] in {POWER GROUND}} {continue}; foreach pin [$p getBPins] {foreach b [$pin getBoxes] {puts $f "[$p getName]|[[$b getTechLayer] getName]|[$b xMin]|[$b yMin]|[$b xMax]|[$b yMax]"}}}
close $f
set f [open dbu.txt w]; puts $f [[ord::get_db_block] getDbUnitsPerMicron];close $f
