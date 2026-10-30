set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-598/tasks/revision300-v-geometry-compose/composed-candidate.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set v [$tech findVia via1_4];set seen {}
foreach part [$v getBoxes] {set layer [[$part getTechLayer] getName];if {[string match metal* $layer]} {lappend seen $layer}}
if {[lsort -unique $seen] ne [lsort [list metal1 metal2]]} {error "Via layers mismatch"}
set v [$tech findVia via1_7];set seen {}
foreach part [$v getBoxes] {set layer [[$part getTechLayer] getName];if {[string match metal* $layer]} {lappend seen $layer}}
if {[lsort -unique $seen] ne [lsort [list metal1 metal2]]} {error "Via layers mismatch"}
set v [$tech findVia via2_5];set seen {}
foreach part [$v getBoxes] {set layer [[$part getTechLayer] getName];if {[string match metal* $layer]} {lappend seen $layer}}
if {[lsort -unique $seen] ne [lsort [list metal2 metal3]]} {error "Via layers mismatch"}
set v [$tech findVia via3_2];set seen {}
foreach part [$v getBoxes] {set layer [[$part getTechLayer] getName];if {[string match metal* $layer]} {lappend seen $layer}}
if {[lsort -unique $seen] ne [lsort [list metal3 metal4]]} {error "Via layers mismatch"}
set wanted [dict create]
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313834313634}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323938343434}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333735363238}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333833353030}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3133373830}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3136373931}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e36333735}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {66756e6374696f6e5f756e69742e66726163315b305d5b375d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3133375d5b31315d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3134315d5b32335d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3233375d5b32355d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b34385d5b31345d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b36385d5b32325d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313034333430}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e6574313731383737}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743732323435}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743737313131}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743738383335}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743830323338}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743832333832}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743834373633}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743835313136}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743836393738}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743838363530}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743838383332}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743935323630}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743938333837}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f706572616e645f625b325d5b335d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3131395d5b32315d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3137325d5b32315d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3139395d5b315d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3231395d5b33305d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b38395d5b32305d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {706f696e745f726f756e6465645b325d5b36395d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {706f696e745f746f74616c5b375d5b375d}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {746f705f6e5b345d}]] 1
set selected [dict create]
foreach net [$block getNets] {set name [string map [list [format %c 92] {}] [$net getName]];if {[dict exists $wanted $name]} {if {[dict exists $selected $name]} {error "Ambiguous target"};dict set selected $name $net}}
if {[dict size $selected] != 36} {error "Missing target"}
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313834313634}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2413950 401100
odb::dbWireEncoder_addPoint $enc 2417750 401100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2413950 401100
odb::dbWireEncoder_addPoint $enc 2413950 401380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2417370 399140
odb::dbWireEncoder_addPoint $enc 2417370 401100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2417750 401100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2413950 401100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2413950 401380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2417370 399140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2417370 401100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2417750 401100
odb::dbWireEncoder_addPoint $enc 2417370 401100
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e323938343434}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2084490 1035580
odb::dbWireEncoder_addPoint $enc 2084870 1035580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2084490 1035580
odb::dbWireEncoder_addPoint $enc 2084490 1036980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2084490 1036980
odb::dbWireEncoder_addPoint $enc 2084870 1036980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2084870 1039220
odb::dbWireEncoder_addPoint $enc 2085250 1039220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2085250 1039220
odb::dbWireEncoder_addPoint $enc 2085250 1039500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2085250 1039500
odb::dbWireEncoder_addPoint $enc 2085630 1039500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2085630 1039500
odb::dbWireEncoder_addPoint $enc 2085630 1043140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2084870 1036980
odb::dbWireEncoder_addPoint $enc 2084870 1039220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2084870 1035580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2085630 1039500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2085630 1043140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2085630 1043140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2085630 1043140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2085630 1039500
odb::dbWireEncoder_addPoint $enc 2085250 1039500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2085630 1039500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333735363238}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1508410 2000740
odb::dbWireEncoder_addPoint $enc 1508410 2001300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1506510 2001300
odb::dbWireEncoder_addPoint $enc 1508410 2001300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1569310 2050860
odb::dbWireEncoder_addPoint $enc 1569310 2051420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1834450 1997660
odb::dbWireEncoder_addPoint $enc 1834750 1997660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1827230 1995140
odb::dbWireEncoder_addPoint $enc 1827230 1997660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1827230 1997660
odb::dbWireEncoder_addPoint $enc 1834450 1997660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1825230 1997380
odb::dbWireEncoder_addPoint $enc 1825230 1997660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1825230 1997660
odb::dbWireEncoder_addPoint $enc 1827230 1997660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1904370 1997100
odb::dbWireEncoder_addPoint $enc 1904370 1997660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1904370 1997100
odb::dbWireEncoder_addPoint $enc 1904750 1997100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1888030 1994860
odb::dbWireEncoder_addPoint $enc 1888510 1994860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1888510 1993740
odb::dbWireEncoder_addPoint $enc 1888510 1994860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1888510 1993740
odb::dbWireEncoder_addPoint $enc 1904750 1993740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1904750 1993740
odb::dbWireEncoder_addPoint $enc 1904750 1997100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1506510 2001300
odb::dbWireEncoder_addPoint $enc 1506510 2006400
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1506130 2006400
odb::dbWireEncoder_addPoint $enc 1506510 2006400
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1506130 2006400
odb::dbWireEncoder_addPoint $enc 1506130 2008860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1506130 2008860
odb::dbWireEncoder_addPoint $enc 1506510 2008860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1506510 2008860
odb::dbWireEncoder_addPoint $enc 1506510 2012220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1506510 2012220
odb::dbWireEncoder_addPoint $enc 1506590 2012220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1506590 2012220
odb::dbWireEncoder_addPoint $enc 1506590 2050860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1686250 2037420
odb::dbWireEncoder_addPoint $enc 1686250 2041900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1686250 2041900
odb::dbWireEncoder_addPoint $enc 1686250 2050020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1738310 2036860
odb::dbWireEncoder_addPoint $enc 1740110 2036860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1740110 2021740
odb::dbWireEncoder_addPoint $enc 1740110 2036860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1740210 2036580
odb::dbWireEncoder_addPoint $enc 1740210 2036720
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1740210 2036580
odb::dbWireEncoder_addPoint $enc 1740210 2036860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1740110 2036860
odb::dbWireEncoder_addPoint $enc 1740210 2036860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1391370 2000740
odb::dbWireEncoder_addPoint $enc 1395150 2000740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1467750 2049740
odb::dbWireEncoder_addPoint $enc 1467750 2051140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1465470 2051140
odb::dbWireEncoder_addPoint $enc 1467750 2051140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1458250 2048060
odb::dbWireEncoder_addPoint $enc 1458250 2051140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1458250 2051140
odb::dbWireEncoder_addPoint $enc 1465470 2051140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1467750 2049740
odb::dbWireEncoder_addPoint $enc 1506590 2049740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1549830 2050860
odb::dbWireEncoder_addPoint $enc 1549830 2051140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1549710 2050860
odb::dbWireEncoder_addPoint $enc 1549830 2050860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1562750 2051140
odb::dbWireEncoder_addPoint $enc 1562750 2051420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1549830 2051420
odb::dbWireEncoder_addPoint $enc 1562750 2051420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1549830 2051140
odb::dbWireEncoder_addPoint $enc 1549830 2051420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1506590 2050860
odb::dbWireEncoder_addPoint $enc 1549710 2050860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1562750 2051420
odb::dbWireEncoder_addPoint $enc 1569310 2051420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1569310 2050860
odb::dbWireEncoder_addPoint $enc 1607400 2050860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1647300 2050020
odb::dbWireEncoder_addPoint $enc 1686250 2050020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1607400 2050300
odb::dbWireEncoder_addPoint $enc 1607400 2050860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1607400 2050300
odb::dbWireEncoder_addPoint $enc 1647300 2050300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1647300 2050020
odb::dbWireEncoder_addPoint $enc 1647300 2050300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1778590 1997380
odb::dbWireEncoder_addPoint $enc 1778590 1997660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1777830 1995140
odb::dbWireEncoder_addPoint $enc 1777830 1997380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1777830 1997380
odb::dbWireEncoder_addPoint $enc 1778590 1997380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1772590 1997380
odb::dbWireEncoder_addPoint $enc 1777830 1997380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1778590 1997380
odb::dbWireEncoder_addPoint $enc 1825230 1997380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1852110 1993740
odb::dbWireEncoder_addPoint $enc 1852110 1997660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1851550 1997660
odb::dbWireEncoder_addPoint $enc 1852110 1997660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1834750 1997660
odb::dbWireEncoder_addPoint $enc 1852110 1997660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1852110 1993740
odb::dbWireEncoder_addPoint $enc 1888510 1993740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1938350 1995140
odb::dbWireEncoder_addPoint $enc 1938350 1997100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1938350 1995140
odb::dbWireEncoder_addPoint $enc 1942750 1995140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1904750 1997100
odb::dbWireEncoder_addPoint $enc 1938350 1997100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1400490 2032940
odb::dbWireEncoder_addPoint $enc 1400490 2036860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1399730 2032940
odb::dbWireEncoder_addPoint $enc 1400490 2032940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1399730 2023140
odb::dbWireEncoder_addPoint $enc 1399730 2032940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1395150 2023140
odb::dbWireEncoder_addPoint $enc 1399730 2023140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1400490 2036860
odb::dbWireEncoder_addPoint $enc 1400490 2043020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1395150 2000740
odb::dbWireEncoder_addPoint $enc 1395150 2023140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1458250 2046300
odb::dbWireEncoder_addPoint $enc 1458250 2048060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1457870 2043020
odb::dbWireEncoder_addPoint $enc 1457870 2046300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1457870 2046300
odb::dbWireEncoder_addPoint $enc 1458250 2046300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1400490 2043020
odb::dbWireEncoder_addPoint $enc 1457870 2043020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1727100 2036860
odb::dbWireEncoder_addPoint $enc 1738310 2036860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1727100 2036860
odb::dbWireEncoder_addPoint $enc 1727100 2037420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1686250 2037420
odb::dbWireEncoder_addPoint $enc 1727100 2037420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1740110 2021740
odb::dbWireEncoder_addPoint $enc 1772590 2021740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1772590 1997380
odb::dbWireEncoder_addPoint $enc 1772590 2021740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1508410 2000740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1506590 2050860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1506590 2049740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1686250 2050020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1834450 1997660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1834450 1997660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1834750 1997660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1834750 1997660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1827230 1995140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1827230 1997660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1904370 1997660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1904750 1997100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1904750 1997100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1888030 1994860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1888030 1994860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1888510 1994860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1888510 1993740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1904750 1993740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1506510 2012220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1506590 2012220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1686250 2041900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1686250 2037420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1738310 2036860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1738310 2036860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1740110 2036860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1740110 2021740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1740210 2036720
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1740210 2036580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1395150 2000740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1391370 2000740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1391370 2000740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1467750 2051140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1467750 2049740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1465470 2051140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1465470 2051140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1467750 2051140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1458250 2048060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1458250 2051140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1549830 2051140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1549830 2050860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1549710 2050860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1549710 2050860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1562750 2051140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1562750 2051420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1549830 2051420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1778590 1997660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1778590 1997380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1777830 1995140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1777830 1997380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1772590 1997380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1852110 1997660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1852110 1993740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1851550 1997660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1851550 1997660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1852110 1997660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1938350 1997100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1938350 1995140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1942750 1995140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1942750 1995140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1400490 2036860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1399730 2023140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1395150 2023140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1400490 2043020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1457870 2043020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1772590 2021740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1904750 1997100
odb::dbWireEncoder_addPoint $enc 1904370 1997100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1904750 1997100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e333833353030}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2010390 1278900
odb::dbWireEncoder_addPoint $enc 2010770 1278900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2010770 1278900
odb::dbWireEncoder_addPoint $enc 2010770 1280860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2010390 1278900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2010770 1278900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2010770 1280860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2010390 1278900
odb::dbWireEncoder_addPoint $enc 2010770 1278900
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3133373830}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2291210 1807260
odb::dbWireEncoder_addPoint $enc 2296530 1807260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2287410 1801800
odb::dbWireEncoder_addPoint $enc 2287410 1801940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2286110 1801940
odb::dbWireEncoder_addPoint $enc 2287410 1801940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2290830 1801940
odb::dbWireEncoder_addPoint $enc 2290830 1804740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2287410 1801940
odb::dbWireEncoder_addPoint $enc 2290830 1801940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2290830 1805860
odb::dbWireEncoder_addPoint $enc 2291210 1805860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2290830 1804740
odb::dbWireEncoder_addPoint $enc 2290830 1805860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2291210 1805860
odb::dbWireEncoder_addPoint $enc 2291210 1807260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2285890 1753500
odb::dbWireEncoder_addPoint $enc 2285890 1753780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2285550 1753500
odb::dbWireEncoder_addPoint $enc 2285890 1753500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2285550 1731940
odb::dbWireEncoder_addPoint $enc 2285550 1753500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2285510 1731940
odb::dbWireEncoder_addPoint $enc 2285550 1731940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2285550 1753500
odb::dbWireEncoder_addPoint $enc 2286110 1753500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2286110 1753500
odb::dbWireEncoder_addPoint $enc 2286110 1801940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2291210 1807260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2296530 1807260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2296530 1807260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2287410 1801800
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2287410 1801940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2286110 1801940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2290830 1804740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2290830 1801940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2285890 1753780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2285550 1753500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2285550 1731940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2285510 1731940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2285510 1731940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2285550 1753500
odb::dbWireEncoder_addPoint $enc 2285890 1753500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2285550 1753500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3136373931}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2440930 2145780
odb::dbWireEncoder_addPoint $enc 2441310 2145780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2441310 2143540
odb::dbWireEncoder_addPoint $enc 2441310 2145780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2441310 2143540
odb::dbWireEncoder_addPoint $enc 2441690 2143540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2441690 2132060
odb::dbWireEncoder_addPoint $enc 2441690 2143540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2440930 2152500
odb::dbWireEncoder_addPoint $enc 2441230 2152500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2441230 2152500
odb::dbWireEncoder_addPoint $enc 2441230 2156980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2441230 2156980
odb::dbWireEncoder_addPoint $enc 2441310 2156980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2440930 2145780
odb::dbWireEncoder_addPoint $enc 2440930 2152500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2441690 2132060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2441230 2152500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2441230 2156980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2441310 2156980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2441310 2156980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2441230 2152500
odb::dbWireEncoder_addPoint $enc 2440930 2152500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2441230 2152500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e36333735}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2350110 1208340
odb::dbWireEncoder_addPoint $enc 2352770 1208340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2350110 1216740
odb::dbWireEncoder_addPoint $enc 2350110 1217300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2350110 1217300
odb::dbWireEncoder_addPoint $enc 2350490 1217300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2350490 1217300
odb::dbWireEncoder_addPoint $enc 2350490 1218700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2350490 1218700
odb::dbWireEncoder_addPoint $enc 2352390 1218700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2352390 1218700
odb::dbWireEncoder_addPoint $enc 2352390 1222900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2352390 1222900
odb::dbWireEncoder_addPoint $enc 2352770 1222900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2352770 1222900
odb::dbWireEncoder_addPoint $enc 2352770 1238020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2350110 1206940
odb::dbWireEncoder_addPoint $enc 2350110 1216740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2352770 1208340
odb::dbWireEncoder_addPoint $enc 2352770 1211140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2342510 1190140
odb::dbWireEncoder_addPoint $enc 2342890 1190140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2342890 1183140
odb::dbWireEncoder_addPoint $enc 2342890 1190140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2342130 1207220
odb::dbWireEncoder_addPoint $enc 2342130 1208060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2342130 1207220
odb::dbWireEncoder_addPoint $enc 2342510 1207220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2342510 1198820
odb::dbWireEncoder_addPoint $enc 2342510 1207220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1198820
odb::dbWireEncoder_addPoint $enc 2342510 1198820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1194900
odb::dbWireEncoder_addPoint $enc 2342110 1198820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1194900
odb::dbWireEncoder_addPoint $enc 2342510 1194900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2342510 1190140
odb::dbWireEncoder_addPoint $enc 2342510 1194900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2342510 1206940
odb::dbWireEncoder_addPoint $enc 2350110 1206940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2350110 1206940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2352770 1208340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2350110 1208340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2350110 1216740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2350490 1218700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2352390 1218700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2352770 1238020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2352770 1211140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2342890 1183140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2342130 1208060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2342510 1198820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1198820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1194900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2342510 1206940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1194900
odb::dbWireEncoder_addPoint $enc 2342510 1194900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1194900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {66756e6374696f6e5f756e69742e66726163315b305d5b375d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2329970 1514100
odb::dbWireEncoder_addPoint $enc 2330350 1514100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2330350 1514100
odb::dbWireEncoder_addPoint $enc 2330350 1514380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2330350 1513540
odb::dbWireEncoder_addPoint $enc 2330350 1514100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2330350 1625260
odb::dbWireEncoder_addPoint $enc 2330350 1642060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2330350 1642060
odb::dbWireEncoder_addPoint $enc 2346590 1642060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2346590 1642060
odb::dbWireEncoder_addPoint $enc 2346590 1642620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2330350 1514380
odb::dbWireEncoder_addPoint $enc 2330350 1625260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2346590 1710380
odb::dbWireEncoder_addPoint $enc 2348830 1710380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2348830 1710380
odb::dbWireEncoder_addPoint $enc 2348830 1710940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2348830 1710940
odb::dbWireEncoder_addPoint $enc 2350870 1710940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2350870 1710940
odb::dbWireEncoder_addPoint $enc 2350870 1712060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2346590 1642620
odb::dbWireEncoder_addPoint $enc 2346590 1710380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2329970 1514100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2330350 1514100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2330350 1514380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2330350 1514380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2330350 1513540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2330350 1514100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2330350 1625260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2330350 1625260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2330350 1642060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2346590 1642060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2346590 1642620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2346590 1642620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2346590 1710380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2348830 1710380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2348830 1710940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2350870 1710940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2350870 1712060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2329970 1514100
odb::dbWireEncoder_addPoint $enc 2330350 1514100
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3133375d5b31315d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2209130 463120
odb::dbWireEncoder_addPoint $enc 2209510 463120
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2209130 463120
odb::dbWireEncoder_addPoint $enc 2209130 464100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2208750 464100
odb::dbWireEncoder_addPoint $enc 2209130 464100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2208750 464100
odb::dbWireEncoder_addPoint $enc 2208750 476700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2206850 476700
odb::dbWireEncoder_addPoint $enc 2208750 476700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2207230 476700
odb::dbWireEncoder_addPoint $enc 2207230 477540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2204950 460740
odb::dbWireEncoder_addPoint $enc 2204950 464380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2204950 464380
odb::dbWireEncoder_addPoint $enc 2208750 464380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2201150 460740
odb::dbWireEncoder_addPoint $enc 2201150 461020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2201150 461020
odb::dbWireEncoder_addPoint $enc 2204950 461020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2199630 460740
odb::dbWireEncoder_addPoint $enc 2199630 461020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2199630 461020
odb::dbWireEncoder_addPoint $enc 2201150 461020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2209510 463120
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2208750 476700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2206850 476700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2207230 477540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2207230 476700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2204950 460740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2204950 464380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2208750 464380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2201150 460740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2201150 461020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2204950 461020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2199630 460740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2199630 461020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2206850 476700
odb::dbWireEncoder_addPoint $enc 2207230 476700
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3134315d5b32335d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 222110 161700
odb::dbWireEncoder_addPoint $enc 223630 161700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 222110 161700
odb::dbWireEncoder_addPoint $enc 222110 163940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 225150 158340
odb::dbWireEncoder_addPoint $enc 225150 161700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 223630 161700
odb::dbWireEncoder_addPoint $enc 225150 161700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 223250 155260
odb::dbWireEncoder_addPoint $enc 223250 161700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 222490 152740
odb::dbWireEncoder_addPoint $enc 222490 153300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 222490 153300
odb::dbWireEncoder_addPoint $enc 223250 153300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 223250 153300
odb::dbWireEncoder_addPoint $enc 223250 155260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 225530 152740
odb::dbWireEncoder_addPoint $enc 225530 153020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 225150 153020
odb::dbWireEncoder_addPoint $enc 225530 153020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 225150 153020
odb::dbWireEncoder_addPoint $enc 225150 153300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 223250 153300
odb::dbWireEncoder_addPoint $enc 225150 153300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 223630 161700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 222110 161700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 222110 163940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 225150 158340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 225150 161700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 223250 155260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 223250 161700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 222490 152740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 222490 153300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 223250 153300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 225530 152740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 225150 153300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 223630 161700
odb::dbWireEncoder_addPoint $enc 223250 161700
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3233375d5b32355d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 79610 309540
odb::dbWireEncoder_addPoint $enc 83030 309540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 79610 306460
odb::dbWireEncoder_addPoint $enc 79610 309540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 87590 306460
odb::dbWireEncoder_addPoint $enc 87590 308700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 83030 308700
odb::dbWireEncoder_addPoint $enc 87590 308700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 83030 308700
odb::dbWireEncoder_addPoint $enc 83030 309540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 86450 314580
odb::dbWireEncoder_addPoint $enc 86450 315140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 86450 314580
odb::dbWireEncoder_addPoint $enc 87590 314580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 87590 308700
odb::dbWireEncoder_addPoint $enc 87590 314580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 84550 317100
odb::dbWireEncoder_addPoint $enc 86450 317100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 86450 315140
odb::dbWireEncoder_addPoint $enc 86450 317100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 84930 317100
odb::dbWireEncoder_addPoint $enc 84930 317660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 83030 309540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 83030 309540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 79610 309540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 79610 306460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 87590 306460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 87590 308700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 83030 308700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 86450 315140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 86450 314580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 87590 314580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 84550 317100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 86450 317100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 84930 317660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 84930 317100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 84550 317100
odb::dbWireEncoder_addPoint $enc 84930 317100
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b34385d5b31345d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1760350 474460
odb::dbWireEncoder_addPoint $enc 1760350 476700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1760350 476700
odb::dbWireEncoder_addPoint $enc 1764530 476700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1764150 463260
odb::dbWireEncoder_addPoint $enc 1764150 476700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1763390 457660
odb::dbWireEncoder_addPoint $enc 1764150 457660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1764150 457660
odb::dbWireEncoder_addPoint $enc 1764150 463260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1758830 455140
odb::dbWireEncoder_addPoint $enc 1758830 459620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1758830 459620
odb::dbWireEncoder_addPoint $enc 1764150 459620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1756930 450940
odb::dbWireEncoder_addPoint $enc 1757310 450940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1756930 450940
odb::dbWireEncoder_addPoint $enc 1756930 452620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1756930 452620
odb::dbWireEncoder_addPoint $enc 1757310 452620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1757310 452620
odb::dbWireEncoder_addPoint $enc 1757310 453180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1757310 453180
odb::dbWireEncoder_addPoint $enc 1758830 453180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1758830 453180
odb::dbWireEncoder_addPoint $enc 1758830 455140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1757310 446460
odb::dbWireEncoder_addPoint $enc 1757310 448420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1757310 448420
odb::dbWireEncoder_addPoint $enc 1758830 448420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1758830 448420
odb::dbWireEncoder_addPoint $enc 1759210 448420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1759210 443940
odb::dbWireEncoder_addPoint $enc 1759210 448420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1759210 443940
odb::dbWireEncoder_addPoint $enc 1764910 443940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1757310 448420
odb::dbWireEncoder_addPoint $enc 1757310 450940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1760350 474460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1760350 476700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1764530 476700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1764150 463260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1764150 476700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1763390 457660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1758830 455140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1758830 459620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1764150 459620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1757310 446460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1757310 448420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1758830 448420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1759210 443940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1764910 443940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1764910 443940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1764530 476700
odb::dbWireEncoder_addPoint $enc 1764150 476700
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b36385d5b32325d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 139650 317100
odb::dbWireEncoder_addPoint $enc 143450 317100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 139650 315140
odb::dbWireEncoder_addPoint $enc 139650 317100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 143070 317100
odb::dbWireEncoder_addPoint $enc 143070 323260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 146110 321020
odb::dbWireEncoder_addPoint $enc 146490 321020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 146110 319060
odb::dbWireEncoder_addPoint $enc 146110 321020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 143070 319060
odb::dbWireEncoder_addPoint $enc 146110 319060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 144590 319060
odb::dbWireEncoder_addPoint $enc 144590 326340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 146870 328300
odb::dbWireEncoder_addPoint $enc 146870 328860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 145730 328300
odb::dbWireEncoder_addPoint $enc 146870 328300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 145730 326340
odb::dbWireEncoder_addPoint $enc 145730 328300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 144590 326340
odb::dbWireEncoder_addPoint $enc 145730 326340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 143450 317100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 139650 317100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 139650 315140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 143070 323260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 143070 317100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 146490 321020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 146110 319060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 143070 319060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 144590 326340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 144590 319060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 146870 328860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 143450 317100
odb::dbWireEncoder_addPoint $enc 143070 317100
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e6574313034333430}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 456190 2391340
odb::dbWireEncoder_addPoint $enc 456190 2392740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 456190 2391340
odb::dbWireEncoder_addPoint $enc 462750 2391340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 456950 2394140
odb::dbWireEncoder_addPoint $enc 456950 2395260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 456950 2393860
odb::dbWireEncoder_addPoint $enc 456950 2394140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 456190 2393860
odb::dbWireEncoder_addPoint $enc 456950 2393860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 456190 2392740
odb::dbWireEncoder_addPoint $enc 456190 2393860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 453530 2391340
odb::dbWireEncoder_addPoint $enc 453530 2392740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 453530 2391340
odb::dbWireEncoder_addPoint $enc 456190 2391340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 453530 2392740
odb::dbWireEncoder_addPoint $enc 453910 2392740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 634110 2314060
odb::dbWireEncoder_addPoint $enc 638590 2314060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 638590 2307340
odb::dbWireEncoder_addPoint $enc 638590 2314060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 616170 2311260
odb::dbWireEncoder_addPoint $enc 616170 2312100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 616170 2312100
odb::dbWireEncoder_addPoint $enc 634110 2312100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 634110 2312100
odb::dbWireEncoder_addPoint $enc 634110 2314060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 634030 2395260
odb::dbWireEncoder_addPoint $enc 634110 2395260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 397290 2419900
odb::dbWireEncoder_addPoint $enc 397290 2420740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 397290 2419900
odb::dbWireEncoder_addPoint $enc 397790 2419900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 373730 2423260
odb::dbWireEncoder_addPoint $enc 374830 2423260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 374830 2419900
odb::dbWireEncoder_addPoint $enc 374830 2423260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 374830 2419900
odb::dbWireEncoder_addPoint $enc 397790 2419900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 453910 2392740
odb::dbWireEncoder_addPoint $enc 453910 2405620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 540550 2412060
odb::dbWireEncoder_addPoint $enc 541150 2412060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 541150 2412060
odb::dbWireEncoder_addPoint $enc 541150 2413180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 634110 2314060
odb::dbWireEncoder_addPoint $enc 634110 2395260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 633270 2414860
odb::dbWireEncoder_addPoint $enc 633270 2415140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 632990 2414860
odb::dbWireEncoder_addPoint $enc 633270 2414860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 632990 2412620
odb::dbWireEncoder_addPoint $enc 632990 2414860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 632990 2412620
odb::dbWireEncoder_addPoint $enc 632990 2413180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 632990 2412620
odb::dbWireEncoder_addPoint $enc 634110 2412620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 634110 2395260
odb::dbWireEncoder_addPoint $enc 634110 2412620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 352990 2400860
odb::dbWireEncoder_addPoint $enc 355490 2400860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 347890 2398340
odb::dbWireEncoder_addPoint $enc 347890 2400860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 347890 2400860
odb::dbWireEncoder_addPoint $enc 352990 2400860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 350170 2392740
odb::dbWireEncoder_addPoint $enc 350550 2392740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 350170 2392740
odb::dbWireEncoder_addPoint $enc 350170 2400860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 352830 2392740
odb::dbWireEncoder_addPoint $enc 352830 2394420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 350170 2394420
odb::dbWireEncoder_addPoint $enc 352830 2394420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 513570 2395260
odb::dbWireEncoder_addPoint $enc 513570 2395540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 513570 2395540
odb::dbWireEncoder_addPoint $enc 514830 2395540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 490390 2389660
odb::dbWireEncoder_addPoint $enc 490390 2391900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 490390 2391900
odb::dbWireEncoder_addPoint $enc 490750 2391900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 490750 2391900
odb::dbWireEncoder_addPoint $enc 490750 2394140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 490750 2394140
odb::dbWireEncoder_addPoint $enc 514830 2394140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 514830 2394140
odb::dbWireEncoder_addPoint $enc 514830 2395540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 490750 2391340
odb::dbWireEncoder_addPoint $enc 490750 2391900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 462750 2391340
odb::dbWireEncoder_addPoint $enc 490750 2391340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 680590 2288140
odb::dbWireEncoder_addPoint $enc 680590 2307340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 680030 2288140
odb::dbWireEncoder_addPoint $enc 680590 2288140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 638590 2307340
odb::dbWireEncoder_addPoint $enc 680590 2307340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 343710 2422140
odb::dbWireEncoder_addPoint $enc 343710 2423260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 343710 2422140
odb::dbWireEncoder_addPoint $enc 347950 2422140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 347950 2422140
odb::dbWireEncoder_addPoint $enc 366990 2422140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 366990 2421580
odb::dbWireEncoder_addPoint $enc 366990 2422140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 352990 2400860
odb::dbWireEncoder_addPoint $enc 352990 2422140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 366990 2421580
odb::dbWireEncoder_addPoint $enc 374830 2421580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 449870 2405620
odb::dbWireEncoder_addPoint $enc 449870 2419900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 397790 2419900
odb::dbWireEncoder_addPoint $enc 449870 2419900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 449870 2405620
odb::dbWireEncoder_addPoint $enc 453910 2405620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 530100 2413180
odb::dbWireEncoder_addPoint $enc 541150 2413180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 514830 2412620
odb::dbWireEncoder_addPoint $enc 530100 2412620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 530100 2412620
odb::dbWireEncoder_addPoint $enc 530100 2413180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 514830 2395540
odb::dbWireEncoder_addPoint $enc 514830 2412620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 541150 2413180
odb::dbWireEncoder_addPoint $enc 632990 2413180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 687870 2261700
odb::dbWireEncoder_addPoint $enc 687990 2261700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 687870 2261700
odb::dbWireEncoder_addPoint $enc 687870 2262540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 680030 2262540
odb::dbWireEncoder_addPoint $enc 687870 2262540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 686470 2258340
odb::dbWireEncoder_addPoint $enc 687990 2258340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 687990 2258340
odb::dbWireEncoder_addPoint $enc 687990 2261700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 680030 2262540
odb::dbWireEncoder_addPoint $enc 680030 2288140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 456190 2392740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 456190 2391340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 462750 2391340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 462750 2391340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 456950 2395260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 456950 2394140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 456190 2393860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 453530 2392740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 453530 2391340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 634110 2314060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 638590 2314060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 638590 2307340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 616170 2311260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 616170 2312100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 634110 2312100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 634030 2395260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 634030 2395260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 634110 2395260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 397290 2420740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 397290 2419900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 397790 2419900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 397790 2419900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 373730 2423260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 373730 2423260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 374830 2423260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 374830 2419900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 374830 2421580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 453910 2405620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 540550 2412060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 540550 2412060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 541150 2412060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 541150 2413180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 633270 2415140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 633270 2414860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 632990 2414860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 632990 2412620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 355490 2400860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 355490 2400860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 352990 2400860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 347890 2398340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 347890 2400860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 350550 2392740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 350170 2400860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 352830 2392740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 352830 2394420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 350170 2394420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 513570 2395260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 513570 2395540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 514830 2395540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 490390 2389660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 490750 2391900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 490750 2394140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 514830 2394140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 490750 2391340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 680590 2307340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 343710 2423260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 343710 2422140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 347950 2422140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 347950 2422140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 352990 2422140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 449870 2419900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 449870 2405620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 514830 2412620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 687990 2261700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 687990 2261700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 687870 2261700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 687870 2262540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 680030 2262540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 686470 2258340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 686470 2258340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 687990 2258340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 490750 2391900
odb::dbWireEncoder_addPoint $enc 490390 2391900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 490750 2391900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e6574313731383737}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 217170 1913100
odb::dbWireEncoder_addPoint $enc 217170 1913660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 217170 1913100
odb::dbWireEncoder_addPoint $enc 217470 1913100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 217470 1910540
odb::dbWireEncoder_addPoint $enc 217470 1913100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 217470 1910540
odb::dbWireEncoder_addPoint $enc 217790 1910540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal8] ROUTED
odb::dbWireEncoder_addPoint $enc 217790 1910540
odb::dbWireEncoder_addPoint $enc 217790 1913740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 216030 1909180
odb::dbWireEncoder_addPoint $enc 216030 1910020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 216030 1910020
odb::dbWireEncoder_addPoint $enc 217470 1910020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 217470 1910020
odb::dbWireEncoder_addPoint $enc 217470 1913100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 211090 1905540
odb::dbWireEncoder_addPoint $enc 211090 1909180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 476990 1910540
odb::dbWireEncoder_addPoint $enc 484590 1910540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 484590 1910540
odb::dbWireEncoder_addPoint $enc 484590 1929340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 540990 1928140
odb::dbWireEncoder_addPoint $enc 540990 1929740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 540990 1929740
odb::dbWireEncoder_addPoint $enc 563390 1929740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 563390 1928140
odb::dbWireEncoder_addPoint $enc 563390 1929740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 204250 1913660
odb::dbWireEncoder_addPoint $enc 204250 1917300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 200450 1917300
odb::dbWireEncoder_addPoint $enc 204250 1917300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 199690 1917300
odb::dbWireEncoder_addPoint $enc 200450 1917300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 199690 1916740
odb::dbWireEncoder_addPoint $enc 199690 1917300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 201970 1905540
odb::dbWireEncoder_addPoint $enc 201970 1906660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 201970 1906660
odb::dbWireEncoder_addPoint $enc 204250 1906660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 204250 1906660
odb::dbWireEncoder_addPoint $enc 204250 1913660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 204250 1909180
odb::dbWireEncoder_addPoint $enc 216030 1909180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 217790 1913740
odb::dbWireEncoder_addPoint $enc 410400 1913740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 410400 1910540
odb::dbWireEncoder_addPoint $enc 410400 1913740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 410400 1910540
odb::dbWireEncoder_addPoint $enc 476990 1910540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 513150 1928140
odb::dbWireEncoder_addPoint $enc 513150 1929340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 484590 1929340
odb::dbWireEncoder_addPoint $enc 513150 1929340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 513150 1928140
odb::dbWireEncoder_addPoint $enc 540990 1928140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 574750 1928140
odb::dbWireEncoder_addPoint $enc 574750 1929740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 574750 1929740
odb::dbWireEncoder_addPoint $enc 598830 1929740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 563390 1928140
odb::dbWireEncoder_addPoint $enc 574750 1928140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 598830 1914780
odb::dbWireEncoder_addPoint $enc 601630 1914780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 601630 1914780
odb::dbWireEncoder_addPoint $enc 602870 1914780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 602870 1908900
odb::dbWireEncoder_addPoint $enc 602870 1914780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 598830 1914780
odb::dbWireEncoder_addPoint $enc 598830 1929740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 217170 1913660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 217470 1913100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 217470 1913100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 217470 1913100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 217470 1910540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via6_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 217790 1910540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via7_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal8] ROUTED
odb::dbWireEncoder_addPoint $enc 217790 1913740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via8_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 217470 1910020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 211090 1905540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 211090 1909180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 476990 1910540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via7_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal8] ROUTED
odb::dbWireEncoder_addPoint $enc 476990 1910540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via8_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 484590 1910540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via6_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 484590 1929340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 204250 1913660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 204250 1917300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 200450 1917300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 199690 1916740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 201970 1905540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 201970 1906660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 204250 1906660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 204250 1909180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 513150 1929340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 513150 1928140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via6_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 598830 1929740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via6_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 598830 1914780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 601630 1914780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 601630 1914780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 602870 1914780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 602870 1908900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 217470 1913100
odb::dbWireEncoder_addPoint $enc 217170 1913100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 217470 1913100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743732323435}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 464550 2162580
odb::dbWireEncoder_addPoint $enc 464550 2163140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 464550 2162580
odb::dbWireEncoder_addPoint $enc 464930 2162580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 464930 2160900
odb::dbWireEncoder_addPoint $enc 464930 2162580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 464930 2160900
odb::dbWireEncoder_addPoint $enc 464990 2160900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 464990 2147460
odb::dbWireEncoder_addPoint $enc 464990 2160900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 460510 2147460
odb::dbWireEncoder_addPoint $enc 464990 2147460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 460510 2147180
odb::dbWireEncoder_addPoint $enc 460510 2147460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 464930 2165660
odb::dbWireEncoder_addPoint $enc 465310 2165660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 464930 2165100
odb::dbWireEncoder_addPoint $enc 464930 2165660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 464550 2165100
odb::dbWireEncoder_addPoint $enc 464930 2165100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 464550 2163140
odb::dbWireEncoder_addPoint $enc 464550 2165100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 486590 2143260
odb::dbWireEncoder_addPoint $enc 486590 2143820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 464990 2143820
odb::dbWireEncoder_addPoint $enc 486590 2143820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 464990 2143820
odb::dbWireEncoder_addPoint $enc 464990 2147460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 486590 2143820
odb::dbWireEncoder_addPoint $enc 486590 2145220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 542830 2144380
odb::dbWireEncoder_addPoint $enc 542830 2146340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 615070 2144660
odb::dbWireEncoder_addPoint $enc 615070 2146060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 409070 2183860
odb::dbWireEncoder_addPoint $enc 409070 2185540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 406790 2185540
odb::dbWireEncoder_addPoint $enc 406790 2185820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 406790 2185820
odb::dbWireEncoder_addPoint $enc 409070 2185820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 409070 2185540
odb::dbWireEncoder_addPoint $enc 409070 2185820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 406790 2185820
odb::dbWireEncoder_addPoint $enc 406790 2188060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 407550 2187500
odb::dbWireEncoder_addPoint $enc 407550 2188060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 406790 2187500
odb::dbWireEncoder_addPoint $enc 407550 2187500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 401470 2187500
odb::dbWireEncoder_addPoint $enc 401470 2188060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 401470 2187500
odb::dbWireEncoder_addPoint $enc 406790 2187500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 402990 2174060
odb::dbWireEncoder_addPoint $enc 402990 2176860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 402990 2174060
odb::dbWireEncoder_addPoint $enc 407930 2174060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 407930 2173780
odb::dbWireEncoder_addPoint $enc 407930 2174060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 401470 2175180
odb::dbWireEncoder_addPoint $enc 401470 2176860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 401470 2175180
odb::dbWireEncoder_addPoint $enc 402990 2175180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 450300 2147180
odb::dbWireEncoder_addPoint $enc 460510 2147180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 412110 2146060
odb::dbWireEncoder_addPoint $enc 412110 2146340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 412110 2146060
odb::dbWireEncoder_addPoint $enc 416670 2146060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 416670 2146060
odb::dbWireEncoder_addPoint $enc 416670 2146620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 416670 2146620
odb::dbWireEncoder_addPoint $enc 450300 2146620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 450300 2146620
odb::dbWireEncoder_addPoint $enc 450300 2147180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 411350 2147740
odb::dbWireEncoder_addPoint $enc 411350 2151940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 411350 2147740
odb::dbWireEncoder_addPoint $enc 412110 2147740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 412110 2146340
odb::dbWireEncoder_addPoint $enc 412110 2147740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 411230 2165380
odb::dbWireEncoder_addPoint $enc 411790 2165380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 411790 2151100
odb::dbWireEncoder_addPoint $enc 411790 2165380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 411350 2151100
odb::dbWireEncoder_addPoint $enc 411790 2151100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 530100 2144940
odb::dbWireEncoder_addPoint $enc 542830 2144940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 511290 2156700
odb::dbWireEncoder_addPoint $enc 511290 2157540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 510910 2156700
odb::dbWireEncoder_addPoint $enc 511290 2156700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 510910 2145220
odb::dbWireEncoder_addPoint $enc 510910 2156700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 512810 2156700
odb::dbWireEncoder_addPoint $enc 512810 2159920
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 511290 2156700
odb::dbWireEncoder_addPoint $enc 512810 2156700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 530100 2144940
odb::dbWireEncoder_addPoint $enc 530100 2145220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 510910 2145220
odb::dbWireEncoder_addPoint $enc 530100 2145220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 486590 2145220
odb::dbWireEncoder_addPoint $enc 510910 2145220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 542830 2144380
odb::dbWireEncoder_addPoint $enc 570000 2144380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 570000 2144380
odb::dbWireEncoder_addPoint $enc 570000 2144660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 570000 2144660
odb::dbWireEncoder_addPoint $enc 615070 2144660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 676210 2143260
odb::dbWireEncoder_addPoint $enc 676210 2146620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 658750 2146620
odb::dbWireEncoder_addPoint $enc 676210 2146620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 658750 2146060
odb::dbWireEncoder_addPoint $enc 658750 2146620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 675830 2137660
odb::dbWireEncoder_addPoint $enc 675830 2139060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 675830 2139060
odb::dbWireEncoder_addPoint $enc 676210 2139060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 676210 2139060
odb::dbWireEncoder_addPoint $enc 676210 2143260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 680010 2140740
odb::dbWireEncoder_addPoint $enc 680010 2143540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 676210 2143540
odb::dbWireEncoder_addPoint $enc 680010 2143540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 681150 2150540
odb::dbWireEncoder_addPoint $enc 681150 2150820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 678490 2150540
odb::dbWireEncoder_addPoint $enc 681150 2150540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 678490 2146620
odb::dbWireEncoder_addPoint $enc 678490 2150540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 676210 2146620
odb::dbWireEncoder_addPoint $enc 678490 2146620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 615070 2146060
odb::dbWireEncoder_addPoint $enc 658750 2146060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 411230 2173780
odb::dbWireEncoder_addPoint $enc 411230 2183860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 407930 2173780
odb::dbWireEncoder_addPoint $enc 411230 2173780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 409070 2183860
odb::dbWireEncoder_addPoint $enc 411230 2183860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 411230 2165380
odb::dbWireEncoder_addPoint $enc 411230 2173780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 464550 2163140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 464930 2160900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 464990 2160900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 464990 2147460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 465310 2165660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 486590 2143260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 486590 2143820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 464990 2143820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 486590 2145220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 542830 2146340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 542830 2144380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 542830 2144940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 409070 2185540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 409070 2183860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 406790 2185540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 406790 2185820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 409070 2185820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 406790 2188060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 407550 2188060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 407550 2187500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 406790 2187500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 401470 2188060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 401470 2187500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 402990 2176860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 402990 2174060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 401470 2176860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 401470 2175180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 402990 2175180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 412110 2146340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 412110 2146060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 411350 2151940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 411350 2147740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 412110 2147740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 411790 2151100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 411350 2151100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 511290 2157540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 510910 2156700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 510910 2145220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 512810 2159920
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 512810 2156700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 676210 2143260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 676210 2146620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 675830 2137660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 680010 2140740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 680010 2143540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 676210 2143540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 681150 2150820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 681150 2150540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 678490 2150540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 678490 2146620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 411230 2173780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 411230 2183860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 510910 2156700
odb::dbWireEncoder_addPoint $enc 511290 2156700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 510910 2156700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743737313131}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2145670 233100
odb::dbWireEncoder_addPoint $enc 2145670 233660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2145670 233100
odb::dbWireEncoder_addPoint $enc 2149470 233100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2140350 228340
odb::dbWireEncoder_addPoint $enc 2140350 233100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2140350 233100
odb::dbWireEncoder_addPoint $enc 2145670 233100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2139590 225540
odb::dbWireEncoder_addPoint $enc 2139590 228340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2139590 228340
odb::dbWireEncoder_addPoint $enc 2140350 228340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2149470 222740
odb::dbWireEncoder_addPoint $enc 2149850 222740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2149470 222740
odb::dbWireEncoder_addPoint $enc 2149470 233100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2149470 211820
odb::dbWireEncoder_addPoint $enc 2150030 211820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2149470 211820
odb::dbWireEncoder_addPoint $enc 2149470 222740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2206850 88340
odb::dbWireEncoder_addPoint $enc 2206850 88620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2206850 88620
odb::dbWireEncoder_addPoint $enc 2207230 88620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2207610 85540
odb::dbWireEncoder_addPoint $enc 2207610 88620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2207230 88620
odb::dbWireEncoder_addPoint $enc 2207610 88620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2149470 233100
odb::dbWireEncoder_addPoint $enc 2149470 266420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2206470 93940
odb::dbWireEncoder_addPoint $enc 2206470 94780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2206470 94780
odb::dbWireEncoder_addPoint $enc 2207610 94780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2207610 94780
odb::dbWireEncoder_addPoint $enc 2207610 96460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2206470 92820
odb::dbWireEncoder_addPoint $enc 2207230 92820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2206470 92820
odb::dbWireEncoder_addPoint $enc 2206470 93940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2207230 88620
odb::dbWireEncoder_addPoint $enc 2207230 92820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2044750 88900
odb::dbWireEncoder_addPoint $enc 2044750 94500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2044750 94500
odb::dbWireEncoder_addPoint $enc 2086200 94500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2086200 94500
odb::dbWireEncoder_addPoint $enc 2086200 94780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2166950 94500
odb::dbWireEncoder_addPoint $enc 2166950 94780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2166950 94500
odb::dbWireEncoder_addPoint $enc 2167950 94500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2167950 94500
odb::dbWireEncoder_addPoint $enc 2167950 94780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2086200 94780
odb::dbWireEncoder_addPoint $enc 2166950 94780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2167950 94780
odb::dbWireEncoder_addPoint $enc 2206470 94780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2168090 200340
odb::dbWireEncoder_addPoint $enc 2168090 200620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2172990 200060
odb::dbWireEncoder_addPoint $enc 2173030 200060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2172990 200060
odb::dbWireEncoder_addPoint $enc 2172990 200340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2168090 200340
odb::dbWireEncoder_addPoint $enc 2172990 200340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2170370 193900
odb::dbWireEncoder_addPoint $enc 2170370 194460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2170370 193900
odb::dbWireEncoder_addPoint $enc 2171130 193900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2171130 193900
odb::dbWireEncoder_addPoint $enc 2171130 200340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2167710 191940
odb::dbWireEncoder_addPoint $enc 2167710 193900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2167710 193900
odb::dbWireEncoder_addPoint $enc 2170370 193900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2150030 200620
odb::dbWireEncoder_addPoint $enc 2168090 200620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2201910 266420
odb::dbWireEncoder_addPoint $enc 2201910 278460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2149470 266420
odb::dbWireEncoder_addPoint $enc 2201910 266420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2004310 83300
odb::dbWireEncoder_addPoint $enc 2005450 83300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2005450 83300
odb::dbWireEncoder_addPoint $enc 2005450 88060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2005450 88060
odb::dbWireEncoder_addPoint $enc 2006970 88060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2006970 88060
odb::dbWireEncoder_addPoint $enc 2006970 88900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2006970 88900
odb::dbWireEncoder_addPoint $enc 2044750 88900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2138070 157500
odb::dbWireEncoder_addPoint $enc 2138070 158060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2138070 157500
odb::dbWireEncoder_addPoint $enc 2150030 157500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2135790 138740
odb::dbWireEncoder_addPoint $enc 2137710 138740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2137710 138740
odb::dbWireEncoder_addPoint $enc 2137710 157500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2137710 157500
odb::dbWireEncoder_addPoint $enc 2138070 157500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2135410 133140
odb::dbWireEncoder_addPoint $enc 2135410 138740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2135410 138740
odb::dbWireEncoder_addPoint $enc 2135790 138740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2136930 130340
odb::dbWireEncoder_addPoint $enc 2136930 131180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2135410 131180
odb::dbWireEncoder_addPoint $enc 2136930 131180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2135410 131180
odb::dbWireEncoder_addPoint $enc 2135410 133140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2134910 125580
odb::dbWireEncoder_addPoint $enc 2135410 125580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2135410 125580
odb::dbWireEncoder_addPoint $enc 2135410 131180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2134910 94780
odb::dbWireEncoder_addPoint $enc 2134910 125580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2150030 157500
odb::dbWireEncoder_addPoint $enc 2150030 211820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2145670 233660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2145670 233100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2149470 233100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2140350 228340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2140350 233100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2139590 225540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2149850 222740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2149850 222740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2149470 222740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2206850 88340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2207610 85540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2134910 94780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2150030 200620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2149470 266420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2206470 93940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2206470 94780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2207610 94780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2207610 96460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2207230 92820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2206470 92820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2044750 88900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2044750 94500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2168090 200340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2168090 200340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2173030 200060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2173030 200060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2170370 194460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2171130 200340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2167710 191940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2167710 193900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2170370 193900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2201910 266420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2201910 278460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2004310 83300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2004310 83300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2005450 83300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2005450 88060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2138070 158060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2150030 157500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2135790 138740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2135790 138740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2137710 138740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2137710 157500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2135410 133140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2136930 130340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2136930 131180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2135410 131180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2134910 125580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2135410 125580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2137710 157500
odb::dbWireEncoder_addPoint $enc 2138070 157500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2137710 157500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743738383335}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 690270 2000740
odb::dbWireEncoder_addPoint $enc 690650 2000740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 690270 1999060
odb::dbWireEncoder_addPoint $enc 690270 2000740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 690270 1999060
odb::dbWireEncoder_addPoint $enc 691410 1999060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 691410 1994860
odb::dbWireEncoder_addPoint $enc 691410 1999060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 691410 1994860
odb::dbWireEncoder_addPoint $enc 695590 1994860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 695590 1984220
odb::dbWireEncoder_addPoint $enc 695590 1994860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 695590 1984220
odb::dbWireEncoder_addPoint $enc 696350 1984220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 696350 1976380
odb::dbWireEncoder_addPoint $enc 696350 1984220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 696350 1976380
odb::dbWireEncoder_addPoint $enc 698250 1976380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 698250 1976380
odb::dbWireEncoder_addPoint $enc 699390 1976380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 690650 2002700
odb::dbWireEncoder_addPoint $enc 692170 2002700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 690650 2000740
odb::dbWireEncoder_addPoint $enc 690650 2002700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 705470 2072700
odb::dbWireEncoder_addPoint $enc 705470 2073540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 705470 2072700
odb::dbWireEncoder_addPoint $enc 705790 2072700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2065420
odb::dbWireEncoder_addPoint $enc 705790 2072700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 705230 2065420
odb::dbWireEncoder_addPoint $enc 705790 2065420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 705230 2052260
odb::dbWireEncoder_addPoint $enc 705230 2065420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 691790 2052260
odb::dbWireEncoder_addPoint $enc 705230 2052260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 703550 2072700
odb::dbWireEncoder_addPoint $enc 705470 2072700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 694070 2163700
odb::dbWireEncoder_addPoint $enc 704110 2163700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 703570 2132060
odb::dbWireEncoder_addPoint $enc 703570 2132900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 703570 2132900
odb::dbWireEncoder_addPoint $enc 705790 2132900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2132900
odb::dbWireEncoder_addPoint $enc 705790 2139900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2139900
odb::dbWireEncoder_addPoint $enc 706350 2139900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 706350 2139900
odb::dbWireEncoder_addPoint $enc 706350 2149420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2149420
odb::dbWireEncoder_addPoint $enc 706350 2149420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2149420
odb::dbWireEncoder_addPoint $enc 705790 2163700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 704110 2163700
odb::dbWireEncoder_addPoint $enc 705790 2163700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 702990 2132900
odb::dbWireEncoder_addPoint $enc 703570 2132900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 705850 2216060
odb::dbWireEncoder_addPoint $enc 705850 2217460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 704670 2217460
odb::dbWireEncoder_addPoint $enc 705850 2217460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 704670 2217460
odb::dbWireEncoder_addPoint $enc 704670 2240700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 704110 2205980
odb::dbWireEncoder_addPoint $enc 705790 2205980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 704110 2205980
odb::dbWireEncoder_addPoint $enc 704110 2214380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 704110 2214380
odb::dbWireEncoder_addPoint $enc 704670 2214380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 704670 2214380
odb::dbWireEncoder_addPoint $enc 704670 2217460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 704670 2296140
odb::dbWireEncoder_addPoint $enc 706910 2296140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 706910 2296140
odb::dbWireEncoder_addPoint $enc 706910 2297260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 706350 2297260
odb::dbWireEncoder_addPoint $enc 706910 2297260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 704710 2387140
odb::dbWireEncoder_addPoint $enc 704710 2388540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 704710 2388540
odb::dbWireEncoder_addPoint $enc 705790 2388540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2375660
odb::dbWireEncoder_addPoint $enc 705790 2388540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 705230 2375660
odb::dbWireEncoder_addPoint $enc 705790 2375660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 705230 2371740
odb::dbWireEncoder_addPoint $enc 705230 2375660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 705230 2371740
odb::dbWireEncoder_addPoint $enc 705790 2371740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 706610 2388540
odb::dbWireEncoder_addPoint $enc 706610 2392740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2388540
odb::dbWireEncoder_addPoint $enc 706610 2388540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 702810 2388540
odb::dbWireEncoder_addPoint $enc 702810 2392740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 702810 2388540
odb::dbWireEncoder_addPoint $enc 704710 2388540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 700910 2391060
odb::dbWireEncoder_addPoint $enc 700910 2392740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 700910 2391060
odb::dbWireEncoder_addPoint $enc 702810 2391060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 693690 2393860
odb::dbWireEncoder_addPoint $enc 693690 2395260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 693690 2393860
odb::dbWireEncoder_addPoint $enc 700910 2393860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 700910 2392740
odb::dbWireEncoder_addPoint $enc 700910 2393860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 691410 2393860
odb::dbWireEncoder_addPoint $enc 691410 2395260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 691410 2393860
odb::dbWireEncoder_addPoint $enc 693690 2393860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 689890 2387140
odb::dbWireEncoder_addPoint $enc 689890 2393860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 689890 2393860
odb::dbWireEncoder_addPoint $enc 691410 2393860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 690270 2028740
odb::dbWireEncoder_addPoint $enc 690270 2030700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 690270 2030700
odb::dbWireEncoder_addPoint $enc 691790 2030700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 692170 2013620
odb::dbWireEncoder_addPoint $enc 693690 2013620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 693690 2013620
odb::dbWireEncoder_addPoint $enc 693690 2025940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 692550 2025940
odb::dbWireEncoder_addPoint $enc 693690 2025940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 692550 2025940
odb::dbWireEncoder_addPoint $enc 692550 2030700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 691790 2030700
odb::dbWireEncoder_addPoint $enc 692550 2030700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 691790 2030700
odb::dbWireEncoder_addPoint $enc 691790 2052260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 692170 2002700
odb::dbWireEncoder_addPoint $enc 692170 2013620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 691790 2104060
odb::dbWireEncoder_addPoint $enc 691790 2104620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 691790 2104620
odb::dbWireEncoder_addPoint $enc 702430 2104620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 702430 2104620
odb::dbWireEncoder_addPoint $enc 702430 2110780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 702430 2110780
odb::dbWireEncoder_addPoint $enc 702990 2110780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 702430 2104620
odb::dbWireEncoder_addPoint $enc 703550 2104620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 702990 2110780
odb::dbWireEncoder_addPoint $enc 702990 2132900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 703550 2072700
odb::dbWireEncoder_addPoint $enc 703550 2104620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 703190 2182600
odb::dbWireEncoder_addPoint $enc 703190 2182740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 703190 2182740
odb::dbWireEncoder_addPoint $enc 704110 2182740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 704110 2182740
odb::dbWireEncoder_addPoint $enc 704110 2186380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 704110 2186380
odb::dbWireEncoder_addPoint $enc 705790 2186380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 699390 2185540
odb::dbWireEncoder_addPoint $enc 699390 2186380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 699390 2186380
odb::dbWireEncoder_addPoint $enc 704110 2186380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 694070 2163700
odb::dbWireEncoder_addPoint $enc 694070 2171260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 704110 2163700
odb::dbWireEncoder_addPoint $enc 704110 2182740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2186380
odb::dbWireEncoder_addPoint $enc 705790 2205980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 704670 2240700
odb::dbWireEncoder_addPoint $enc 704670 2296140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2365500
odb::dbWireEncoder_addPoint $enc 705790 2371740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 702810 2335340
odb::dbWireEncoder_addPoint $enc 702810 2336740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 702810 2335340
odb::dbWireEncoder_addPoint $enc 704670 2335340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 704670 2335340
odb::dbWireEncoder_addPoint $enc 704670 2344300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 704670 2344300
odb::dbWireEncoder_addPoint $enc 706350 2344300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 706350 2344300
odb::dbWireEncoder_addPoint $enc 706350 2365500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2365500
odb::dbWireEncoder_addPoint $enc 706350 2365500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 704670 2335340
odb::dbWireEncoder_addPoint $enc 706350 2335340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 706350 2297260
odb::dbWireEncoder_addPoint $enc 706350 2335340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 690650 2000740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 690270 1999060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 691410 1999060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 691410 1994860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 695590 1994860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 696350 1976380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 698250 1976380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 699390 1976380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 692170 2002700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 690650 2002700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 705470 2073540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2072700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 705230 2052260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 691790 2052260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 703550 2072700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 704110 2163700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 694070 2163700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 703570 2132060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 703570 2132900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2132900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2163700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 702990 2132900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 705850 2216060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 705850 2217460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 704670 2217460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 704670 2240700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 704670 2240700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2205980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 704110 2205980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 704670 2296140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 706910 2296140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 704710 2387140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 704710 2388540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2388540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 706610 2392740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 706610 2388540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 702810 2392740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 702810 2388540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 700910 2392740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 700910 2391060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 702810 2391060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 693690 2395260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 693690 2393860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 700910 2393860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 691410 2395260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 691410 2393860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 689890 2387140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 689890 2393860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 690270 2028740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 690270 2030700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 691790 2030700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 693690 2025940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 692550 2025940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 692550 2030700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 691790 2104060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 691790 2104620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 702430 2104620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 703550 2104620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 703190 2182600
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 703190 2182740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 704110 2182740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 704110 2186380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2186380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 699390 2185540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 699390 2186380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 694070 2171260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 702810 2336740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 702810 2335340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 704670 2335340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 704670 2344300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 706350 2344300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 706350 2335340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2072700
odb::dbWireEncoder_addPoint $enc 705470 2072700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 705790 2072700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743830323338}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 87970 2067940
odb::dbWireEncoder_addPoint $enc 87970 2068500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 60990 2151940
odb::dbWireEncoder_addPoint $enc 60990 2152500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 60670 2152500
odb::dbWireEncoder_addPoint $enc 60990 2152500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 60990 2149980
odb::dbWireEncoder_addPoint $enc 60990 2151940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 70490 2112460
odb::dbWireEncoder_addPoint $enc 70490 2112740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 79710 2112460
odb::dbWireEncoder_addPoint $enc 79710 2149980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 58710 2168180
odb::dbWireEncoder_addPoint $enc 60670 2168180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 58710 2168180
odb::dbWireEncoder_addPoint $enc 58710 2171260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 60670 2152500
odb::dbWireEncoder_addPoint $enc 60670 2168180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 113430 2056740
odb::dbWireEncoder_addPoint $enc 113430 2057300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 112190 2057300
odb::dbWireEncoder_addPoint $enc 113430 2057300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 113430 2057300
odb::dbWireEncoder_addPoint $enc 113870 2057300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 87970 2068500
odb::dbWireEncoder_addPoint $enc 112190 2068500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 97070 2144100
odb::dbWireEncoder_addPoint $enc 97070 2149980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 97070 2144100
odb::dbWireEncoder_addPoint $enc 100510 2144100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 100510 2143260
odb::dbWireEncoder_addPoint $enc 100510 2144100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 60990 2149980
odb::dbWireEncoder_addPoint $enc 97070 2149980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 113870 2027900
odb::dbWireEncoder_addPoint $enc 114430 2027900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 114430 2026780
odb::dbWireEncoder_addPoint $enc 114430 2027900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 113870 2026780
odb::dbWireEncoder_addPoint $enc 114430 2026780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 113870 2023420
odb::dbWireEncoder_addPoint $enc 113870 2026780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 108490 2023420
odb::dbWireEncoder_addPoint $enc 113870 2023420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 108490 2017540
odb::dbWireEncoder_addPoint $enc 108490 2023420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 113870 2027900
odb::dbWireEncoder_addPoint $enc 113870 2057300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 99370 2088380
odb::dbWireEncoder_addPoint $enc 113810 2088380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 99370 2088380
odb::dbWireEncoder_addPoint $enc 99370 2088660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 83070 2088660
odb::dbWireEncoder_addPoint $enc 99370 2088660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 83070 2088660
odb::dbWireEncoder_addPoint $enc 83070 2112460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 70490 2112460
odb::dbWireEncoder_addPoint $enc 83070 2112460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 112190 2057300
odb::dbWireEncoder_addPoint $enc 112190 2088380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 87970 2067940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 87970 2068500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 60990 2151940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 60670 2152500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 60990 2149980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 79710 2149980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 70490 2112460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 70490 2112740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 79710 2112460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 60670 2168180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 58710 2168180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 58710 2171260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 113430 2056740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 113430 2057300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 112190 2057300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 113870 2057300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 112190 2068500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 97070 2149980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 97070 2144100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 100510 2144100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 100510 2143260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 113870 2023420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 108490 2023420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 108490 2017540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 113810 2088380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 113810 2088380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 83070 2088660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 83070 2112460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 112190 2088380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 60670 2152500
odb::dbWireEncoder_addPoint $enc 60990 2152500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 60670 2152500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743832333832}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 310270 1915900
odb::dbWireEncoder_addPoint $enc 310270 1916740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 310270 1915900
odb::dbWireEncoder_addPoint $enc 311550 1915900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 311550 1908620
odb::dbWireEncoder_addPoint $enc 311550 1915900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 311550 1908620
odb::dbWireEncoder_addPoint $enc 312110 1908620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 312110 1892380
odb::dbWireEncoder_addPoint $enc 312110 1908620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 312110 1892380
odb::dbWireEncoder_addPoint $enc 321630 1892380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 311030 1924300
odb::dbWireEncoder_addPoint $enc 311550 1924300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 311550 1915900
odb::dbWireEncoder_addPoint $enc 311550 1924300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 317490 1990940
odb::dbWireEncoder_addPoint $enc 317490 1993740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 317490 1990940
odb::dbWireEncoder_addPoint $enc 323950 1990940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 323950 1990940
odb::dbWireEncoder_addPoint $enc 323950 1992060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 313690 2127580
odb::dbWireEncoder_addPoint $enc 313690 2128700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 313690 2127580
odb::dbWireEncoder_addPoint $enc 323190 2127580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 323190 2127580
odb::dbWireEncoder_addPoint $enc 323190 2129540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 312170 2207940
odb::dbWireEncoder_addPoint $enc 312170 2211860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 312170 2211860
odb::dbWireEncoder_addPoint $enc 319390 2211860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 319390 2211860
odb::dbWireEncoder_addPoint $enc 319390 2220260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 319390 2220260
odb::dbWireEncoder_addPoint $enc 320910 2220260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 320910 2220260
odb::dbWireEncoder_addPoint $enc 320910 2227260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 319770 2227260
odb::dbWireEncoder_addPoint $enc 320910 2227260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 312170 2206260
odb::dbWireEncoder_addPoint $enc 312550 2206260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 312170 2206260
odb::dbWireEncoder_addPoint $enc 312170 2207940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 320150 1806420
odb::dbWireEncoder_addPoint $enc 320510 1806420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 310650 1930180
odb::dbWireEncoder_addPoint $enc 311030 1930180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 310650 1930180
odb::dbWireEncoder_addPoint $enc 310650 1940260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 310650 1940260
odb::dbWireEncoder_addPoint $enc 315210 1940260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 315210 1940260
odb::dbWireEncoder_addPoint $enc 315210 1945300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 315210 1945300
odb::dbWireEncoder_addPoint $enc 323190 1945300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 323190 1944740
odb::dbWireEncoder_addPoint $enc 323190 1945300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 310650 1940260
odb::dbWireEncoder_addPoint $enc 310650 1940820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 311030 1924300
odb::dbWireEncoder_addPoint $enc 311030 1930180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 296430 2183300
odb::dbWireEncoder_addPoint $enc 296430 2191980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 296430 2191980
odb::dbWireEncoder_addPoint $enc 310270 2191980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 310270 2191980
odb::dbWireEncoder_addPoint $enc 310270 2197860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 310270 2197860
odb::dbWireEncoder_addPoint $enc 312550 2197860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 299250 2174340
odb::dbWireEncoder_addPoint $enc 299250 2183300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 296430 2183300
odb::dbWireEncoder_addPoint $enc 299250 2183300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 312550 2197860
odb::dbWireEncoder_addPoint $enc 312550 2206260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 290270 1989260
odb::dbWireEncoder_addPoint $enc 290270 1993740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 289710 1989260
odb::dbWireEncoder_addPoint $enc 290270 1989260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 289710 1979180
odb::dbWireEncoder_addPoint $enc 289710 1989260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 289150 1979180
odb::dbWireEncoder_addPoint $enc 289710 1979180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 289150 1969380
odb::dbWireEncoder_addPoint $enc 289150 1979180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 287470 1969380
odb::dbWireEncoder_addPoint $enc 289150 1969380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 284670 2000460
odb::dbWireEncoder_addPoint $enc 285230 2000460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 285230 1993740
odb::dbWireEncoder_addPoint $enc 285230 2000460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 285230 1993740
odb::dbWireEncoder_addPoint $enc 290270 1993740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 275310 1997660
odb::dbWireEncoder_addPoint $enc 275310 1997940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 275310 1997940
odb::dbWireEncoder_addPoint $enc 285230 1997940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 290270 1993740
odb::dbWireEncoder_addPoint $enc 317490 1993740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 276830 2140740
odb::dbWireEncoder_addPoint $enc 276830 2142420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 276830 2142420
odb::dbWireEncoder_addPoint $enc 278730 2142420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 278730 2142420
odb::dbWireEncoder_addPoint $enc 278730 2161460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 277210 2161460
odb::dbWireEncoder_addPoint $enc 278730 2161460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 278730 2142420
odb::dbWireEncoder_addPoint $enc 279870 2142420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 279870 2128700
odb::dbWireEncoder_addPoint $enc 313690 2128700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 290700 1940820
odb::dbWireEncoder_addPoint $enc 310650 1940820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 289750 1953000
odb::dbWireEncoder_addPoint $enc 289750 1955380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 287470 1955380
odb::dbWireEncoder_addPoint $enc 289750 1955380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 290700 1940820
odb::dbWireEncoder_addPoint $enc 290700 1941100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 285950 1941100
odb::dbWireEncoder_addPoint $enc 290700 1941100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 285950 1941100
odb::dbWireEncoder_addPoint $enc 285950 1955380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 285950 1955380
odb::dbWireEncoder_addPoint $enc 287470 1955380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 286710 1939140
odb::dbWireEncoder_addPoint $enc 286710 1939700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 286330 1939700
odb::dbWireEncoder_addPoint $enc 286710 1939700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 286330 1939700
odb::dbWireEncoder_addPoint $enc 286330 1941100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 287470 1955380
odb::dbWireEncoder_addPoint $enc 287470 1969380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 284810 2014180
odb::dbWireEncoder_addPoint $enc 284810 2014460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 284670 2014180
odb::dbWireEncoder_addPoint $enc 284810 2014180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 284670 2000460
odb::dbWireEncoder_addPoint $enc 284670 2014180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 284810 2109660
odb::dbWireEncoder_addPoint $enc 284810 2111900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 279870 2111900
odb::dbWireEncoder_addPoint $enc 284810 2111900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 279870 2111900
odb::dbWireEncoder_addPoint $enc 279870 2142420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 275690 2184420
odb::dbWireEncoder_addPoint $enc 275690 2185540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 275690 2184420
odb::dbWireEncoder_addPoint $enc 277210 2184420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 277210 2161460
odb::dbWireEncoder_addPoint $enc 277210 2184420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 277210 2183300
odb::dbWireEncoder_addPoint $enc 296430 2183300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 320510 1857660
odb::dbWireEncoder_addPoint $enc 321630 1857660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 320510 1806420
odb::dbWireEncoder_addPoint $enc 320510 1857660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 321630 1857660
odb::dbWireEncoder_addPoint $enc 321630 1892380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 281770 2051140
odb::dbWireEncoder_addPoint $enc 282150 2051140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 283290 2039940
odb::dbWireEncoder_addPoint $enc 283290 2040780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 282150 2040780
odb::dbWireEncoder_addPoint $enc 283290 2040780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 282150 2040780
odb::dbWireEncoder_addPoint $enc 282150 2051140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 283290 2040780
odb::dbWireEncoder_addPoint $enc 284670 2040780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 284670 2014180
odb::dbWireEncoder_addPoint $enc 284670 2040780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 275310 2092860
odb::dbWireEncoder_addPoint $enc 275310 2094820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 275310 2094820
odb::dbWireEncoder_addPoint $enc 284810 2094820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 281390 2070180
odb::dbWireEncoder_addPoint $enc 282150 2070180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 281390 2070180
odb::dbWireEncoder_addPoint $enc 281390 2072140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 281010 2072140
odb::dbWireEncoder_addPoint $enc 281390 2072140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 281010 2072140
odb::dbWireEncoder_addPoint $enc 281010 2072700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 281010 2072700
odb::dbWireEncoder_addPoint $enc 281310 2072700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 281310 2072700
odb::dbWireEncoder_addPoint $enc 281310 2094820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 282150 2051140
odb::dbWireEncoder_addPoint $enc 282150 2070180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 284810 2094820
odb::dbWireEncoder_addPoint $enc 284810 2109660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 310270 1916740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 310270 1915900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 311550 1915900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 312110 1892380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 321630 1892380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 311030 1924300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 311550 1924300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 317490 1993740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 317490 1990940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 323950 1990940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 323950 1992060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 313690 2128700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 313690 2127580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 323190 2127580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 323190 2129540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 312170 2207940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 312170 2211860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 319390 2211860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 319770 2227260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 320150 1806420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 320150 1806420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 320510 1806420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 310650 1940260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 315210 1940260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 315210 1945300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 323190 1945300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 323190 1944740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 296430 2183300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 296430 2191980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 310270 2191980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 310270 2197860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 312550 2197860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 299250 2174340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 299250 2183300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 290270 1993740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 289150 1969380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 287470 1969380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 285230 1993740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 275310 1997660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 275310 1997940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 285230 1997940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 276830 2140740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 276830 2142420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 278730 2142420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 278730 2161460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 277210 2161460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 279870 2142420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 279870 2128700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 289750 1953000
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 289750 1955380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 287470 1955380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 285950 1941100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 285950 1955380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 286710 1939140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 286330 1941100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 284810 2014460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 284810 2014180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 284670 2014180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 284810 2109660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 284810 2111900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 279870 2111900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 275690 2185540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 275690 2184420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 277210 2184420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 277210 2183300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 320510 1857660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 321630 1857660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 281770 2051140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 283290 2039940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 283290 2040780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 282150 2040780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 284670 2040780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 275310 2092860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 275310 2094820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 284810 2094820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 281310 2072700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 281310 2094820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 281310 2072700
odb::dbWireEncoder_addPoint $enc 281010 2072700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 281310 2072700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743834373633}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 325850 2300060
odb::dbWireEncoder_addPoint $enc 325850 2302580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 336190 2076900
odb::dbWireEncoder_addPoint $enc 336490 2076900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 339910 2155300
odb::dbWireEncoder_addPoint $enc 340290 2155300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 339530 2291940
odb::dbWireEncoder_addPoint $enc 339530 2302580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 339530 2286060
odb::dbWireEncoder_addPoint $enc 342950 2286060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 339530 2286060
odb::dbWireEncoder_addPoint $enc 339530 2291940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 344850 2286340
odb::dbWireEncoder_addPoint $enc 344850 2286900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 342950 2286900
odb::dbWireEncoder_addPoint $enc 344850 2286900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 342950 2286060
odb::dbWireEncoder_addPoint $enc 342950 2286900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 325850 2302580
odb::dbWireEncoder_addPoint $enc 339530 2302580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 336110 2093420
odb::dbWireEncoder_addPoint $enc 336490 2093420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 336110 2093420
odb::dbWireEncoder_addPoint $enc 336110 2096500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 336110 2096500
odb::dbWireEncoder_addPoint $enc 336490 2096500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 336490 2076900
odb::dbWireEncoder_addPoint $enc 336490 2093420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 344470 2185540
odb::dbWireEncoder_addPoint $enc 344470 2187780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 344470 2187780
odb::dbWireEncoder_addPoint $enc 344850 2187780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 344850 2187780
odb::dbWireEncoder_addPoint $enc 344850 2192540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 344850 2192540
odb::dbWireEncoder_addPoint $enc 346750 2192540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 346750 2192540
odb::dbWireEncoder_addPoint $enc 346750 2193660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 344470 2176860
odb::dbWireEncoder_addPoint $enc 344470 2185540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 340290 2168740
odb::dbWireEncoder_addPoint $enc 340290 2170700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 340290 2170700
odb::dbWireEncoder_addPoint $enc 344470 2170700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 344470 2170700
odb::dbWireEncoder_addPoint $enc 344470 2176860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 339910 2168740
odb::dbWireEncoder_addPoint $enc 340290 2168740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 339910 2155300
odb::dbWireEncoder_addPoint $enc 339910 2168740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 342950 2285700
odb::dbWireEncoder_addPoint $enc 342950 2286060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 342950 2285700
odb::dbWireEncoder_addPoint $enc 343330 2285700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 337630 2266180
odb::dbWireEncoder_addPoint $enc 337630 2266460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 337630 2266180
odb::dbWireEncoder_addPoint $enc 344590 2266180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 344590 2237900
odb::dbWireEncoder_addPoint $enc 344590 2266180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 344590 2237900
odb::dbWireEncoder_addPoint $enc 346370 2237900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 343330 2266180
odb::dbWireEncoder_addPoint $enc 343330 2285700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 337630 2056740
odb::dbWireEncoder_addPoint $enc 337630 2059820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 336190 2059820
odb::dbWireEncoder_addPoint $enc 337630 2059820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 326990 2059820
odb::dbWireEncoder_addPoint $enc 326990 2062340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 326990 2059820
odb::dbWireEncoder_addPoint $enc 336190 2059820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 324330 2054780
odb::dbWireEncoder_addPoint $enc 326990 2054780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 326990 2054780
odb::dbWireEncoder_addPoint $enc 326990 2059820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 327370 2051140
odb::dbWireEncoder_addPoint $enc 327370 2054780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 326990 2054780
odb::dbWireEncoder_addPoint $enc 327370 2054780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 336190 2059820
odb::dbWireEncoder_addPoint $enc 336190 2076900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 336490 2115540
odb::dbWireEncoder_addPoint $enc 336750 2115540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 336750 2115540
odb::dbWireEncoder_addPoint $enc 336750 2120020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 336750 2120020
odb::dbWireEncoder_addPoint $enc 336870 2120020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 336870 2120020
odb::dbWireEncoder_addPoint $enc 336870 2130380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 336870 2130380
odb::dbWireEncoder_addPoint $enc 337630 2130380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 337630 2130380
odb::dbWireEncoder_addPoint $enc 337630 2146340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 337630 2146340
odb::dbWireEncoder_addPoint $enc 340290 2146340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 336490 2096500
odb::dbWireEncoder_addPoint $enc 336490 2115540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 340290 2146340
odb::dbWireEncoder_addPoint $enc 340290 2155300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 346370 2228660
odb::dbWireEncoder_addPoint $enc 347390 2228660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 347390 2207100
odb::dbWireEncoder_addPoint $enc 347390 2228660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 347390 2207100
odb::dbWireEncoder_addPoint $enc 347950 2207100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 347950 2200940
odb::dbWireEncoder_addPoint $enc 347950 2207100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 347950 2200660
odb::dbWireEncoder_addPoint $enc 347950 2200940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 346750 2200660
odb::dbWireEncoder_addPoint $enc 347950 2200660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 346370 2228660
odb::dbWireEncoder_addPoint $enc 346370 2237900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 346750 2193660
odb::dbWireEncoder_addPoint $enc 346750 2200660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 325850 2302580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 325850 2300060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 336190 2076900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 339530 2291940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 339530 2302580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 342950 2286060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 339530 2286060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 344850 2286340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 344850 2286900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 342950 2286900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 346750 2193660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 344470 2185540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 344850 2192540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 346750 2192540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 344470 2176860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 340290 2168740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 340290 2170700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 344470 2170700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 337630 2266460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 337630 2266180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 344590 2266180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 344590 2237900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 346370 2237900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 343330 2266180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 337630 2056740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 337630 2059820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 336190 2059820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 326990 2062340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 326990 2059820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 324330 2054780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 324330 2054780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 326990 2054780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 327370 2051140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 336490 2115540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 336750 2115540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 336750 2120020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 336870 2120020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 337630 2146340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 340290 2146340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 346370 2228660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 347390 2228660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 347950 2200940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 346750 2200660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 336190 2076900
odb::dbWireEncoder_addPoint $enc 336490 2076900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 336190 2076900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743835313136}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2063210 1916460
odb::dbWireEncoder_addPoint $enc 2065870 1916460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2063210 1916460
odb::dbWireEncoder_addPoint $enc 2063210 1920380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2061690 1920380
odb::dbWireEncoder_addPoint $enc 2063210 1920380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2061310 1941660
odb::dbWireEncoder_addPoint $enc 2061310 1942220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2061310 1942220
odb::dbWireEncoder_addPoint $enc 2063210 1942220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2063210 1942220
odb::dbWireEncoder_addPoint $enc 2063210 1954540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2062830 1954540
odb::dbWireEncoder_addPoint $enc 2063210 1954540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2061690 1938300
odb::dbWireEncoder_addPoint $enc 2063210 1938300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2063210 1938300
odb::dbWireEncoder_addPoint $enc 2063210 1942220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2061690 1920380
odb::dbWireEncoder_addPoint $enc 2061690 1938300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2018750 1886780
odb::dbWireEncoder_addPoint $enc 2019510 1886780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2019510 1886780
odb::dbWireEncoder_addPoint $enc 2019510 1891260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2029770 1977500
odb::dbWireEncoder_addPoint $enc 2029770 1977780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2021410 1977500
odb::dbWireEncoder_addPoint $enc 2029770 1977500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2021410 1977500
odb::dbWireEncoder_addPoint $enc 2021410 1978340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2030910 1972460
odb::dbWireEncoder_addPoint $enc 2033950 1972460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2033950 1972460
odb::dbWireEncoder_addPoint $enc 2033950 1977780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2022170 1882020
odb::dbWireEncoder_addPoint $enc 2022170 1883140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2018750 1882020
odb::dbWireEncoder_addPoint $enc 2022170 1882020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2025970 1868860
odb::dbWireEncoder_addPoint $enc 2025970 1869420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2025210 1869420
odb::dbWireEncoder_addPoint $enc 2025970 1869420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2024450 1869420
odb::dbWireEncoder_addPoint $enc 2025210 1869420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2024450 1869420
odb::dbWireEncoder_addPoint $enc 2024450 1882020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2018750 1882020
odb::dbWireEncoder_addPoint $enc 2018750 1886780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2025590 1941100
odb::dbWireEncoder_addPoint $enc 2025590 1943620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2016850 1941100
odb::dbWireEncoder_addPoint $enc 2025590 1941100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2016850 1939140
odb::dbWireEncoder_addPoint $enc 2016850 1941100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2030910 1943620
odb::dbWireEncoder_addPoint $enc 2030910 1972460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2025590 1943620
odb::dbWireEncoder_addPoint $enc 2063210 1943620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2058270 1882860
odb::dbWireEncoder_addPoint $enc 2058270 1883140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2057630 1882860
odb::dbWireEncoder_addPoint $enc 2058270 1882860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2057630 1882580
odb::dbWireEncoder_addPoint $enc 2057630 1882860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2046110 1882580
odb::dbWireEncoder_addPoint $enc 2057630 1882580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2046110 1882300
odb::dbWireEncoder_addPoint $enc 2046110 1882580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2041170 1882300
odb::dbWireEncoder_addPoint $enc 2046110 1882300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2041170 1882020
odb::dbWireEncoder_addPoint $enc 2041170 1882300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2067770 1894060
odb::dbWireEncoder_addPoint $enc 2067770 1894340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2067390 1894060
odb::dbWireEncoder_addPoint $enc 2067770 1894060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2067390 1893220
odb::dbWireEncoder_addPoint $enc 2067390 1894060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2065870 1893220
odb::dbWireEncoder_addPoint $enc 2067390 1893220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2065870 1884820
odb::dbWireEncoder_addPoint $enc 2065870 1893220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2058270 1884820
odb::dbWireEncoder_addPoint $enc 2065870 1884820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2058270 1884540
odb::dbWireEncoder_addPoint $enc 2058270 1884820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2058270 1883140
odb::dbWireEncoder_addPoint $enc 2058270 1884540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2064350 1899940
odb::dbWireEncoder_addPoint $enc 2064350 1900220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2064350 1900220
odb::dbWireEncoder_addPoint $enc 2067770 1900220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2067770 1894340
odb::dbWireEncoder_addPoint $enc 2067770 1900220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2065870 1913100
odb::dbWireEncoder_addPoint $enc 2065870 1913660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2065470 1913100
odb::dbWireEncoder_addPoint $enc 2065870 1913100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2065470 1900220
odb::dbWireEncoder_addPoint $enc 2065470 1913100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2022170 1882020
odb::dbWireEncoder_addPoint $enc 2041170 1882020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2065870 1913660
odb::dbWireEncoder_addPoint $enc 2065870 1916460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2039650 1975260
odb::dbWireEncoder_addPoint $enc 2039650 1977780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2039650 1975260
odb::dbWireEncoder_addPoint $enc 2040030 1975260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2062830 1957340
odb::dbWireEncoder_addPoint $enc 2063790 1957340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2063790 1957340
odb::dbWireEncoder_addPoint $enc 2063790 1966020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2063210 1966020
odb::dbWireEncoder_addPoint $enc 2063790 1966020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2029770 1977780
odb::dbWireEncoder_addPoint $enc 2039650 1977780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2062830 1954540
odb::dbWireEncoder_addPoint $enc 2062830 1957340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2065870 1916460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2063210 1916460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2063210 1920380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2061690 1920380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2061310 1941660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2061310 1942220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2063210 1942220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2063210 1943620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2061690 1938300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2063210 1938300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2018750 1886780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2019510 1886780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2019510 1891260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2029770 1977780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2029770 1977500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2021410 1977500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2021410 1978340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2030910 1972460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2033950 1972460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2033950 1977780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2022170 1883140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2022170 1882020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2018750 1882020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2025970 1868860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2025210 1869420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2024450 1869420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2024450 1882020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2025590 1943620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2025590 1941100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2016850 1941100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2016850 1939140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2030910 1943620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2058270 1883140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2058270 1882860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2067770 1894340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2067390 1893220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2065870 1893220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2065870 1884820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2058270 1884540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2064350 1899940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2064350 1900220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2067770 1900220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2065870 1913660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2065470 1913100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2065470 1900220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2039650 1977780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2040030 1975260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2062830 1957340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2063790 1957340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2063790 1966020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2063210 1966020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2063210 1966020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2065470 1913100
odb::dbWireEncoder_addPoint $enc 2065870 1913100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2065470 1913100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743836393738}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 136990 1995140
odb::dbWireEncoder_addPoint $enc 136990 1995980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 136990 1995980
odb::dbWireEncoder_addPoint $enc 146350 1995980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 131670 1995980
odb::dbWireEncoder_addPoint $enc 136990 1995980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 244150 2053100
odb::dbWireEncoder_addPoint $enc 244150 2054220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 456190 2075920
odb::dbWireEncoder_addPoint $enc 456190 2076340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 456190 2076340
odb::dbWireEncoder_addPoint $enc 456570 2076340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 456570 2076340
odb::dbWireEncoder_addPoint $enc 463410 2076340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 463410 2076340
odb::dbWireEncoder_addPoint $enc 463410 2078580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 452010 2081660
odb::dbWireEncoder_addPoint $enc 456570 2081660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 456570 2076340
odb::dbWireEncoder_addPoint $enc 456570 2081660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 452110 2081380
odb::dbWireEncoder_addPoint $enc 452110 2081660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 559550 2003260
odb::dbWireEncoder_addPoint $enc 559630 2003260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 559630 2003260
odb::dbWireEncoder_addPoint $enc 559630 2005500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 790590 2139060
odb::dbWireEncoder_addPoint $enc 790590 2140740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 791350 2142700
odb::dbWireEncoder_addPoint $enc 791350 2143260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 790970 2142700
odb::dbWireEncoder_addPoint $enc 791350 2142700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 790970 2142420
odb::dbWireEncoder_addPoint $enc 790970 2142700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 790590 2142420
odb::dbWireEncoder_addPoint $enc 790970 2142420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 790590 2140740
odb::dbWireEncoder_addPoint $enc 790590 2142420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 789070 2142140
odb::dbWireEncoder_addPoint $enc 789070 2143260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 789070 2142140
odb::dbWireEncoder_addPoint $enc 790590 2142140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 851770 1995140
odb::dbWireEncoder_addPoint $enc 851770 1997100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 851390 1997100
odb::dbWireEncoder_addPoint $enc 851770 1997100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 851770 1992060
odb::dbWireEncoder_addPoint $enc 854430 1992060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 851770 1992060
odb::dbWireEncoder_addPoint $enc 851770 1995140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 850630 1989260
odb::dbWireEncoder_addPoint $enc 850630 1989540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 850630 1989260
odb::dbWireEncoder_addPoint $enc 852150 1989260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 852150 1989260
odb::dbWireEncoder_addPoint $enc 852150 1992060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 855190 1986460
odb::dbWireEncoder_addPoint $enc 855190 1987020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 852150 1987020
odb::dbWireEncoder_addPoint $enc 855190 1987020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 852150 1987020
odb::dbWireEncoder_addPoint $enc 852150 1989260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 878750 2079140
odb::dbWireEncoder_addPoint $enc 878750 2082220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 878750 2082220
odb::dbWireEncoder_addPoint $enc 882170 2082220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 878750 2076620
odb::dbWireEncoder_addPoint $enc 879510 2076620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 878750 2076620
odb::dbWireEncoder_addPoint $enc 878750 2079140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 851010 2137660
odb::dbWireEncoder_addPoint $enc 851010 2137940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 851010 2137940
odb::dbWireEncoder_addPoint $enc 854750 2137940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 851010 2137940
odb::dbWireEncoder_addPoint $enc 851010 2139060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 859370 2137660
odb::dbWireEncoder_addPoint $enc 859370 2137940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 854750 2137940
odb::dbWireEncoder_addPoint $enc 859370 2137940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 862790 2141580
odb::dbWireEncoder_addPoint $enc 862790 2157540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 859370 2141580
odb::dbWireEncoder_addPoint $enc 862790 2141580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 859370 2137940
odb::dbWireEncoder_addPoint $enc 859370 2141580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 852910 2163140
odb::dbWireEncoder_addPoint $enc 853290 2163140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 853290 2162020
odb::dbWireEncoder_addPoint $enc 853290 2163140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 853290 2162020
odb::dbWireEncoder_addPoint $enc 854810 2162020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 854810 2157260
odb::dbWireEncoder_addPoint $enc 854810 2162020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 854810 2157260
odb::dbWireEncoder_addPoint $enc 862790 2157260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 146350 1995980
odb::dbWireEncoder_addPoint $enc 146350 2037980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 638030 2005500
odb::dbWireEncoder_addPoint $enc 638030 2015860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 856990 2034340
odb::dbWireEncoder_addPoint $enc 857470 2034340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 856990 2009980
odb::dbWireEncoder_addPoint $enc 856990 2034340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 851390 2009980
odb::dbWireEncoder_addPoint $enc 856990 2009980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 857470 2034340
odb::dbWireEncoder_addPoint $enc 860510 2034340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 851390 1997100
odb::dbWireEncoder_addPoint $enc 851390 2009980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 854750 2126100
odb::dbWireEncoder_addPoint $enc 854750 2137940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 854190 2126100
odb::dbWireEncoder_addPoint $enc 854750 2126100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 878370 2098460
odb::dbWireEncoder_addPoint $enc 880270 2098460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 878370 2097340
odb::dbWireEncoder_addPoint $enc 878370 2098460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 878370 2097340
odb::dbWireEncoder_addPoint $enc 882170 2097340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 882170 2082220
odb::dbWireEncoder_addPoint $enc 882170 2097340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 868110 2176020
odb::dbWireEncoder_addPoint $enc 868110 2176860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 859750 2174340
odb::dbWireEncoder_addPoint $enc 859750 2176020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 859750 2176020
odb::dbWireEncoder_addPoint $enc 868110 2176020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 852910 2174340
odb::dbWireEncoder_addPoint $enc 859750 2174340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 852910 2163140
odb::dbWireEncoder_addPoint $enc 852910 2174340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 122170 1995980
odb::dbWireEncoder_addPoint $enc 122170 1997660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 122170 1995980
odb::dbWireEncoder_addPoint $enc 131670 1995980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 251370 2054220
odb::dbWireEncoder_addPoint $enc 251370 2054780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 251370 2054780
odb::dbWireEncoder_addPoint $enc 256110 2054780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 256110 2054500
odb::dbWireEncoder_addPoint $enc 256110 2054780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 256110 2054500
odb::dbWireEncoder_addPoint $enc 269610 2054500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 269610 2052540
odb::dbWireEncoder_addPoint $enc 269610 2054500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 244150 2054220
odb::dbWireEncoder_addPoint $enc 251370 2054220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 370500 2077740
odb::dbWireEncoder_addPoint $enc 370500 2078300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 306510 2077740
odb::dbWireEncoder_addPoint $enc 370500 2077740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 449870 2081100
odb::dbWireEncoder_addPoint $enc 449870 2081380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 440910 2081100
odb::dbWireEncoder_addPoint $enc 449870 2081100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 370500 2078300
odb::dbWireEncoder_addPoint $enc 440910 2078300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 449870 2081380
odb::dbWireEncoder_addPoint $enc 452110 2081380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 433070 2163420
odb::dbWireEncoder_addPoint $enc 433070 2165660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 442130 2206260
odb::dbWireEncoder_addPoint $enc 446310 2206260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 446310 2206260
odb::dbWireEncoder_addPoint $enc 446310 2207940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 530100 2005500
odb::dbWireEncoder_addPoint $enc 559630 2005500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 497230 1993180
odb::dbWireEncoder_addPoint $enc 499510 1993180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 497230 1989540
odb::dbWireEncoder_addPoint $enc 497230 1993180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 530100 2005500
odb::dbWireEncoder_addPoint $enc 530100 2006060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 500270 2069060
odb::dbWireEncoder_addPoint $enc 500270 2073540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 498590 2069060
odb::dbWireEncoder_addPoint $enc 500270 2069060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 493430 2071580
odb::dbWireEncoder_addPoint $enc 493430 2073540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 493430 2071580
odb::dbWireEncoder_addPoint $enc 500270 2071580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 503310 2074940
odb::dbWireEncoder_addPoint $enc 503310 2076060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 500270 2074940
odb::dbWireEncoder_addPoint $enc 503310 2074940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 500270 2073540
odb::dbWireEncoder_addPoint $enc 500270 2074940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 493430 2073540
odb::dbWireEncoder_addPoint $enc 493430 2078580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 463410 2078580
odb::dbWireEncoder_addPoint $enc 493430 2078580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 559630 2003820
odb::dbWireEncoder_addPoint $enc 570000 2003820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 570000 2003260
odb::dbWireEncoder_addPoint $enc 570000 2003820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 570000 2003260
odb::dbWireEncoder_addPoint $enc 594350 2003260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 594350 2003260
odb::dbWireEncoder_addPoint $enc 594350 2005500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 594350 2005500
odb::dbWireEncoder_addPoint $enc 638030 2005500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 790590 2139060
odb::dbWireEncoder_addPoint $enc 851010 2139060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 146350 2037980
odb::dbWireEncoder_addPoint $enc 171000 2037980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 171000 2037980
odb::dbWireEncoder_addPoint $enc 171000 2038260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 440910 2078300
odb::dbWireEncoder_addPoint $enc 440910 2086200
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 429210 2109660
odb::dbWireEncoder_addPoint $enc 429210 2115540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 440910 2086200
odb::dbWireEncoder_addPoint $enc 441470 2086200
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 442130 2200100
odb::dbWireEncoder_addPoint $enc 442130 2202340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 434190 2200100
odb::dbWireEncoder_addPoint $enc 442130 2200100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 433070 2179100
odb::dbWireEncoder_addPoint $enc 433070 2185260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 442130 2202340
odb::dbWireEncoder_addPoint $enc 442130 2206260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 498590 2044700
odb::dbWireEncoder_addPoint $enc 500270 2044700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 498590 2044700
odb::dbWireEncoder_addPoint $enc 498590 2069060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 656510 2015580
odb::dbWireEncoder_addPoint $enc 656510 2015860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 656510 2015580
odb::dbWireEncoder_addPoint $enc 660990 2015580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 660990 2015580
odb::dbWireEncoder_addPoint $enc 660990 2015860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 660990 2015860
odb::dbWireEncoder_addPoint $enc 689700 2015860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 689700 2015300
odb::dbWireEncoder_addPoint $enc 689700 2015860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 638030 2015860
odb::dbWireEncoder_addPoint $enc 656510 2015860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 849300 2009980
odb::dbWireEncoder_addPoint $enc 851390 2009980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 809400 2009980
odb::dbWireEncoder_addPoint $enc 809400 2010540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 809400 2010540
odb::dbWireEncoder_addPoint $enc 849300 2010540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 849300 2009980
odb::dbWireEncoder_addPoint $enc 849300 2010540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 499130 2000740
odb::dbWireEncoder_addPoint $enc 499130 2002140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 499130 2002140
odb::dbWireEncoder_addPoint $enc 500270 2002140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 499130 1998220
odb::dbWireEncoder_addPoint $enc 499510 1998220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 499130 1998220
odb::dbWireEncoder_addPoint $enc 499130 2000740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 512430 2006060
odb::dbWireEncoder_addPoint $enc 512430 2006340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 500270 2006060
odb::dbWireEncoder_addPoint $enc 512430 2006060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 517750 2007740
odb::dbWireEncoder_addPoint $enc 517750 2008860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 511670 2007740
odb::dbWireEncoder_addPoint $enc 517750 2007740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 511670 2006620
odb::dbWireEncoder_addPoint $enc 511670 2007740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 511670 2006620
odb::dbWireEncoder_addPoint $enc 512430 2006620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 512430 2006340
odb::dbWireEncoder_addPoint $enc 512430 2006620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 518190 2006060
odb::dbWireEncoder_addPoint $enc 518190 2007740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 517750 2007740
odb::dbWireEncoder_addPoint $enc 518190 2007740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 499510 1993180
odb::dbWireEncoder_addPoint $enc 499510 1998220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 500270 2002140
odb::dbWireEncoder_addPoint $enc 500270 2044700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 518190 2006060
odb::dbWireEncoder_addPoint $enc 530100 2006060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 901550 2181620
odb::dbWireEncoder_addPoint $enc 901550 2182460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 901170 2181620
odb::dbWireEncoder_addPoint $enc 901550 2181620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 901170 2180220
odb::dbWireEncoder_addPoint $enc 901170 2181620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 900410 2180220
odb::dbWireEncoder_addPoint $enc 901170 2180220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 900410 2179660
odb::dbWireEncoder_addPoint $enc 900410 2180220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 893570 2179660
odb::dbWireEncoder_addPoint $enc 900410 2179660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 893570 2175740
odb::dbWireEncoder_addPoint $enc 893570 2179660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 890150 2175740
odb::dbWireEncoder_addPoint $enc 893570 2175740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 890150 2175740
odb::dbWireEncoder_addPoint $enc 890150 2176020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 904210 2184140
odb::dbWireEncoder_addPoint $enc 904210 2185540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 901550 2184140
odb::dbWireEncoder_addPoint $enc 904210 2184140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 901550 2182460
odb::dbWireEncoder_addPoint $enc 901550 2184140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 906490 2169580
odb::dbWireEncoder_addPoint $enc 906490 2170420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 901790 2170420
odb::dbWireEncoder_addPoint $enc 906490 2170420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 901790 2170420
odb::dbWireEncoder_addPoint $enc 901790 2180220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 901170 2180220
odb::dbWireEncoder_addPoint $enc 901790 2180220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 868110 2176020
odb::dbWireEncoder_addPoint $enc 890150 2176020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 835050 2058700
odb::dbWireEncoder_addPoint $enc 835050 2062340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 834670 2058700
odb::dbWireEncoder_addPoint $enc 835050 2058700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 834670 2053100
odb::dbWireEncoder_addPoint $enc 834670 2058700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 829350 2059260
odb::dbWireEncoder_addPoint $enc 835050 2059260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 827070 2058700
odb::dbWireEncoder_addPoint $enc 827070 2059260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 827070 2058700
odb::dbWireEncoder_addPoint $enc 829350 2058700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 829350 2058700
odb::dbWireEncoder_addPoint $enc 829350 2059260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 834030 2062060
odb::dbWireEncoder_addPoint $enc 835050 2062060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 879890 2048060
odb::dbWireEncoder_addPoint $enc 881790 2048060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 881790 2048060
odb::dbWireEncoder_addPoint $enc 881790 2052260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 879510 2052260
odb::dbWireEncoder_addPoint $enc 881790 2052260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 877990 2039940
odb::dbWireEncoder_addPoint $enc 877990 2040220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 877990 2040220
odb::dbWireEncoder_addPoint $enc 879890 2040220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 879890 2040220
odb::dbWireEncoder_addPoint $enc 879890 2048060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 877990 2036580
odb::dbWireEncoder_addPoint $enc 877990 2039940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 879510 2052260
odb::dbWireEncoder_addPoint $enc 879510 2076620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 766270 2009980
odb::dbWireEncoder_addPoint $enc 766270 2015300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 765890 2015860
odb::dbWireEncoder_addPoint $enc 765890 2023140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 765890 2015300
odb::dbWireEncoder_addPoint $enc 765890 2015860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 689700 2015300
odb::dbWireEncoder_addPoint $enc 766270 2015300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 766270 2009980
odb::dbWireEncoder_addPoint $enc 809400 2009980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 217170 2053660
odb::dbWireEncoder_addPoint $enc 217550 2053660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 217170 2050020
odb::dbWireEncoder_addPoint $enc 217170 2053660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 217170 2050020
odb::dbWireEncoder_addPoint $enc 217550 2050020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 217550 2037700
odb::dbWireEncoder_addPoint $enc 217550 2050020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 209190 2037700
odb::dbWireEncoder_addPoint $enc 217550 2037700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 209190 2037700
odb::dbWireEncoder_addPoint $enc 209190 2038260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 171000 2038260
odb::dbWireEncoder_addPoint $enc 209190 2038260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 217170 2053100
odb::dbWireEncoder_addPoint $enc 244150 2053100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 279490 2052540
odb::dbWireEncoder_addPoint $enc 279490 2052820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 279490 2052820
odb::dbWireEncoder_addPoint $enc 305950 2052820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 305950 2052820
odb::dbWireEncoder_addPoint $enc 305950 2057580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 305950 2057580
odb::dbWireEncoder_addPoint $enc 306510 2057580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 269610 2052540
odb::dbWireEncoder_addPoint $enc 279490 2052540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 306510 2057580
odb::dbWireEncoder_addPoint $enc 306510 2077740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 441470 2115540
odb::dbWireEncoder_addPoint $enc 441470 2137100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 440910 2137100
odb::dbWireEncoder_addPoint $enc 441470 2137100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 440910 2137100
odb::dbWireEncoder_addPoint $enc 440910 2148860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 440230 2148860
odb::dbWireEncoder_addPoint $enc 440910 2148860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 448210 2115260
odb::dbWireEncoder_addPoint $enc 448210 2115540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 441470 2115540
odb::dbWireEncoder_addPoint $enc 448210 2115540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 429210 2115540
odb::dbWireEncoder_addPoint $enc 441470 2115540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 441470 2086200
odb::dbWireEncoder_addPoint $enc 441470 2115540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 862030 2053380
odb::dbWireEncoder_addPoint $enc 862030 2053660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 843410 2053380
odb::dbWireEncoder_addPoint $enc 862030 2053380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 843410 2053100
odb::dbWireEncoder_addPoint $enc 843410 2053380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 860510 2036860
odb::dbWireEncoder_addPoint $enc 860510 2037420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 860510 2037420
odb::dbWireEncoder_addPoint $enc 860510 2038540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 860130 2038540
odb::dbWireEncoder_addPoint $enc 860510 2038540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 860130 2038540
odb::dbWireEncoder_addPoint $enc 860130 2053380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 869630 2036860
odb::dbWireEncoder_addPoint $enc 869630 2038260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 860510 2038260
odb::dbWireEncoder_addPoint $enc 869630 2038260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 869630 2036580
odb::dbWireEncoder_addPoint $enc 869630 2036860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 834670 2053100
odb::dbWireEncoder_addPoint $enc 843410 2053100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 860510 2034340
odb::dbWireEncoder_addPoint $enc 860510 2036860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 869630 2036580
odb::dbWireEncoder_addPoint $enc 877990 2036580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 443270 2162580
odb::dbWireEncoder_addPoint $enc 443270 2163140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 433630 2162580
odb::dbWireEncoder_addPoint $enc 443270 2162580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 433630 2162580
odb::dbWireEncoder_addPoint $enc 433630 2163420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 439850 2149700
odb::dbWireEncoder_addPoint $enc 440230 2149700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 439850 2149700
odb::dbWireEncoder_addPoint $enc 439850 2149980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 439470 2149980
odb::dbWireEncoder_addPoint $enc 439850 2149980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 439470 2149980
odb::dbWireEncoder_addPoint $enc 439470 2162580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 433630 2165660
odb::dbWireEncoder_addPoint $enc 433630 2179100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 433070 2163420
odb::dbWireEncoder_addPoint $enc 433630 2163420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 433070 2165660
odb::dbWireEncoder_addPoint $enc 433630 2165660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 433070 2179100
odb::dbWireEncoder_addPoint $enc 433630 2179100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 433070 2185260
odb::dbWireEncoder_addPoint $enc 434190 2185260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 434190 2185260
odb::dbWireEncoder_addPoint $enc 434190 2200100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 440230 2148860
odb::dbWireEncoder_addPoint $enc 440230 2149700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 854430 2092580
odb::dbWireEncoder_addPoint $enc 854430 2092860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 854190 2092580
odb::dbWireEncoder_addPoint $enc 854430 2092580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 854810 2090340
odb::dbWireEncoder_addPoint $enc 854810 2090900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 854430 2090900
odb::dbWireEncoder_addPoint $enc 854810 2090900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 854430 2090900
odb::dbWireEncoder_addPoint $enc 854430 2092580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 869630 2097060
odb::dbWireEncoder_addPoint $enc 869630 2097340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 854190 2097060
odb::dbWireEncoder_addPoint $enc 869630 2097060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 834290 2070180
odb::dbWireEncoder_addPoint $enc 834290 2070460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 834030 2070180
odb::dbWireEncoder_addPoint $enc 834290 2070180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 833150 2072140
odb::dbWireEncoder_addPoint $enc 833150 2073400
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 833150 2072140
odb::dbWireEncoder_addPoint $enc 834030 2072140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 834030 2070180
odb::dbWireEncoder_addPoint $enc 834030 2072140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 834030 2062060
odb::dbWireEncoder_addPoint $enc 834030 2070180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 854190 2092580
odb::dbWireEncoder_addPoint $enc 854190 2126100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 869630 2097340
odb::dbWireEncoder_addPoint $enc 878370 2097340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 136990 1995140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 136990 1995980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 146350 1995980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 131670 1995980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 131670 1995980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 306510 2077740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 456190 2075920
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 456570 2076340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 463410 2076340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 463410 2078580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 452010 2081660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 452010 2081660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 456570 2081660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 559550 2003260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 559550 2003260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 559630 2003260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 559630 2005500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 559630 2003820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 638030 2005500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 790590 2140740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 790590 2139060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 791350 2143260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 789070 2143260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 789070 2142140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 790590 2142140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 851770 1995140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 851390 1997100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 854430 1992060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 854430 1992060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 851770 1992060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 850630 1989540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 850630 1989260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 852150 1989260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 852150 1992060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 855190 1986460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 855190 1987020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 852150 1987020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 878750 2079140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 878750 2082220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 882170 2082220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 851010 2137660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 851010 2137940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 854750 2137940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 851010 2139060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 859370 2137660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 859370 2137940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 862790 2157540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 862790 2141580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 859370 2141580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 852910 2163140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 853290 2162020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 854810 2162020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 854810 2157260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 862790 2157260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 146350 2037980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 638030 2015860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 851390 2009980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 857470 2034340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 857470 2034340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 856990 2034340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 856990 2009980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 860510 2034340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 880270 2098460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 880270 2098460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 878370 2098460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 878370 2097340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 882170 2097340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 868110 2176860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 868110 2176020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 859750 2174340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 859750 2176020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 852910 2174340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 859750 2174340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 122170 1995980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 122170 1997660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 269610 2054500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 269610 2052540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 440910 2078300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 440910 2081100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 442130 2206260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 446310 2206260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 446310 2207940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 499510 1993180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 497230 1993180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 497230 1989540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 500270 2073540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 500270 2069060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 498590 2069060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 493430 2073540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 493430 2071580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 500270 2071580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 503310 2076060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 503310 2074940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 500270 2074940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 493430 2078580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 594350 2003260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 594350 2005500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 429210 2109660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 429210 2115540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 442130 2202340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 442130 2200100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 434190 2200100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 433070 2185260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 498590 2044700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 500270 2044700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 499130 2000740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 499130 2002140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 500270 2002140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 512430 2006340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 512430 2006340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 500270 2006060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 517750 2008860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 517750 2007740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 511670 2007740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 511670 2006620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 518190 2006060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 518190 2007740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 901550 2182460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 901170 2180220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 893570 2179660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 893570 2175740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 904210 2185540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 904210 2184140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 901550 2184140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 906490 2169580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 906490 2170420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 901790 2170420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 901790 2180220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 835050 2062340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 834670 2053100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 829350 2059260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 829350 2059260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 835050 2059260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 827070 2059260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 827070 2058700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 829350 2058700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 834030 2062060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 835050 2062060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 879890 2048060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 879890 2048060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 881790 2048060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 881790 2052260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 879510 2052260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 877990 2039940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 877990 2040220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 879890 2040220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 877990 2036580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 766270 2015300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 766270 2009980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 765890 2023140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 765890 2015860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 217550 2053660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 217550 2037700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 217170 2053100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 305950 2052820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 440230 2148860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 441470 2115540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 440910 2148860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 440230 2148860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 448210 2115260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 448210 2115540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 862030 2053660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 862030 2053380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 860510 2036860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 860510 2037420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 860130 2038540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 860130 2053380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 869630 2036860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 869630 2038260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 869630 2036580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 443270 2163140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 443270 2162580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 433630 2162580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 439470 2162580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 434190 2185260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 854430 2092860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 854430 2092580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 854190 2092580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 854810 2090340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 854190 2097060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 834290 2070460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 834290 2070180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 834030 2070180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 833150 2073400
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 833150 2072140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 834030 2072140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 851390 1997100
odb::dbWireEncoder_addPoint $enc 851770 1997100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 851390 1997100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743838363530}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2446830 1583820
odb::dbWireEncoder_addPoint $enc 2446830 1584140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 2446830 1584140
odb::dbWireEncoder_addPoint $enc 2448190 1584140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2448530 1583820
odb::dbWireEncoder_addPoint $enc 2448530 1584100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2446830 1583820
odb::dbWireEncoder_addPoint $enc 2448530 1583820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 2446830 1681740
odb::dbWireEncoder_addPoint $enc 2448190 1681740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2445490 1682380
odb::dbWireEncoder_addPoint $enc 2445490 1687140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2445490 1682380
odb::dbWireEncoder_addPoint $enc 2445710 1682380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2445710 1681820
odb::dbWireEncoder_addPoint $enc 2445710 1682380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2445710 1681820
odb::dbWireEncoder_addPoint $enc 2446830 1681820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2447390 1737740
odb::dbWireEncoder_addPoint $enc 2447390 1740060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2446830 1737740
odb::dbWireEncoder_addPoint $enc 2447390 1737740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal8] ROUTED
odb::dbWireEncoder_addPoint $enc 2448190 1584140
odb::dbWireEncoder_addPoint $enc 2448190 1681740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2446830 1681740
odb::dbWireEncoder_addPoint $enc 2446830 1737740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2360590 1575140
odb::dbWireEncoder_addPoint $enc 2360750 1575140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2360590 1575140
odb::dbWireEncoder_addPoint $enc 2360590 1575420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2347150 1575420
odb::dbWireEncoder_addPoint $enc 2360590 1575420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2336810 1575420
odb::dbWireEncoder_addPoint $enc 2347150 1575420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2336810 1575140
odb::dbWireEncoder_addPoint $enc 2336810 1575420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2338750 1809740
odb::dbWireEncoder_addPoint $enc 2341550 1809740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2338750 1809740
odb::dbWireEncoder_addPoint $enc 2338750 1830780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2338750 1830780
odb::dbWireEncoder_addPoint $enc 2342110 1830780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2341750 1916740
odb::dbWireEncoder_addPoint $enc 2341750 1917300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2341750 1917300
odb::dbWireEncoder_addPoint $enc 2342110 1917300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1917020
odb::dbWireEncoder_addPoint $enc 2342110 1917300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2341550 1924940
odb::dbWireEncoder_addPoint $enc 2342110 1924940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2341550 1916940
odb::dbWireEncoder_addPoint $enc 2341550 1924940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2341550 1916940
odb::dbWireEncoder_addPoint $enc 2342110 1916940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2430670 1580740
odb::dbWireEncoder_addPoint $enc 2431150 1580740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2431150 1575980
odb::dbWireEncoder_addPoint $enc 2431150 1580740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2414910 1575980
odb::dbWireEncoder_addPoint $enc 2431150 1575980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2414910 1575420
odb::dbWireEncoder_addPoint $enc 2414910 1575980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2431150 1580740
odb::dbWireEncoder_addPoint $enc 2431150 1583820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2360590 1575420
odb::dbWireEncoder_addPoint $enc 2414910 1575420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2431150 1583820
odb::dbWireEncoder_addPoint $enc 2446830 1583820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2445300 1740060
odb::dbWireEncoder_addPoint $enc 2447390 1740060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2441790 1740060
odb::dbWireEncoder_addPoint $enc 2442450 1740060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2445300 1740060
odb::dbWireEncoder_addPoint $enc 2445300 1740620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2441790 1740620
odb::dbWireEncoder_addPoint $enc 2445300 1740620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2341550 1789340
odb::dbWireEncoder_addPoint $enc 2341550 1809740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1830780
odb::dbWireEncoder_addPoint $enc 2342110 1917020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2342130 1944740
odb::dbWireEncoder_addPoint $enc 2342130 1945020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1945020
odb::dbWireEncoder_addPoint $enc 2342130 1945020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1942780
odb::dbWireEncoder_addPoint $enc 2342110 1945020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1941660
odb::dbWireEncoder_addPoint $enc 2352010 1941660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1941660
odb::dbWireEncoder_addPoint $enc 2342110 1942780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1924940
odb::dbWireEncoder_addPoint $enc 2342110 1942780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2341550 1789340
odb::dbWireEncoder_addPoint $enc 2405400 1789340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2405400 1788220
odb::dbWireEncoder_addPoint $enc 2405400 1789340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2405400 1788220
odb::dbWireEncoder_addPoint $enc 2441790 1788220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2441790 1740060
odb::dbWireEncoder_addPoint $enc 2441790 1788220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2446830 1583820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2446830 1584140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via6_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 2448190 1584140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via7_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2448530 1584100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2448530 1583820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2446830 1583820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2446830 1583820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2446830 1681740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via6_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 2448190 1681740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via7_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2445490 1687140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2445490 1682380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2445710 1682380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2445710 1681820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2446830 1681820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2447390 1740060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2360750 1575140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2360750 1575140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2360590 1575140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2360590 1575420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2347150 1575420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2347150 1575420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2336810 1575420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2336810 1575140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2338750 1830780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1830780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2341750 1916740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1917300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1917020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1917020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2430670 1580740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2430670 1580740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2431150 1580740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2431150 1575980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2431150 1583820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2442450 1740060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2442450 1740060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2441790 1740060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2441790 1740620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2341550 1789340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2342130 1944740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2342130 1945020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1945020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1942780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1942780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2352010 1941660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2352010 1941660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1941660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2441790 1788220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1917300
odb::dbWireEncoder_addPoint $enc 2341750 1917300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2342110 1917300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743838383332}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1571550 1423380
odb::dbWireEncoder_addPoint $enc 1576430 1423380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1576430 1423380
odb::dbWireEncoder_addPoint $enc 1576430 1425340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1576430 1425340
odb::dbWireEncoder_addPoint $enc 1576590 1425340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1487780
odb::dbWireEncoder_addPoint $enc 1576590 1487780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1576590 1487780
odb::dbWireEncoder_addPoint $enc 1576590 1500100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1500100
odb::dbWireEncoder_addPoint $enc 1576590 1500100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1573790 1591100
odb::dbWireEncoder_addPoint $enc 1574910 1591100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1574350 1651020
odb::dbWireEncoder_addPoint $enc 1574910 1651020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1651020
odb::dbWireEncoder_addPoint $enc 1574910 1677900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1677900
odb::dbWireEncoder_addPoint $enc 1575290 1677900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1575290 1677900
odb::dbWireEncoder_addPoint $enc 1575290 1681820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1681820
odb::dbWireEncoder_addPoint $enc 1575290 1681820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1568450 1401820
odb::dbWireEncoder_addPoint $enc 1568450 1405740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1568070 1401820
odb::dbWireEncoder_addPoint $enc 1568450 1401820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1568070 1398460
odb::dbWireEncoder_addPoint $enc 1568070 1401820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1568450 1405740
odb::dbWireEncoder_addPoint $enc 1571550 1405740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1571550 1405740
odb::dbWireEncoder_addPoint $enc 1571550 1423380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1574150 1454180
odb::dbWireEncoder_addPoint $enc 1574150 1454460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574150 1454180
odb::dbWireEncoder_addPoint $enc 1574910 1454180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1576430 1448300
odb::dbWireEncoder_addPoint $enc 1576590 1448300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1576430 1448300
odb::dbWireEncoder_addPoint $enc 1576430 1450260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1450260
odb::dbWireEncoder_addPoint $enc 1576430 1450260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1450260
odb::dbWireEncoder_addPoint $enc 1574910 1454180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1454180
odb::dbWireEncoder_addPoint $enc 1574910 1487780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1576590 1425340
odb::dbWireEncoder_addPoint $enc 1576590 1448300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1573790 1565340
odb::dbWireEncoder_addPoint $enc 1574910 1565340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1573790 1565340
odb::dbWireEncoder_addPoint $enc 1573790 1591100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1500100
odb::dbWireEncoder_addPoint $enc 1574910 1565340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1574350 1608740
odb::dbWireEncoder_addPoint $enc 1574910 1608740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1574350 1608740
odb::dbWireEncoder_addPoint $enc 1574350 1651020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1591100
odb::dbWireEncoder_addPoint $enc 1574910 1608740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1574350 1705900
odb::dbWireEncoder_addPoint $enc 1574910 1705900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1681820
odb::dbWireEncoder_addPoint $enc 1574910 1705900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1573390 1778700
odb::dbWireEncoder_addPoint $enc 1574350 1778700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1573390 1778700
odb::dbWireEncoder_addPoint $enc 1573390 1779260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1574350 1705900
odb::dbWireEncoder_addPoint $enc 1574350 1778700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1563130 1405180
odb::dbWireEncoder_addPoint $enc 1563130 1405740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1563130 1405740
odb::dbWireEncoder_addPoint $enc 1568450 1405740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1571550 1423380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1576430 1423380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1576430 1425340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1576590 1425340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1487780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1576590 1487780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1576590 1500100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1500100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1573790 1591100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1591100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1677900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1575290 1681820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1681820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1568450 1405740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1568070 1398460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1571550 1405740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1574150 1454460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1574150 1454180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1454180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1576590 1448300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1576430 1448300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1576430 1450260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1450260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1573790 1565340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1565340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574350 1778700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1573390 1778700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1573390 1779260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1563130 1405180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1563130 1405740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1677900
odb::dbWireEncoder_addPoint $enc 1575290 1677900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 1677900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743935323630}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 91390 572460
odb::dbWireEncoder_addPoint $enc 92150 572460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 92530 595140
odb::dbWireEncoder_addPoint $enc 92530 596260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 92150 596260
odb::dbWireEncoder_addPoint $enc 92530 596260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 91390 592060
odb::dbWireEncoder_addPoint $enc 91770 592060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 91770 592060
odb::dbWireEncoder_addPoint $enc 91770 596260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 91770 596260
odb::dbWireEncoder_addPoint $enc 92150 596260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 91390 587580
odb::dbWireEncoder_addPoint $enc 91770 587580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 91770 587580
odb::dbWireEncoder_addPoint $enc 91770 592060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 91390 572460
odb::dbWireEncoder_addPoint $enc 91390 587580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 55670 646940
odb::dbWireEncoder_addPoint $enc 56430 646940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 55670 644980
odb::dbWireEncoder_addPoint $enc 55670 646940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 55670 644980
odb::dbWireEncoder_addPoint $enc 56810 644980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 56810 639940
odb::dbWireEncoder_addPoint $enc 56810 644980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 56430 639940
odb::dbWireEncoder_addPoint $enc 56810 639940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 54910 670460
odb::dbWireEncoder_addPoint $enc 54910 678020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 54150 664860
odb::dbWireEncoder_addPoint $enc 54910 664860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 54910 664860
odb::dbWireEncoder_addPoint $enc 54910 670460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 53390 653380
odb::dbWireEncoder_addPoint $enc 53390 660100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 53390 660100
odb::dbWireEncoder_addPoint $enc 53770 660100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 53770 660100
odb::dbWireEncoder_addPoint $enc 53770 664860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 53770 664860
odb::dbWireEncoder_addPoint $enc 54150 664860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 53390 653380
odb::dbWireEncoder_addPoint $enc 56430 653380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 72770 658700
odb::dbWireEncoder_addPoint $enc 72770 659260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 72390 658700
odb::dbWireEncoder_addPoint $enc 72770 658700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 72390 653380
odb::dbWireEncoder_addPoint $enc 72390 658700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 56430 653380
odb::dbWireEncoder_addPoint $enc 72390 653380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 56430 646940
odb::dbWireEncoder_addPoint $enc 56430 653380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 92150 570000
odb::dbWireEncoder_addPoint $enc 92150 572460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 92530 568820
odb::dbWireEncoder_addPoint $enc 93670 568820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 93670 564060
odb::dbWireEncoder_addPoint $enc 93670 568820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 93670 564060
odb::dbWireEncoder_addPoint $enc 94050 564060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 92150 570000
odb::dbWireEncoder_addPoint $enc 92530 570000
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 92530 568820
odb::dbWireEncoder_addPoint $enc 92530 570000
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 51110 678300
odb::dbWireEncoder_addPoint $enc 51110 679140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 50730 678300
odb::dbWireEncoder_addPoint $enc 51110 678300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 50730 676340
odb::dbWireEncoder_addPoint $enc 50730 678300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 46930 676340
odb::dbWireEncoder_addPoint $enc 50730 676340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 46930 676060
odb::dbWireEncoder_addPoint $enc 46930 676340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 51110 678020
odb::dbWireEncoder_addPoint $enc 51110 678300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 46930 653380
odb::dbWireEncoder_addPoint $enc 46930 653660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 46930 653380
odb::dbWireEncoder_addPoint $enc 53390 653380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 51110 678020
odb::dbWireEncoder_addPoint $enc 54910 678020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 97470 636300
odb::dbWireEncoder_addPoint $enc 97470 636860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 97070 636300
odb::dbWireEncoder_addPoint $enc 97470 636300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 97070 613900
odb::dbWireEncoder_addPoint $enc 97070 636300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 92150 613900
odb::dbWireEncoder_addPoint $enc 97070 613900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 79990 636300
odb::dbWireEncoder_addPoint $enc 79990 636580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 79990 636300
odb::dbWireEncoder_addPoint $enc 97070 636300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 92150 596260
odb::dbWireEncoder_addPoint $enc 92150 613900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 57570 636580
odb::dbWireEncoder_addPoint $enc 57570 636860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 56430 636580
odb::dbWireEncoder_addPoint $enc 57570 636580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 50730 628740
odb::dbWireEncoder_addPoint $enc 50730 629300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 50730 629300
odb::dbWireEncoder_addPoint $enc 53770 629300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 53770 629300
odb::dbWireEncoder_addPoint $enc 53770 636580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 53770 636580
odb::dbWireEncoder_addPoint $enc 56430 636580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 56430 636580
odb::dbWireEncoder_addPoint $enc 56430 639940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 57570 636580
odb::dbWireEncoder_addPoint $enc 79990 636580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 92530 595140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 91390 592060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 56430 639940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 55670 644980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 56810 644980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 54910 670460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 54910 678020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 54150 664860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 53390 653380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 56430 653380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 72770 659260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 72390 653380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 92530 568820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 92530 568820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 93670 568820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 94050 564060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 51110 679140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 50730 676340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 46930 676340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 46930 676060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 51110 678020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 46930 653380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 46930 653660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 97470 636860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 97070 636300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 97070 613900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 92150 613900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 57570 636860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 57570 636580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 56430 636580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 50730 628740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 50730 629300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 53770 629300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 53770 636580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 97070 636300
odb::dbWireEncoder_addPoint $enc 97470 636300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 97070 636300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743938333837}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1280790 942340
odb::dbWireEncoder_addPoint $enc 1280790 944860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1342730 559580
odb::dbWireEncoder_addPoint $enc 1342730 560700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1342730 560700
odb::dbWireEncoder_addPoint $enc 1343070 560700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1342730 560700
odb::dbWireEncoder_addPoint $enc 1342730 561820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1343070 575820
odb::dbWireEncoder_addPoint $enc 1343070 576100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1341970 576100
odb::dbWireEncoder_addPoint $enc 1343070 576100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1341970 576100
odb::dbWireEncoder_addPoint $enc 1341970 578340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1343070 560700
odb::dbWireEncoder_addPoint $enc 1343070 575820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1338170 835660
odb::dbWireEncoder_addPoint $enc 1338170 835940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1334670 835660
odb::dbWireEncoder_addPoint $enc 1338170 835660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1334670 835660
odb::dbWireEncoder_addPoint $enc 1334670 837340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1328290 813540
odb::dbWireEncoder_addPoint $enc 1328290 813820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1328290 813820
odb::dbWireEncoder_addPoint $enc 1334110 813820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1334110 813820
odb::dbWireEncoder_addPoint $enc 1334110 835660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1334110 835660
odb::dbWireEncoder_addPoint $enc 1334670 835660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1329810 813540
odb::dbWireEncoder_addPoint $enc 1329810 813820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1333990 810460
odb::dbWireEncoder_addPoint $enc 1334110 810460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1334110 810460
odb::dbWireEncoder_addPoint $enc 1334110 813820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1328100 561820
odb::dbWireEncoder_addPoint $enc 1342730 561820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1304730 562100
odb::dbWireEncoder_addPoint $enc 1304730 564060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1304730 562100
odb::dbWireEncoder_addPoint $enc 1328100 562100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1328100 561820
odb::dbWireEncoder_addPoint $enc 1328100 562100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1302750 644700
odb::dbWireEncoder_addPoint $enc 1304990 644700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1280410 942340
odb::dbWireEncoder_addPoint $enc 1288200 942340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1288200 942060
odb::dbWireEncoder_addPoint $enc 1288200 942340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1288200 942060
odb::dbWireEncoder_addPoint $enc 1290990 942060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1290990 934220
odb::dbWireEncoder_addPoint $enc 1290990 942060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1290430 934220
odb::dbWireEncoder_addPoint $enc 1290990 934220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1302750 609900
odb::dbWireEncoder_addPoint $enc 1302750 644700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1302750 609900
odb::dbWireEncoder_addPoint $enc 1303310 609900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1303310 577780
odb::dbWireEncoder_addPoint $enc 1303310 609900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1303310 577780
odb::dbWireEncoder_addPoint $enc 1304990 577780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1304990 562100
odb::dbWireEncoder_addPoint $enc 1304990 577780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1300550 651140
odb::dbWireEncoder_addPoint $enc 1300550 653100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1300550 653100
odb::dbWireEncoder_addPoint $enc 1301630 653100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1301070 653100
odb::dbWireEncoder_addPoint $enc 1301630 653100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1301630 653100
odb::dbWireEncoder_addPoint $enc 1304990 653100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1304990 644700
odb::dbWireEncoder_addPoint $enc 1304990 653100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1309670 836220
odb::dbWireEncoder_addPoint $enc 1309670 837340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1307790 837340
odb::dbWireEncoder_addPoint $enc 1309670 837340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1301070 837340
odb::dbWireEncoder_addPoint $enc 1307790 837340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1327390 837340
odb::dbWireEncoder_addPoint $enc 1327390 837900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1307790 837900
odb::dbWireEncoder_addPoint $enc 1327390 837900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1307790 837340
odb::dbWireEncoder_addPoint $enc 1307790 837900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1327390 837340
odb::dbWireEncoder_addPoint $enc 1334670 837340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1290430 897820
odb::dbWireEncoder_addPoint $enc 1301070 897820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1290430 897820
odb::dbWireEncoder_addPoint $enc 1290430 934220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 1301070 653100
odb::dbWireEncoder_addPoint $enc 1301070 897820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1280410 942340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1280410 942340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1280790 944860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1280790 942340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1342730 559580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1343070 560700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1342730 561820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1343070 575820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1341970 576100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1341970 578340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1338170 835940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1338170 835660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1334670 835660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1334670 837340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1328290 813540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1328290 813820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1334110 813820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1329810 813540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1329810 813820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1333990 810460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1333990 810460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1334110 810460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1304730 564060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1304730 562100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1304990 562100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1302750 644700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1304990 644700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1290990 942060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1303310 577780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1304990 577780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1300550 651140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1300550 653100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1301630 653100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1301630 653100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1301070 653100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1304990 653100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1309670 836220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1309670 837340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1307790 837340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1307790 837340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1301070 837340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1290430 897820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1301070 897820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1343070 560700
odb::dbWireEncoder_addPoint $enc 1342730 560700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1343070 560700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6f706572616e645f625b325d5b335d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2165810 639660
odb::dbWireEncoder_addPoint $enc 2165810 642180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2163910 639660
odb::dbWireEncoder_addPoint $enc 2165810 639660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2163910 639660
odb::dbWireEncoder_addPoint $enc 2163910 639800
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2162390 664860
odb::dbWireEncoder_addPoint $enc 2165810 664860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2165810 642180
odb::dbWireEncoder_addPoint $enc 2165810 664860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2187090 642180
odb::dbWireEncoder_addPoint $enc 2187090 642460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2184810 611660
odb::dbWireEncoder_addPoint $enc 2184810 611940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2165810 642180
odb::dbWireEncoder_addPoint $enc 2187090 642180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2205330 684740
odb::dbWireEncoder_addPoint $enc 2205330 685020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2200770 685020
odb::dbWireEncoder_addPoint $enc 2205330 685020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2200770 684180
odb::dbWireEncoder_addPoint $enc 2200770 685020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2200770 684180
odb::dbWireEncoder_addPoint $enc 2201150 684180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2199250 687260
odb::dbWireEncoder_addPoint $enc 2200770 687260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2200770 685020
odb::dbWireEncoder_addPoint $enc 2200770 687260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2197730 645540
odb::dbWireEncoder_addPoint $enc 2197730 645820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2197730 645820
odb::dbWireEncoder_addPoint $enc 2198190 645820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2198190 645820
odb::dbWireEncoder_addPoint $enc 2198190 676060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2198190 676060
odb::dbWireEncoder_addPoint $enc 2201150 676060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2196590 645820
odb::dbWireEncoder_addPoint $enc 2197730 645820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196210 642180
odb::dbWireEncoder_addPoint $enc 2196210 645820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196210 645820
odb::dbWireEncoder_addPoint $enc 2196590 645820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2196210 642180
odb::dbWireEncoder_addPoint $enc 2196970 642180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2187090 642180
odb::dbWireEncoder_addPoint $enc 2196210 642180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2201150 676060
odb::dbWireEncoder_addPoint $enc 2201150 684180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2196210 611100
odb::dbWireEncoder_addPoint $enc 2196210 611660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2198490 636300
odb::dbWireEncoder_addPoint $enc 2198490 636860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2198190 636300
odb::dbWireEncoder_addPoint $enc 2198490 636300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2198190 611660
odb::dbWireEncoder_addPoint $enc 2198190 636300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2196210 611660
odb::dbWireEncoder_addPoint $enc 2198190 611660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2196970 636300
odb::dbWireEncoder_addPoint $enc 2198190 636300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2184810 611660
odb::dbWireEncoder_addPoint $enc 2196210 611660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196970 636300
odb::dbWireEncoder_addPoint $enc 2196970 642180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2165810 642180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2165810 639660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2163910 639660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2163910 639800
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2165810 664860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2162390 664860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2162390 664860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2187090 642460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2187090 642180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2184810 611940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2184810 611660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2205330 684740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2205330 685020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2200770 685020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2199250 687260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2199250 687260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2200770 687260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2201150 676060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2197730 645540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2197730 645820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2198190 645820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2198190 676060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2201150 676060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2196590 645820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196590 645820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196210 642180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196970 642180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2196210 611100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196210 611100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2198490 636860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2198190 636300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2198190 611660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196970 636300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2198190 636300
odb::dbWireEncoder_addPoint $enc 2198490 636300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2198190 636300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3131395d5b32315d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 71630 1914500
odb::dbWireEncoder_addPoint $enc 71630 1917300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 71310 1917300
odb::dbWireEncoder_addPoint $enc 71630 1917300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 72010 1913660
odb::dbWireEncoder_addPoint $enc 72010 1914500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 71630 1914500
odb::dbWireEncoder_addPoint $enc 72010 1914500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 68510 1966860
odb::dbWireEncoder_addPoint $enc 70750 1966860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 65710 2079420
odb::dbWireEncoder_addPoint $enc 66270 2079420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 65710 2051420
odb::dbWireEncoder_addPoint $enc 65710 2079420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 65710 2051420
odb::dbWireEncoder_addPoint $enc 68510 2051420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 70750 1928780
odb::dbWireEncoder_addPoint $enc 71310 1928780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 70750 1928780
odb::dbWireEncoder_addPoint $enc 70750 1966860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 71310 1917300
odb::dbWireEncoder_addPoint $enc 71310 1928780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 68510 1966860
odb::dbWireEncoder_addPoint $enc 68510 2051420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 62510 2092860
odb::dbWireEncoder_addPoint $enc 62510 2093420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 62510 2093420
odb::dbWireEncoder_addPoint $enc 66270 2093420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 67830 2101540
odb::dbWireEncoder_addPoint $enc 67830 2102100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 66270 2102100
odb::dbWireEncoder_addPoint $enc 67830 2102100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 66270 2093420
odb::dbWireEncoder_addPoint $enc 66270 2102100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 66690 2112740
odb::dbWireEncoder_addPoint $enc 67070 2112740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 66690 2111900
odb::dbWireEncoder_addPoint $enc 66690 2112740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 65170 2111900
odb::dbWireEncoder_addPoint $enc 66690 2111900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 65170 2107980
odb::dbWireEncoder_addPoint $enc 65170 2111900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 65170 2107980
odb::dbWireEncoder_addPoint $enc 67830 2107980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 67830 2102100
odb::dbWireEncoder_addPoint $enc 67830 2107980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 62130 2118060
odb::dbWireEncoder_addPoint $enc 62130 2118340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 62130 2118060
odb::dbWireEncoder_addPoint $enc 66690 2118060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 66690 2112740
odb::dbWireEncoder_addPoint $enc 66690 2118060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 72390 2115260
odb::dbWireEncoder_addPoint $enc 72390 2115540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 66690 2115540
odb::dbWireEncoder_addPoint $enc 72390 2115540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 72390 2115540
odb::dbWireEncoder_addPoint $enc 72390 2118340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 66270 2079420
odb::dbWireEncoder_addPoint $enc 66270 2093420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 71630 1914500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 71310 1917300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 72010 1913660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 68510 1966860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 70750 1966860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 65710 2051420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 68510 2051420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 62510 2092860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 62510 2093420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 66270 2093420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 67830 2101540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 67830 2102100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 66270 2102100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 67070 2112740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 66690 2111900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 65170 2111900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 65170 2107980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 67830 2107980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 62130 2118340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 62130 2118060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 66690 2118060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 72390 2115260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 72390 2115540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 66690 2115540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 72390 2118340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 71310 1917300
odb::dbWireEncoder_addPoint $enc 71630 1917300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 71310 1917300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3137325d5b32315d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1815070 1358700
odb::dbWireEncoder_addPoint $enc 1817390 1358700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1817390 1358700
odb::dbWireEncoder_addPoint $enc 1817390 1367660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1817350 1367660
odb::dbWireEncoder_addPoint $enc 1817390 1367660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1815450 1358700
odb::dbWireEncoder_addPoint $enc 1815450 1359260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1814310 1372420
odb::dbWireEncoder_addPoint $enc 1814310 1373540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1814310 1372420
odb::dbWireEncoder_addPoint $enc 1817350 1372420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1815830 1399580
odb::dbWireEncoder_addPoint $enc 1815830 1401540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1815830 1399580
odb::dbWireEncoder_addPoint $enc 1817730 1399580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1817730 1372420
odb::dbWireEncoder_addPoint $enc 1817730 1399580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1817350 1372420
odb::dbWireEncoder_addPoint $enc 1817730 1372420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1814310 1400980
odb::dbWireEncoder_addPoint $enc 1814310 1401400
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1814310 1400980
odb::dbWireEncoder_addPoint $enc 1815830 1400980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1817350 1367660
odb::dbWireEncoder_addPoint $enc 1817350 1372420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1815070 1358700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1817390 1358700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1817390 1367660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1817350 1367660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1815450 1359260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1815450 1358700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1814310 1373540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1814310 1372420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1817350 1372420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1815830 1401540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1815830 1399580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1817730 1399580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1814310 1401400
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1814310 1400980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1815830 1400980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1815070 1358700
odb::dbWireEncoder_addPoint $enc 1815450 1358700
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3139395d5b315d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1832930 2319940
odb::dbWireEncoder_addPoint $enc 1832930 2321620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1837490 2305660
odb::dbWireEncoder_addPoint $enc 1837870 2305660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1841290 2291940
odb::dbWireEncoder_addPoint $enc 1841290 2302860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1837870 2302860
odb::dbWireEncoder_addPoint $enc 1841290 2302860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1837870 2302860
odb::dbWireEncoder_addPoint $enc 1837870 2305660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1841290 2289700
odb::dbWireEncoder_addPoint $enc 1842430 2289700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1841290 2289700
odb::dbWireEncoder_addPoint $enc 1841290 2291940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1834830 2342900
odb::dbWireEncoder_addPoint $enc 1834830 2344860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1834830 2342900
odb::dbWireEncoder_addPoint $enc 1835310 2342900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1835310 2342620
odb::dbWireEncoder_addPoint $enc 1835310 2342900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1834830 2347940
odb::dbWireEncoder_addPoint $enc 1835210 2347940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1834830 2344860
odb::dbWireEncoder_addPoint $enc 1834830 2347940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1837550 2316300
odb::dbWireEncoder_addPoint $enc 1837550 2321620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1837550 2316300
odb::dbWireEncoder_addPoint $enc 1837870 2316300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1836730 2333660
odb::dbWireEncoder_addPoint $enc 1836730 2335060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1836730 2335060
odb::dbWireEncoder_addPoint $enc 1838670 2335060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1838670 2320780
odb::dbWireEncoder_addPoint $enc 1838670 2335060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1837550 2320780
odb::dbWireEncoder_addPoint $enc 1838670 2320780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1837870 2335060
odb::dbWireEncoder_addPoint $enc 1837870 2342340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1837870 2342340
odb::dbWireEncoder_addPoint $enc 1837870 2342620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1832930 2321620
odb::dbWireEncoder_addPoint $enc 1837550 2321620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1835310 2342620
odb::dbWireEncoder_addPoint $enc 1837870 2342620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1837870 2305660
odb::dbWireEncoder_addPoint $enc 1837870 2316300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1832930 2319940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1832930 2321620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1837490 2305660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1841290 2291940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1841290 2302860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1837870 2302860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1842430 2289700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1834830 2344860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1834830 2342900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1835210 2347940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1837550 2321620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1837550 2316300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1836730 2333660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1836730 2335060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1838670 2335060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1837870 2342340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1837870 2335060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1837870 2342620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1837550 2316300
odb::dbWireEncoder_addPoint $enc 1837870 2316300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1837550 2316300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3231395d5b33305d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2312870 2294460
odb::dbWireEncoder_addPoint $enc 2312870 2294740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2311310 2294740
odb::dbWireEncoder_addPoint $enc 2312870 2294740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2310210 2291940
odb::dbWireEncoder_addPoint $enc 2310210 2292220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2310210 2292220
odb::dbWireEncoder_addPoint $enc 2311310 2292220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2311310 2292220
odb::dbWireEncoder_addPoint $enc 2311310 2294740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2312870 2294740
odb::dbWireEncoder_addPoint $enc 2312870 2296420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2310750 2365500
odb::dbWireEncoder_addPoint $enc 2311310 2365500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2311310 2294740
odb::dbWireEncoder_addPoint $enc 2311310 2365500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2310750 2365500
odb::dbWireEncoder_addPoint $enc 2310750 2475900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2283230 2475900
odb::dbWireEncoder_addPoint $enc 2283230 2476740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2282850 2475900
odb::dbWireEncoder_addPoint $enc 2310750 2475900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2333010 2296420
odb::dbWireEncoder_addPoint $enc 2333010 2300060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2337190 2297540
odb::dbWireEncoder_addPoint $enc 2337190 2298100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2333010 2298100
odb::dbWireEncoder_addPoint $enc 2337190 2298100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2336050 2291940
odb::dbWireEncoder_addPoint $enc 2336050 2292220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2333010 2292220
odb::dbWireEncoder_addPoint $enc 2336050 2292220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2333010 2292220
odb::dbWireEncoder_addPoint $enc 2333010 2296420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2326930 2308180
odb::dbWireEncoder_addPoint $enc 2326930 2308740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2326930 2308180
odb::dbWireEncoder_addPoint $enc 2327310 2308180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2327310 2308180
odb::dbWireEncoder_addPoint $enc 2333010 2308180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2333010 2300060
odb::dbWireEncoder_addPoint $enc 2333010 2308180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2312870 2296420
odb::dbWireEncoder_addPoint $enc 2333010 2296420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2312870 2294460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2312870 2294740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2311310 2294740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2310210 2291940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2310210 2292220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2311310 2292220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2312870 2296420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2310750 2475900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2282850 2475900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2283230 2476740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2283230 2475900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2333010 2300060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2333010 2296420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2337190 2297540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2337190 2298100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2333010 2298100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2336050 2291940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2336050 2292220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2333010 2292220
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2326930 2308740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2327310 2308180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2333010 2308180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2282850 2475900
odb::dbWireEncoder_addPoint $enc 2283230 2475900
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b38395d5b32305d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 726750 2312100
odb::dbWireEncoder_addPoint $enc 728650 2312100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 726750 2312100
odb::dbWireEncoder_addPoint $enc 726750 2314340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 728270 2310140
odb::dbWireEncoder_addPoint $enc 728270 2312100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 746890 2311260
odb::dbWireEncoder_addPoint $enc 746890 2312100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 746890 2310140
odb::dbWireEncoder_addPoint $enc 746890 2311260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 728270 2310140
odb::dbWireEncoder_addPoint $enc 746890 2310140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 782610 2311260
odb::dbWireEncoder_addPoint $enc 782610 2312100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 766270 2288860
odb::dbWireEncoder_addPoint $enc 766270 2289420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 761230 2289420
odb::dbWireEncoder_addPoint $enc 766270 2289420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 761230 2289420
odb::dbWireEncoder_addPoint $enc 761230 2312100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 773870 2288860
odb::dbWireEncoder_addPoint $enc 773870 2290820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 771310 2290820
odb::dbWireEncoder_addPoint $enc 773870 2290820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 771310 2290540
odb::dbWireEncoder_addPoint $enc 771310 2290820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 767030 2290540
odb::dbWireEncoder_addPoint $enc 771310 2290540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 767030 2289420
odb::dbWireEncoder_addPoint $enc 767030 2290540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 766270 2289420
odb::dbWireEncoder_addPoint $enc 767030 2289420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 779570 2288580
odb::dbWireEncoder_addPoint $enc 779570 2288860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 773870 2288580
odb::dbWireEncoder_addPoint $enc 779570 2288580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 773870 2288580
odb::dbWireEncoder_addPoint $enc 773870 2288860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 783750 2288580
odb::dbWireEncoder_addPoint $enc 783750 2288860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 779570 2288580
odb::dbWireEncoder_addPoint $enc 783750 2288580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 746890 2312100
odb::dbWireEncoder_addPoint $enc 782610 2312100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 728650 2312100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 726750 2312100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 726750 2314340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 728270 2310140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 728270 2312100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 746890 2311260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 746890 2312100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 746890 2310140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 782610 2311260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 782610 2312100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 766270 2288860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 766270 2289420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 761230 2289420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 761230 2312100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 773870 2288860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 773870 2290820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 767030 2290540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 767030 2289420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 779570 2288860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 779570 2288580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 773870 2288580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 783750 2288860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 783750 2288580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 728650 2312100
odb::dbWireEncoder_addPoint $enc 728270 2312100
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {706f696e745f726f756e6465645b325d5b36395d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1842430 955500
odb::dbWireEncoder_addPoint $enc 1842430 956060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1850030 955500
odb::dbWireEncoder_addPoint $enc 1850030 956060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1853830 955500
odb::dbWireEncoder_addPoint $enc 1853830 955780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1853790 955500
odb::dbWireEncoder_addPoint $enc 1853830 955500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1853790 955220
odb::dbWireEncoder_addPoint $enc 1853790 955500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1851550 955220
odb::dbWireEncoder_addPoint $enc 1853790 955220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1851550 955220
odb::dbWireEncoder_addPoint $enc 1851550 955500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1850030 955500
odb::dbWireEncoder_addPoint $enc 1851550 955500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1842050 955500
odb::dbWireEncoder_addPoint $enc 1850030 955500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1842050 955500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1842430 956060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1842430 955500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1850030 956060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1850030 955500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1853830 955780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1853830 955500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1842050 955500
odb::dbWireEncoder_addPoint $enc 1842430 955500
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {706f696e745f746f74616c5b375d5b375d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1344630 1020740
odb::dbWireEncoder_addPoint $enc 1344630 1021300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1343870 1021300
odb::dbWireEncoder_addPoint $enc 1343870 1023260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1343870 1017660
odb::dbWireEncoder_addPoint $enc 1343870 1021300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1316130 1023260
odb::dbWireEncoder_addPoint $enc 1316190 1023260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1314990 1023260
odb::dbWireEncoder_addPoint $enc 1316130 1023260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1326270 1021300
odb::dbWireEncoder_addPoint $enc 1326270 1021860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1316190 1021860
odb::dbWireEncoder_addPoint $enc 1326270 1021860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1326270 1021300
odb::dbWireEncoder_addPoint $enc 1344630 1021300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1316190 997500
odb::dbWireEncoder_addPoint $enc 1316190 1023260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1314990 959700
odb::dbWireEncoder_addPoint $enc 1316190 959700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1316190 959700
odb::dbWireEncoder_addPoint $enc 1316190 982380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1315630 982380
odb::dbWireEncoder_addPoint $enc 1316190 982380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1315630 982380
odb::dbWireEncoder_addPoint $enc 1315630 997500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1315630 997500
odb::dbWireEncoder_addPoint $enc 1316190 997500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1315370 959140
odb::dbWireEncoder_addPoint $enc 1315370 959700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1344630 1020740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1344630 1021300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1343870 1023260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1343870 1021300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1343870 1017660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1316130 1023260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1316130 1023260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1316190 1023260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1314990 1023260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1314990 1023260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1316190 1021860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1314990 959700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1316190 959700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1315370 959140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1315370 959700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1314990 959700
odb::dbWireEncoder_addPoint $enc 1315370 959700
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {746f705f6e5b345d}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 580450 795900
odb::dbWireEncoder_addPoint $enc 583110 795900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 580450 790580
odb::dbWireEncoder_addPoint $enc 580450 795900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 580070 790580
odb::dbWireEncoder_addPoint $enc 580450 790580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 580070 787780
odb::dbWireEncoder_addPoint $enc 580070 790580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 582730 795900
odb::dbWireEncoder_addPoint $enc 582730 799260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 583110 795900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 580450 795900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 580070 787780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 582730 799260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 582730 795900
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 583110 795900
odb::dbWireEncoder_addPoint $enc 582730 795900
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db transition-batch.odb
write_def transition-batch.def
drt::check_drc_cmd transition-batch-drc.rpt 0 0 0 0 native_whole_drc
