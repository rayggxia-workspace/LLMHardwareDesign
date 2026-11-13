# Read-only classification of the remaining pins from report_activity_annotation.
# Liberty power values are checked separately; a matching name alone is no proof.
proc audit_unannotated {db_path pins_path output_path} {
    read_db $db_path
    set block [ord::get_db_block]
    set file [open $pins_path r]
    set text [read $file]
    close $file
    set out [open $output_path w]
    set count 0
    foreach line [split $text "\n"] {
        if {![regexp {^ (.+)/([^/]+)$} $line -> name pin]} { continue }
        set instance [$block findInst $name]
        if {$instance eq "NULL" || $instance eq ""} {error "unmatched physical instance $name"}
        set master [$instance getMaster]
        set kind [$master getName]
        if {$kind ne "ANTENNA_X1" || $pin ne "A"} {error "unclassified physical pin $name/$pin ($kind)"}
        puts $out "$name/$pin $kind"
        incr count
    }
    close $out
    if {$count == 0} {error "no unannotated pins were inspected"}
    puts "PHYSICAL_UNANNOTATED_DIODE_COUNT $count"
}
