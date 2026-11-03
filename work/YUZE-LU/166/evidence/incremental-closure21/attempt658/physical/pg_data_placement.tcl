set block [ord::get_db_block]
set pg_before [dict create]
foreach inst [$block getInsts] {dict set pg_before [$inst getName] [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]}
set inst [$block findInst {r166_hold_endpoint_extracted_0000225214}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {CLKBUF_X1} || [$inst getLocation] ne {187720 380800} || [$inst getOrient] ne {MX}} {error "Measured PG data buffer differs from GRT checkpoint"}
$inst setPlacementStatus PLACED
$inst setLocation 187720 386400
$inst setPlacementStatus LOCKED
set inst [$block findInst {r166_hold_endpoint_extracted_0000325215}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {CLKBUF_X1} || [$inst getLocation] ne {186580 380800} || [$inst getOrient] ne {MX}} {error "Measured PG data buffer differs from GRT checkpoint"}
$inst setPlacementStatus PLACED
$inst setLocation 188860 386400
$inst setPlacementStatus LOCKED
set inst [$block findInst {r166_hold_endpoint_extracted_0001825230}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {CLKBUF_X1} || [$inst getLocation] ne {3306380 828800} || [$inst getOrient] ne {MX}} {error "Measured PG data buffer differs from GRT checkpoint"}
$inst setPlacementStatus PLACED
$inst setLocation 3306380 834400
$inst setPlacementStatus LOCKED
set inst [$block findInst {r166_hold_endpoint_extracted_0001925231}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {CLKBUF_X1} || [$inst getLocation] ne {3305240 828800} || [$inst getOrient] ne {MX}} {error "Measured PG data buffer differs from GRT checkpoint"}
$inst setPlacementStatus PLACED
$inst setLocation 3305240 834400
$inst setPlacementStatus LOCKED
set net [$block findNet {state_store.local_read\[0\][46]}]
if {$net eq "NULL" || [$net getSigType] in {CLOCK POWER GROUND}} {error "Measured PG reroute is not an existing data net"}
set wire [$net getWire]
if {$wire eq "NULL"} {error "Measured original colliding data wire missing"}
odb::dbWire_destroy $wire
check_placement -verbose
foreach inst [$block getInsts] {
 set name [$inst getName];set now [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]
 if {$now ne [dict get $pg_before $name] && [lsearch -exact {r166_hold_endpoint_extracted_0000225214 r166_hold_endpoint_extracted_0000325215 r166_hold_endpoint_extracted_0001825230 r166_hold_endpoint_extracted_0001925231} $name]<0} {error "Unselected original cell changed during PG placement ECO"}
}
puts "R166_MEASURED_PG_DATA_PLACEMENT; moved=4; other_cells_unchanged=1; post_eco_timing_qualified=0"
