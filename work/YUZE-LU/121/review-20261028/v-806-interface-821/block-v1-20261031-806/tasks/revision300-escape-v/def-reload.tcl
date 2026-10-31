set_thread_count 16
read_lef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-806/tasks/revision300-escape-v/technology/research12.tech.lef}
read_lef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-805/tasks/revision300-geometry-v/candidate.lef}
read_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-806/tasks/revision300-escape-v/upper-roundtrip.def}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-806/src/project/experiments/block_v1/odb_geometry.tcl}
set f [open /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-806/tasks/revision300-escape-v/def-reload-ports.tsv w]
set block [ord::get_db_block]
if {[llength [$block getInsts]] != 1} {error "Expected one frozen macro"}
foreach term [$block getBTerms] {
 set name [$term getName];set net [$term getNet]
 if {[$net getName] ne $name || [llength [$net getITerms]] != 1 || [llength [$net getBTerms]] != 1} {error "Port identity/count mismatch"}
 set inner [lindex [$net getITerms] 0]
 if {[[$inner getInst] getName] ne "LEAF" || [[$inner getMTerm] getName] ne $name} {error "Wrong macro bit"}
 puts $f "$name\t[$term getIoType]\t[$term getSigType]"
}
close $f
bvgeom::export {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-806/tasks/revision300-escape-v/def-reload-geometry.tsv}
