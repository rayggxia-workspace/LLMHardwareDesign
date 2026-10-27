read_db $::env(PINXY_ODB)
set out inputs/pin-use-r01/$::env(PINXY_CASE).tsv
if {[file exists $out]} {error "Output already exists $out"}
set f [open $out w];puts $f "pin\tdirection\tsig_type"
foreach t [[ord::get_db_block] getBTerms] {puts $f "[$t getName]\t[$t getIoType]\t[$t getSigType]"}
close $f
puts "PIN_USE_EXPORTED"
