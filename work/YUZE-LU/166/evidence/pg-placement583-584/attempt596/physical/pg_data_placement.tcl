set block [ord::get_db_block]
set pg_before [dict create]
foreach inst [$block getInsts] {dict set pg_before [$inst getName] [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]}
set inst [$block findInst {$abc$862551$auto$blifparse.cc:397:parse_blif$872786}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {MUX2_X1} || [$inst getLocation] ne {3537040 414400} || [$inst getOrient] ne {MX}} {error "Measured PG data buffer differs from GRT checkpoint"}
$inst setPlacementStatus PLACED
$inst setLocation 3533240 420000
$inst setPlacementStatus LOCKED
set inst [$block findInst {r166_hold_endpoint_extracted_0000525029}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {CLKBUF_X1} || [$inst getLocation] ne {176320 2234400} || [$inst getOrient] ne {MX}} {error "Measured PG data buffer differs from GRT checkpoint"}
$inst setPlacementStatus PLACED
$inst setLocation 174420 2228800
$inst setPlacementStatus LOCKED
set inst [$block findInst {r166_hold_endpoint_extracted_0000625030}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {CLKBUF_X1} || [$inst getLocation] ne {175180 2234400} || [$inst getOrient] ne {MX}} {error "Measured PG data buffer differs from GRT checkpoint"}
$inst setPlacementStatus PLACED
$inst setLocation 173280 2228800
$inst setPlacementStatus LOCKED
set inst [$block findInst {r166_hold_endpoint_extracted_0001125035}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {CLKBUF_X1} || [$inst getLocation] ne {320720 2713200} || [$inst getOrient] ne {R0}} {error "Measured PG data buffer differs from GRT checkpoint"}
$inst setPlacementStatus PLACED
$inst setLocation 320720 2718800
$inst setPlacementStatus LOCKED
set inst [$block findInst {r166_hold_endpoint_extracted_0001225036}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {CLKBUF_X1} || [$inst getLocation] ne {319580 2713200} || [$inst getOrient] ne {R0}} {error "Measured PG data buffer differs from GRT checkpoint"}
$inst setPlacementStatus PLACED
$inst setLocation 319580 2718800
$inst setPlacementStatus LOCKED
set inst [$block findInst {r166_hold_endpoint_extracted_0001325037}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {CLKBUF_X1} || [$inst getLocation] ne {604960 2685200} || [$inst getOrient] ne {R0}} {error "Measured PG data buffer differs from GRT checkpoint"}
$inst setPlacementStatus PLACED
$inst setLocation 604960 2690800
$inst setPlacementStatus LOCKED
set inst [$block findInst {r166_hold_endpoint_extracted_0001425038}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {CLKBUF_X1} || [$inst getLocation] ne {603820 2685200} || [$inst getOrient] ne {R0}} {error "Measured PG data buffer differs from GRT checkpoint"}
$inst setPlacementStatus PLACED
$inst setLocation 603820 2690800
$inst setPlacementStatus LOCKED
set inst [$block findInst {wire15352}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {BUF_X4} || [$inst getLocation] ne {3187060 3323600} || [$inst getOrient] ne {R0}} {error "Measured PG data buffer differs from GRT checkpoint"}
$inst setPlacementStatus PLACED
$inst setLocation 3190100 3329200
$inst setPlacementStatus LOCKED
set inst [$block findInst {wire24916}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {BUF_X4} || [$inst getLocation] ne {1037780 1363600} || [$inst getOrient] ne {R0}} {error "Measured PG data buffer differs from GRT checkpoint"}
$inst setPlacementStatus PLACED
$inst setLocation 1025620 1369200
$inst setPlacementStatus LOCKED
set inst [$block findInst {wire25152}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {BUF_X1} || [$inst getLocation] ne {1131640 949200} || [$inst getOrient] ne {R0}} {error "Measured PG data buffer differs from GRT checkpoint"}
$inst setPlacementStatus PLACED
$inst setLocation 1125940 954800
$inst setPlacementStatus LOCKED
check_placement -verbose
foreach inst [$block getInsts] {
 set name [$inst getName];set now [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]
 if {$now ne [dict get $pg_before $name] && [lsearch -exact {$abc$862551$auto$blifparse.cc:397:parse_blif$872786 r166_hold_endpoint_extracted_0000525029 r166_hold_endpoint_extracted_0000625030 r166_hold_endpoint_extracted_0001125035 r166_hold_endpoint_extracted_0001225036 r166_hold_endpoint_extracted_0001325037 r166_hold_endpoint_extracted_0001425038 wire15352 wire24916 wire25152} $name]<0} {error "Unselected original cell changed during PG placement ECO"}
}
puts "R166_MEASURED_PG_DATA_PLACEMENT; moved=10; other_cells_unchanged=1; post_eco_timing_qualified=0"
