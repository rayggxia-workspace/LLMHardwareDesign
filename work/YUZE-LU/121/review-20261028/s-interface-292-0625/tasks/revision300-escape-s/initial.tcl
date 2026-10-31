set_thread_count 16
read_lef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-292/tasks/revision300-escape-s/technology/research12.tech.lef}
read_lef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-280/tasks/revision300-geometry-s/candidate.lef}
read_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-292/tasks/revision300-escape-s/upper.def}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-292/src/project/experiments/block_v1/odb_geometry.tcl}
set f [open /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-292/tasks/revision300-escape-s/initial-ports.tsv w]
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
bvgeom::export {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-292/tasks/revision300-escape-s/initial-geometry.tsv}
write_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-292/tasks/revision300-escape-s/upper.odb}
write_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-292/tasks/revision300-escape-s/upper-roundtrip.def}
