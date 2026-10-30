set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-705/tasks/revision300-v-joint-via-compose/local-candidate.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set wanted [dict create]
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743833333438}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333731353439}]] 1
set selected [dict create]
foreach net [$block getNets] {set name [string map [list [format %c 92] {}] [$net getName]];if {[dict exists $wanted $name]} {if {[dict exists $selected $name]} {error "Ambiguous target"};dict set selected $name $net}}
if {[dict size $selected] != 2} {error "Missing target"}
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743833333438}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1600670 2127020
odb::dbWireEncoder_addPoint $enc 1600670 2127300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1671050 2006060
odb::dbWireEncoder_addPoint $enc 1673710 2006060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1674090 2000740
odb::dbWireEncoder_addPoint $enc 1674090 2006060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1673710 2006060
odb::dbWireEncoder_addPoint $enc 1674090 2006060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1682070 2073540
odb::dbWireEncoder_addPoint $enc 1682070 2074660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1674470 2074660
odb::dbWireEncoder_addPoint $enc 1682070 2074660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1674470 2074660
odb::dbWireEncoder_addPoint $enc 1674470 2074940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1671790 2074940
odb::dbWireEncoder_addPoint $enc 1674470 2074940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1687010 2048060
odb::dbWireEncoder_addPoint $enc 1687010 2050860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1685870 2050860
odb::dbWireEncoder_addPoint $enc 1687010 2050860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1685870 2050860
odb::dbWireEncoder_addPoint $enc 1685870 2055340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1685110 2055340
odb::dbWireEncoder_addPoint $enc 1685870 2055340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1685110 2055340
odb::dbWireEncoder_addPoint $enc 1685110 2065700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1684730 2065700
odb::dbWireEncoder_addPoint $enc 1685110 2065700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1684730 2065700
odb::dbWireEncoder_addPoint $enc 1684730 2071300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1682070 2071300
odb::dbWireEncoder_addPoint $enc 1684730 2071300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1682070 2071300
odb::dbWireEncoder_addPoint $enc 1682070 2073540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1652750 2137100
odb::dbWireEncoder_addPoint $enc 1652750 2160620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1652190 2160620
odb::dbWireEncoder_addPoint $enc 1652750 2160620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1687010 2046300
odb::dbWireEncoder_addPoint $enc 1687010 2048060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1673710 2006060
odb::dbWireEncoder_addPoint $enc 1673710 2006400
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1685790 2031260
odb::dbWireEncoder_addPoint $enc 1685790 2043860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1685790 2043860
odb::dbWireEncoder_addPoint $enc 1686630 2043860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1686630 2043860
odb::dbWireEncoder_addPoint $enc 1686630 2046300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1686630 2046300
odb::dbWireEncoder_addPoint $enc 1687010 2046300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1677130 2017540
odb::dbWireEncoder_addPoint $enc 1677130 2023700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1677130 2023700
odb::dbWireEncoder_addPoint $enc 1685790 2023700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1685790 2023700
odb::dbWireEncoder_addPoint $enc 1685790 2031260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1673710 2006400
odb::dbWireEncoder_addPoint $enc 1674470 2006400
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1674470 2006400
odb::dbWireEncoder_addPoint $enc 1674470 2009420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1674470 2009420
odb::dbWireEncoder_addPoint $enc 1674850 2009420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1674850 2009420
odb::dbWireEncoder_addPoint $enc 1674850 2013620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1674850 2013620
odb::dbWireEncoder_addPoint $enc 1678270 2013620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1678270 2013620
odb::dbWireEncoder_addPoint $enc 1678270 2018100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1677130 2018100
odb::dbWireEncoder_addPoint $enc 1678270 2018100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1651630 2120860
odb::dbWireEncoder_addPoint $enc 1675150 2120860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1675150 2093700
odb::dbWireEncoder_addPoint $enc 1675150 2120860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1671790 2093700
odb::dbWireEncoder_addPoint $enc 1675150 2093700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1651630 2120860
odb::dbWireEncoder_addPoint $enc 1651630 2137100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1671790 2074940
odb::dbWireEncoder_addPoint $enc 1671790 2093700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1651070 2170140
odb::dbWireEncoder_addPoint $enc 1652190 2170140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1651070 2170140
odb::dbWireEncoder_addPoint $enc 1651070 2183860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1649390 2183860
odb::dbWireEncoder_addPoint $enc 1651070 2183860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1649390 2183860
odb::dbWireEncoder_addPoint $enc 1649390 2189180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1649390 2189180
odb::dbWireEncoder_addPoint $enc 1649770 2189180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1649770 2189180
odb::dbWireEncoder_addPoint $enc 1649770 2193660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1647870 2193660
odb::dbWireEncoder_addPoint $enc 1649770 2193660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1647870 2193660
odb::dbWireEncoder_addPoint $enc 1647870 2196460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1647870 2196460
odb::dbWireEncoder_addPoint $enc 1648250 2196460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1648250 2196460
odb::dbWireEncoder_addPoint $enc 1648250 2196600
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1652190 2160620
odb::dbWireEncoder_addPoint $enc 1652190 2170140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1542230 2148860
odb::dbWireEncoder_addPoint $enc 1542230 2149420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1542230 2149420
odb::dbWireEncoder_addPoint $enc 1542430 2149420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1542430 2149420
odb::dbWireEncoder_addPoint $enc 1542430 2161180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1541870 2161180
odb::dbWireEncoder_addPoint $enc 1542430 2161180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1541850 2136540
odb::dbWireEncoder_addPoint $enc 1542990 2136540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1542990 2136540
odb::dbWireEncoder_addPoint $enc 1542990 2149420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1542430 2149420
odb::dbWireEncoder_addPoint $enc 1542990 2149420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1647300 2137100
odb::dbWireEncoder_addPoint $enc 1652750 2137100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1621390 2143260
odb::dbWireEncoder_addPoint $enc 1621650 2143260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1621390 2128140
odb::dbWireEncoder_addPoint $enc 1621390 2143260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1607970 2128140
odb::dbWireEncoder_addPoint $enc 1621390 2128140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1607970 2127020
odb::dbWireEncoder_addPoint $enc 1607970 2128140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1607590 2127020
odb::dbWireEncoder_addPoint $enc 1607970 2127020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1647300 2136820
odb::dbWireEncoder_addPoint $enc 1647300 2137100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1621390 2136820
odb::dbWireEncoder_addPoint $enc 1647300 2136820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1600670 2127020
odb::dbWireEncoder_addPoint $enc 1607590 2127020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1541850 2126100
odb::dbWireEncoder_addPoint $enc 1541850 2136540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1541850 2126100
odb::dbWireEncoder_addPoint $enc 1542230 2126100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1542230 2123940
odb::dbWireEncoder_addPoint $enc 1542230 2126100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1538050 2179660
odb::dbWireEncoder_addPoint $enc 1541870 2179660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1538050 2179660
odb::dbWireEncoder_addPoint $enc 1538050 2179940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1541870 2161180
odb::dbWireEncoder_addPoint $enc 1541870 2179660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1721630 2031260
odb::dbWireEncoder_addPoint $enc 1725390 2031260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1725390 2030420
odb::dbWireEncoder_addPoint $enc 1725390 2031260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1685790 2031260
odb::dbWireEncoder_addPoint $enc 1721630 2031260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1587450 2127300
odb::dbWireEncoder_addPoint $enc 1587450 2128700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 2128700
odb::dbWireEncoder_addPoint $enc 1587450 2128700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 2128700
odb::dbWireEncoder_addPoint $enc 1574910 2135700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1595050 2120860
odb::dbWireEncoder_addPoint $enc 1595050 2121700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1594670 2121700
odb::dbWireEncoder_addPoint $enc 1595050 2121700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1594670 2121700
odb::dbWireEncoder_addPoint $enc 1594670 2123380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1593910 2123380
odb::dbWireEncoder_addPoint $enc 1594670 2123380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1593910 2123100
odb::dbWireEncoder_addPoint $enc 1593910 2123380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1593390 2123100
odb::dbWireEncoder_addPoint $enc 1593910 2123100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1593390 2123100
odb::dbWireEncoder_addPoint $enc 1593390 2125900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1593390 2125900
odb::dbWireEncoder_addPoint $enc 1593950 2125900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1593950 2125900
odb::dbWireEncoder_addPoint $enc 1593950 2127300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1541850 2135700
odb::dbWireEncoder_addPoint $enc 1574910 2135700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1587450 2127300
odb::dbWireEncoder_addPoint $enc 1600670 2127300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1670290 1991220
odb::dbWireEncoder_addPoint $enc 1671050 1991220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1670290 1983100
odb::dbWireEncoder_addPoint $enc 1670290 1991220
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1670290 1983100
odb::dbWireEncoder_addPoint $enc 1671810 1983100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1671810 1975260
odb::dbWireEncoder_addPoint $enc 1671810 1983100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1671050 1991220
odb::dbWireEncoder_addPoint $enc 1671050 2006060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1671050 2006060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1674090 2000740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1682070 2073540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1682070 2074660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1671790 2074940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1687010 2048060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1687010 2050860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1685870 2050860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1684730 2071300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1682070 2071300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1652750 2137100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1651630 2137100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1685790 2031260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1685790 2043860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1686630 2043860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1677130 2017540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1677130 2023700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1685790 2023700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1674850 2013620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1678270 2013620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1651630 2120860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1675150 2120860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1675150 2093700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1671790 2093700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1652190 2170140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1651070 2170140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1651070 2183860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1649390 2183860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1649770 2193660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1647870 2193660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1648250 2196600
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1542230 2148860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1542230 2149420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1542430 2149420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1541850 2136540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1542990 2136540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1541850 2135700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1621650 2143260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1621650 2143260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1621390 2143260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1621390 2128140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1607970 2128140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1607590 2127020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1621390 2136820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1542230 2123940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1541870 2179660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1538050 2179660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1538050 2179940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1721630 2031260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1721630 2031260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1725390 2031260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1725390 2030420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1587450 2127300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1587450 2128700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 2128700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1574910 2135700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1595050 2120860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1594670 2123380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1593390 2123100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1593950 2127300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1670290 1983100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1671810 1983100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1671810 1975260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1673710 2006060
odb::dbWireEncoder_addPoint $enc 1673715 2006060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1673715 2006060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1673570 2005990
odb::dbWireEncoder_addRect $enc 0 0 280 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333731353439}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 160910 1837500
odb::dbWireEncoder_addPoint $enc 161310 1837500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 160550 1789620
odb::dbWireEncoder_addPoint $enc 160910 1789620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 160550 1779260
odb::dbWireEncoder_addPoint $enc 160550 1789620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 160910 1789620
odb::dbWireEncoder_addPoint $enc 160910 1837500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 160910 1837500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 161310 1837500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 160910 1789620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 160550 1789620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 160550 1779260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 161310 1837500
odb::dbWireEncoder_addPoint $enc 161305 1837500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 161305 1837500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 161240 1837360
odb::dbWireEncoder_addRect $enc 0 0 140 280
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db local-candidate.odb
write_def local-candidate.def
drt::check_drc_cmd local-native-drc.rpt 0 0 0 0 native_whole_drc
