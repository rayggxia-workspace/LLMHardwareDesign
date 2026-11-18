read_db $::env(CU_SEED)/4_cts.odb
set b [ord::get_db_block]
set f [open removed-shared-hold.tsv w]
foreach name {hold97892 hold97893 hold97894} {
 set i [$b findInst $name]
 if {$i eq "NULL" || [[$i getMaster] getName] ne "CLKBUF_X1"} {error "Exact common path hold buffer mismatch $name"}
 set a [[$i findITerm A] getNet]
 set z [[$i findITerm Z] getNet]
 if {[llength [$z getBTerms]]} {error "Unexpected output port on removed hold net"}
 foreach it [$z getITerms] {if {$it ne [$i findITerm Z]} {$it connect $a}}
 puts $f "$name\t[$a getName]\t[$z getName]"
 odb::dbInst_destroy $i
 odb::dbNet_destroy $z
}
close $f
write_db unshared.odb