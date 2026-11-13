# Run with an exact native ODB and a terminal-only TSV exported by the caller.
# Each input row is "<instance TAB master-terminal>" with no header.
read_db $::env(ITERM_ODB)
set b [ord::get_db_block]
source $::env(ITERM_GEOMETRY)
set d [$b getDieArea]
puts [join [list BLOCK [$b getName] [$b getDbUnitsPerMicron] [$d xMin] [$d yMin] [$d xMax] [$d yMax]] \t]
set seen {}
set input [open $::env(ITERM_LIST) r]
while {[gets $input line]>=0} {
    if {$line eq ""} {continue}
    set fields [split $line \t]
    if {[llength $fields]!=2 || [dict exists $seen $line]} {error "invalid or duplicate ITerm selector: $line"}
    dict set seen $line 1
    lassign $fields name pin
    if {$::env(ITERM_LEAF_BTERM) eq "1"} {
        set port [$b findBTerm $pin]
        if {$port eq "NULL" || [$port getNet] eq "NULL"} {error "missing independent native BTerm $pin"}
        foreach nt [[$port getNet] getITerms] {
            set mt [$nt getMTerm]
            puts [join [list LEAF_MEMBER [[$nt getInst] getName] [$mt getName] [$mt getIoType]] \t]
        }
        foreach bp [$port getBPins] {
            if {[$bp getPlacementStatus] ni {PLACED FIRM LOCKED COVER}} {continue}
            foreach box [$bp getBoxes] {
                if {[$box isVia]} {continue}
                puts [join [list LEAF_BTERM $pin [$port getIoType] [[$box getTechLayer] getName] \
                      [$box xMin] [$box yMin] [$box xMax] [$box yMax]] \t]
            }
        }
        continue
    }
    set inst [$b findInst $name]
    if {$inst eq "NULL"} {error "no exact ODB instance $name"}
    set it [$inst findITerm $pin]
    if {$it eq "NULL"} {error "no exact ODB ITerm $name/$pin"}
    set net [$it getNet]
    if {$net eq "NULL"} {error "unconnected ITerm $name/$pin"}
    set master [$inst getMaster]
    set term [$it getMTerm]
    lassign [$inst getOrigin] x y
    puts [join [list ENDPOINT $name $pin [$master getName] [$master getType] [$term getIoType] \
          [$net getName] [$net getSigType] [$inst getPlacementStatus] [$inst getOrient] $x $y] \t]
    foreach bt [$net getBTerms] {puts [join [list ALIAS $name $pin [$bt getName]] \t]}
    foreach nt [$net getITerms] {
        set m [$nt getMTerm]
        puts [join [list MEMBER $name $pin [[$nt getInst] getName] [$m getName] [$m getIoType]] \t]
    }
    foreach mp [$term getMPins] {
        foreach box [$mp getGeometry] {
            bvgeom::db_box stdout "$name/$pin" $box iterm-pin [$inst getTransform]
        }
    }
    set wire [$net getWire]
    if {$wire ne "NULL"} {
        set iter [odb::new_dbWirePathItr]
        set path [odb::new_dbWirePath]
        set shape [odb::new_dbWirePathShape]
        $iter begin $wire
        while {[$iter getNextPath $path]} {
            while {[$iter getNextShape $shape]} {
                bvgeom::wire_shape stdout "$name/$pin" [odb::dbWirePathShape_shape_get $shape]
            }
        }
        odb::delete_dbWirePathShape $shape
        odb::delete_dbWirePath $path
        odb::delete_dbWirePathItr $iter
    }
}
close $input
write_def $::env(ITERM_DEF_READBACK)
if {$::env(ITERM_LEAF_BTERM) eq "0"} {write_verilog $::env(ITERM_NETLIST_READBACK)}
