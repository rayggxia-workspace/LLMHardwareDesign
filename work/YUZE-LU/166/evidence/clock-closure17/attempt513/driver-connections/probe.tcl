set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt491/physical/flow/results/nangate45/r166_1024/base/r166_grt_closure-round0.odb}
set b [ord::get_db_block]
set f [open connections.tsv w]
set inst [$b findInst {wire25134}]
if {$inst eq "NULL"} {error "Measured driver missing"}
set p [$inst findITerm {Z}]
if {$p eq "NULL"} {error "Measured driver pin missing"}
set net [$p getNet]
if {$net eq "NULL"} {error "Measured driver net missing"}
set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
puts $f [join [list DRIVER [$inst getName] [[$inst getMaster] getName] [[$p getMTerm] getName] [$net getName] [$net getSigType] [$inst getPlacementStatus] [$inst getLocation] $group] "	"]
foreach term [$net getITerms] {
 set cell [$term getInst];set master [$cell getMaster];set mt [$term getMTerm];set group [$cell getGroup]
 if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list TERM [$cell getName] [$master getName] [$mt getName] [$mt getIoType] [$cell getPlacementStatus] [$cell getLocation] $group] "	"]
}
foreach term [$net getBTerms] {puts $f [join [list PORT [$term getName] [$term getIoType]] "	"]}
set inst [$b findInst {wire25196}]
if {$inst eq "NULL"} {error "Measured driver missing"}
set p [$inst findITerm {Z}]
if {$p eq "NULL"} {error "Measured driver pin missing"}
set net [$p getNet]
if {$net eq "NULL"} {error "Measured driver net missing"}
set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
puts $f [join [list DRIVER [$inst getName] [[$inst getMaster] getName] [[$p getMTerm] getName] [$net getName] [$net getSigType] [$inst getPlacementStatus] [$inst getLocation] $group] "	"]
foreach term [$net getITerms] {
 set cell [$term getInst];set master [$cell getMaster];set mt [$term getMTerm];set group [$cell getGroup]
 if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list TERM [$cell getName] [$master getName] [$mt getName] [$mt getIoType] [$cell getPlacementStatus] [$cell getLocation] $group] "	"]
}
foreach term [$net getBTerms] {puts $f [join [list PORT [$term getName] [$term getIoType]] "	"]}
close $f
