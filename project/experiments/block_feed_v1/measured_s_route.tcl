# Exact single-net M10 detour replacement. Source DEF and all other geometry are checked by routed_repair.py.
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set net [$block findNet {dout[58]}]
if {$net eq "NULL"} {error "Missing exact target net"}
write_def before3-odb.def
odb::dbWire_destroy [$net getWire]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1756990 848140
odb::dbWireEncoder_addPoint $enc 1760190 848140
odb::dbWireEncoder_addPoint $enc 1760190 840140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1756990 848140
odb::dbWireEncoder_addPoint $enc 1761790 848140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 1760830 848140
odb::dbWireEncoder_addPoint $enc 1761790 848140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 1760830 847420
odb::dbWireEncoder_addPoint $enc 1760830 848140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1760830 839300
odb::dbWireEncoder_addPoint $enc 1760830 847420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1759590 839300
odb::dbWireEncoder_addPoint $enc 1760830 839300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1756990 848140
set via [$tech findVia via9_0]
if {$via ne "NULL"} {odb::dbWireEncoder_addTechVia $enc $via} else {set via [$block findVia via9_0]; if {$via eq "NULL"} {error "Missing actual via"}; odb::dbWireEncoder_addVia $enc $via}
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 1761790 848140
set via [$tech findVia via7_0]
if {$via ne "NULL"} {odb::dbWireEncoder_addTechVia $enc $via} else {set via [$block findVia via7_0]; if {$via eq "NULL"} {error "Missing actual via"}; odb::dbWireEncoder_addVia $enc $via}
odb::dbWireEncoder_newPath $enc [$tech findLayer metal8] ROUTED
odb::dbWireEncoder_addPoint $enc 1761790 848140
set via [$tech findVia via8_0]
if {$via ne "NULL"} {odb::dbWireEncoder_addTechVia $enc $via} else {set via [$block findVia via8_0]; if {$via eq "NULL"} {error "Missing actual via"}; odb::dbWireEncoder_addVia $enc $via}
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 1760830 848140
set via [$tech findVia via6_0]
if {$via ne "NULL"} {odb::dbWireEncoder_addTechVia $enc $via} else {set via [$block findVia via6_0]; if {$via eq "NULL"} {error "Missing actual via"}; odb::dbWireEncoder_addVia $enc $via}
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1760830 847420
set via [$tech findVia via4_0]
if {$via ne "NULL"} {odb::dbWireEncoder_addTechVia $enc $via} else {set via [$block findVia via4_0]; if {$via eq "NULL"} {error "Missing actual via"}; odb::dbWireEncoder_addVia $enc $via}
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1760830 847420
set via [$tech findVia via5_0]
if {$via ne "NULL"} {odb::dbWireEncoder_addTechVia $enc $via} else {set via [$block findVia via5_0]; if {$via eq "NULL"} {error "Missing actual via"}; odb::dbWireEncoder_addVia $enc $via}
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1760830 839300
set via [$tech findVia via3_2]
if {$via ne "NULL"} {odb::dbWireEncoder_addTechVia $enc $via} else {set via [$block findVia via3_2]; if {$via eq "NULL"} {error "Missing actual via"}; odb::dbWireEncoder_addVia $enc $via}
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1759590 839300
set via [$tech findVia via1_4]
if {$via ne "NULL"} {odb::dbWireEncoder_addTechVia $enc $via} else {set via [$block findVia via1_4]; if {$via eq "NULL"} {error "Missing actual via"}; odb::dbWireEncoder_addVia $enc $via}
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1759590 839300
set via [$tech findVia via2_5]
if {$via ne "NULL"} {odb::dbWireEncoder_addTechVia $enc $via} else {set via [$block findVia via2_5]; if {$via eq "NULL"} {error "Missing actual via"}; odb::dbWireEncoder_addVia $enc $via}
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
