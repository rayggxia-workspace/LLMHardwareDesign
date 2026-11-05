set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-internal-drive-02/candidate-1182/flow/results/nangate45/bv1_block_feed_s_macro/base/6_final.odb}
set f [open {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-internal-drive-02/candidate-1182/strong-driver-audit.tsv} w]

foreach port [[ord::get_db_block] getBTerms] {
 if {[$port getSigType] in {POWER GROUND} || [$port getIoType] ne "OUTPUT"} {continue}
 set drivers {}
 foreach term [[$port getNet] getITerms] {
  if {[[$term getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $term}
 }
 if {[llength $drivers]!=1} {error "Actual output driver count"}
 set term [lindex $drivers 0];set inst [$term getInst];set master [[$inst getMaster] getName]
 if {$master ne "BUF_X32" || ![string match control_output_driver_* [$inst getName]]} {error "Strong output stage was replaced"}
 puts $f "[$port getName]\t[$inst getName]\t$master\t[[$term getMTerm] getName]"
}
close $f
