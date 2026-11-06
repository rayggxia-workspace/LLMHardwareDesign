# The selected sink branch receives real delay cells before routing.
set block [ord::get_db_block]
set master [[ord::get_db] findMaster BUF_X1]
if {$master eq "NULL"} {error "BUF_X1 is absent"}
set inventory [open "$::env(RESULTS_DIR)/pu-hold-delay.tsv" w]
puts $inventory "endpoint\tinstance\told_net\tnew_net"
set counter 0
foreach {endpoint stages} $pu_hold_endpoints {
    set split [string last / $endpoint]
    if {$split < 1} {error "expected an instance input pin: $endpoint"}
    set instance [$block findInst [string range $endpoint 0 $split-1]]
    if {$instance eq "NULL"} {error "hold endpoint instance missing: $endpoint"}
    set pin [$instance findITerm [string range $endpoint $split+1 end]]
    if {$pin eq "NULL" || [[$pin getMTerm] getIoType] ne "INPUT"} {error "hold endpoint is not an input: $endpoint"}
    set net [$pin getNet]
    if {$net eq "NULL" || [$net getSigType] in {CLOCK POWER GROUND}} {error "invalid hold target net: $endpoint"}
    set anchor $instance
    if {[[$anchor getMaster] isBlock]} {
        set anchor ""
        foreach term [$net getITerms] {
            set driver [$term getInst]
            if {[[$term getMTerm] getIoType] eq "OUTPUT" && ![[$driver getMaster] isBlock]} {
                set anchor $driver
                break
            }
        }
        if {$anchor eq ""} {error "hold branch needs a standard-cell placement anchor: $endpoint"}
    }
    lassign [$anchor getLocation] x y
    set previous $net
    for {set stage 0} {$stage < $stages} {incr stage} {
        set name pu_endpoint_hold_[incr counter]
        set instance [odb::dbInst_create $block $master $name]
        set next [odb::dbNet_create $block ${name}_Z]
        $instance setLocation [expr {$x + $stage*[$master getWidth]}] $y
        $instance setOrient [$anchor getOrient]
        $instance setPlacementStatus PLACED
        [$instance findITerm A] connect $previous
        [$instance findITerm Z] connect $next
        set_dont_touch [get_cells $name]
        puts $inventory "$endpoint\t$name\t[$previous getName]\t[$next getName]"
        set previous $next
    }
    $pin disconnect
    $pin connect $previous
}
close $inventory
global_connect
detailed_placement_helper
check_placement -verbose
