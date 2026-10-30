set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-705/tasks/revision300-v-joint-via-compose/local-candidate.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set wanted [dict create]
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313130353338}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333931343337}]] 1
dict set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743834353931}]] 1
set selected [dict create]
foreach net [$block getNets] {set name [string map [list [format %c 92] {}] [$net getName]];if {[dict exists $wanted $name]} {if {[dict exists $selected $name]} {error "Ambiguous target"};dict set selected $name $net}}
if {[dict size $selected] != 3} {error "Missing target"}
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313130353338}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 955510 1018500
odb::dbWireEncoder_addPoint $enc 955510 1026060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 955510 1018500
odb::dbWireEncoder_addPoint $enc 960070 1018500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 960070 1018500
odb::dbWireEncoder_addPoint $enc 961210 1018500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 956650 1026340
odb::dbWireEncoder_addPoint $enc 956650 1026480
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 955510 1026340
odb::dbWireEncoder_addPoint $enc 956650 1026340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 955510 1026060
odb::dbWireEncoder_addPoint $enc 955510 1026340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 955510 1018500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 960070 1018500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 960070 1018500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 961210 1018500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 961210 1018500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 956650 1026480
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 955510 1026060
odb::dbWireEncoder_addPoint $enc 955510 1026065
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 955510 1026065
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 955370 1025990
odb::dbWireEncoder_addRect $enc 0 0 280 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333931343337}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2074610 2237340
odb::dbWireEncoder_addPoint $enc 2074610 2238460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2072710 2237340
odb::dbWireEncoder_addPoint $enc 2074610 2237340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2072710 2237340
odb::dbWireEncoder_addPoint $enc 2072710 2237620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2074610 2238460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2072710 2237620
odb::dbWireEncoder_addPoint $enc 2072710 2237615
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2072710 2237615
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2072570 2237550
odb::dbWireEncoder_addRect $enc 0 0 280 140
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {6e65743834353931}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1897910 1839740
odb::dbWireEncoder_addPoint $enc 1898030 1839740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1897910 1839740
odb::dbWireEncoder_addPoint $enc 1897910 1840860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1971950 1578780
odb::dbWireEncoder_addPoint $enc 1971950 1579340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1971950 1578780
odb::dbWireEncoder_addPoint $enc 1974750 1578780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1974750 1578780
odb::dbWireEncoder_addPoint $enc 1974750 1579340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1974750 1579340
odb::dbWireEncoder_addPoint $enc 1980910 1579340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1970490 1583400
odb::dbWireEncoder_addPoint $enc 1970490 1583540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1970490 1583540
odb::dbWireEncoder_addPoint $enc 1971950 1583540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1971950 1579340
odb::dbWireEncoder_addPoint $enc 1971950 1583540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2155550 1347500
odb::dbWireEncoder_addPoint $enc 2155550 1348060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2155550 1347500
odb::dbWireEncoder_addPoint $enc 2156190 1347500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2156190 1347500
odb::dbWireEncoder_addPoint $enc 2156190 1348060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2126510 1348060
odb::dbWireEncoder_addPoint $enc 2156190 1348060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2126510 1348060
odb::dbWireEncoder_addPoint $enc 2126510 1352140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2156190 1348060
odb::dbWireEncoder_addPoint $enc 2156190 1353660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1807870 1547420
odb::dbWireEncoder_addPoint $enc 1807870 1547980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1807870 1547420
odb::dbWireEncoder_addPoint $enc 1825230 1547420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1825230 1547420
odb::dbWireEncoder_addPoint $enc 1825230 1547980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1969730 1460060
odb::dbWireEncoder_addPoint $enc 1970110 1460060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1969710 1460060
odb::dbWireEncoder_addPoint $enc 1969730 1460060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 1969790 1550540
odb::dbWireEncoder_addPoint $enc 1969790 1552140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 1969790 1550540
odb::dbWireEncoder_addPoint $enc 1980910 1550540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 1980910 1550540
odb::dbWireEncoder_addPoint $enc 1980910 1555340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 1980910 1555340
odb::dbWireEncoder_addPoint $enc 1980910 1579340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 1978110 1687420
odb::dbWireEncoder_addPoint $enc 1978110 1778700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1566510 1568700
odb::dbWireEncoder_addPoint $enc 1567310 1568700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1965790 1579340
odb::dbWireEncoder_addPoint $enc 1971950 1579340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1935150 1755460
odb::dbWireEncoder_addPoint $enc 1938350 1755460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1935150 1751260
odb::dbWireEncoder_addPoint $enc 1935150 1755460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1939710 1818460
odb::dbWireEncoder_addPoint $enc 1939710 1818740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1939710 1818740
odb::dbWireEncoder_addPoint $enc 1940030 1818740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1940030 1818460
odb::dbWireEncoder_addPoint $enc 1940030 1818740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1936290 1838340
odb::dbWireEncoder_addPoint $enc 1936670 1838340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1936290 1837500
odb::dbWireEncoder_addPoint $enc 1936290 1838340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1936290 1837500
odb::dbWireEncoder_addPoint $enc 1936670 1837500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1936670 1837500
odb::dbWireEncoder_addPoint $enc 1940030 1837500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1940030 1818740
odb::dbWireEncoder_addPoint $enc 1940030 1837500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1936670 1837500
odb::dbWireEncoder_addPoint $enc 1936670 1839740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1898030 1839740
odb::dbWireEncoder_addPoint $enc 1936670 1839740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2028630 1363740
odb::dbWireEncoder_addPoint $enc 2028630 1367940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2028510 1363740
odb::dbWireEncoder_addPoint $enc 2028630 1363740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2027390 1363740
odb::dbWireEncoder_addPoint $enc 2028510 1363740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2027390 1363340
odb::dbWireEncoder_addPoint $enc 2027390 1363740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2008350 1497020
odb::dbWireEncoder_addPoint $enc 2009470 1497020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 2108990 1352140
odb::dbWireEncoder_addPoint $enc 2108990 1353740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 2108990 1352140
odb::dbWireEncoder_addPoint $enc 2124830 1352140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 2027390 1353740
odb::dbWireEncoder_addPoint $enc 2108990 1353740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2124830 1352140
odb::dbWireEncoder_addPoint $enc 2126510 1352140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2172650 1350860
odb::dbWireEncoder_addPoint $enc 2172650 1351140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2172650 1350860
odb::dbWireEncoder_addPoint $enc 2173550 1350860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2173550 1350860
odb::dbWireEncoder_addPoint $enc 2173550 1351140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2173550 1351140
odb::dbWireEncoder_addPoint $enc 2173550 1353660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2156190 1353660
odb::dbWireEncoder_addPoint $enc 2181390 1353660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2181390 1586340
odb::dbWireEncoder_addPoint $enc 2183290 1586340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2183670 1590260
odb::dbWireEncoder_addPoint $enc 2183670 1591940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2181390 1590260
odb::dbWireEncoder_addPoint $enc 2183670 1590260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2181390 1586340
odb::dbWireEncoder_addPoint $enc 2181390 1590260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1567070 1537340
odb::dbWireEncoder_addPoint $enc 1567070 1548540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1566170 1537340
odb::dbWireEncoder_addPoint $enc 1567070 1537340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1566170 1535940
odb::dbWireEncoder_addPoint $enc 1566170 1537340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1566510 1560860
odb::dbWireEncoder_addPoint $enc 1567070 1560860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1567070 1548540
odb::dbWireEncoder_addPoint $enc 1567070 1560860
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1566510 1560860
odb::dbWireEncoder_addPoint $enc 1566510 1568700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1567070 1548540
odb::dbWireEncoder_addPoint $enc 1607400 1548540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1607400 1548540
odb::dbWireEncoder_addPoint $enc 1607400 1549100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1607400 1549100
odb::dbWireEncoder_addPoint $enc 1614110 1549100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1614110 1547980
odb::dbWireEncoder_addPoint $enc 1614110 1549100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1725550 1547420
odb::dbWireEncoder_addPoint $enc 1725550 1547980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1806900 1547980
odb::dbWireEncoder_addPoint $enc 1807870 1547980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1806900 1547420
odb::dbWireEncoder_addPoint $enc 1806900 1547980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1725550 1547420
odb::dbWireEncoder_addPoint $enc 1806900 1547420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1965930 1459500
odb::dbWireEncoder_addPoint $enc 1965930 1460060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1959850 1459500
odb::dbWireEncoder_addPoint $enc 1965930 1459500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1959850 1459500
odb::dbWireEncoder_addPoint $enc 1959850 1459780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1958710 1459780
odb::dbWireEncoder_addPoint $enc 1959850 1459780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1958710 1459780
odb::dbWireEncoder_addPoint $enc 1958710 1460060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1965930 1460060
odb::dbWireEncoder_addPoint $enc 1969710 1460060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1946750 1547140
odb::dbWireEncoder_addPoint $enc 1946930 1547140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1946750 1547140
odb::dbWireEncoder_addPoint $enc 1946750 1551340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1946750 1551340
odb::dbWireEncoder_addPoint $enc 1947310 1551340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 1947310 1551340
odb::dbWireEncoder_addPoint $enc 1947310 1552140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 1947310 1552140
odb::dbWireEncoder_addPoint $enc 1969790 1552140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 1965790 1579340
odb::dbWireEncoder_addPoint $enc 1965790 1687420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1965790 1687420
odb::dbWireEncoder_addPoint $enc 1978110 1687420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1938190 1773660
odb::dbWireEncoder_addPoint $enc 1938190 1773940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1938190 1773940
odb::dbWireEncoder_addPoint $enc 1938910 1773940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1938910 1773940
odb::dbWireEncoder_addPoint $enc 1938910 1778700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1938910 1778700
odb::dbWireEncoder_addPoint $enc 1940030 1778700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1938350 1767780
odb::dbWireEncoder_addPoint $enc 1938910 1767780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1938910 1767780
odb::dbWireEncoder_addPoint $enc 1938910 1773940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1963650 1778700
odb::dbWireEncoder_addPoint $enc 1963650 1779260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1962990 1778700
odb::dbWireEncoder_addPoint $enc 1963650 1778700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1962990 1778700
odb::dbWireEncoder_addPoint $enc 1962990 1779820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1940030 1779820
odb::dbWireEncoder_addPoint $enc 1962990 1779820
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1938350 1755460
odb::dbWireEncoder_addPoint $enc 1938350 1767780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 1940030 1778700
odb::dbWireEncoder_addPoint $enc 1940030 1818460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1962990 1778700
odb::dbWireEncoder_addPoint $enc 1978110 1778700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2013950 1449740
odb::dbWireEncoder_addPoint $enc 2013950 1460060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 2013950 1449740
odb::dbWireEncoder_addPoint $enc 2027390 1449740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1969710 1460060
odb::dbWireEncoder_addPoint $enc 2013950 1460060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2009470 1460060
odb::dbWireEncoder_addPoint $enc 2009470 1497020
odb::dbWireEncoder_newPath $enc [$tech findLayer metal8] ROUTED
odb::dbWireEncoder_addPoint $enc 2027390 1353740
odb::dbWireEncoder_addPoint $enc 2027390 1449740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 1980910 1555340
odb::dbWireEncoder_addPoint $enc 2008350 1555340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2008350 1497020
odb::dbWireEncoder_addPoint $enc 2008350 1555340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2181390 1353660
odb::dbWireEncoder_addPoint $enc 2181390 1447800
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2180830 1447800
odb::dbWireEncoder_addPoint $enc 2181390 1447800
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2181390 1549660
odb::dbWireEncoder_addPoint $enc 2181770 1549660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2181390 1529740
odb::dbWireEncoder_addPoint $enc 2181390 1549660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2180830 1529740
odb::dbWireEncoder_addPoint $enc 2181390 1529740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2180830 1447800
odb::dbWireEncoder_addPoint $enc 2180830 1529740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2181390 1549660
odb::dbWireEncoder_addPoint $enc 2181390 1586340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1683550 1547980
odb::dbWireEncoder_addPoint $enc 1683550 1550780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1683550 1550780
odb::dbWireEncoder_addPoint $enc 1692510 1550780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1692510 1547980
odb::dbWireEncoder_addPoint $enc 1692510 1550780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1614110 1547980
odb::dbWireEncoder_addPoint $enc 1683550 1547980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1692510 1547980
odb::dbWireEncoder_addPoint $enc 1725550 1547980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 1835870 1547980
odb::dbWireEncoder_addPoint $enc 1835870 1548540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 1835870 1548540
odb::dbWireEncoder_addPoint $enc 1836990 1548540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1836990 1548540
odb::dbWireEncoder_addPoint $enc 1837550 1548540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1837550 1547980
odb::dbWireEncoder_addPoint $enc 1837550 1548540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1825230 1547980
odb::dbWireEncoder_addPoint $enc 1835870 1547980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1837550 1547980
odb::dbWireEncoder_addPoint $enc 1946750 1547980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1898030 1839740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1898030 1839740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1897910 1839740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1897910 1840860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1980910 1579340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1970490 1583400
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1970490 1583540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1971950 1583540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1971950 1579340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2155550 1348060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2155550 1347500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2156190 1347500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2156190 1348060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2126510 1348060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2156190 1353660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1970110 1460060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1969730 1460060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1969710 1460060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1969710 1460060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 1980910 1550540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via6_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 1980910 1555340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via6_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1978110 1687420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1978110 1778700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1566510 1568700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1567310 1568700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1567310 1568700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1965790 1579340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1938350 1755460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1935150 1755460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1935150 1751260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1939710 1818460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1939710 1818740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1940030 1818740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1940030 1818460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1940030 1818460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1936670 1838340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1936670 1837500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1936670 1837500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1940030 1837500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1936670 1839740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 2027390 1353740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via7_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2028630 1367940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2028630 1363740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2028510 1363740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2028510 1363740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2027390 1363740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2027390 1363340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via6_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 2027390 1363340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via7_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2008350 1497020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2009470 1497020
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2124830 1352140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via6_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2181390 1353660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2172650 1351140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2172650 1350860
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2173550 1351140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2173550 1353660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2183290 1586340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2183290 1586340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2181390 1586340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2183670 1591940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2183670 1590260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2181390 1590260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1567070 1548540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1567070 1537340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1566170 1537340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1566170 1535940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1965930 1460060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1965930 1459500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1958710 1459780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1958710 1460060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1946930 1547140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1946930 1547140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1946750 1547140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1946750 1551340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1947310 1551340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 1947310 1552140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via6_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1946750 1547980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1965790 1687420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1938190 1773660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1938190 1773940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1938910 1773940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1938910 1778700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1940030 1778700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 1963650 1779260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1963650 1778700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1962990 1778700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1962990 1779820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1940030 1779820
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1962990 1778700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2013950 1460060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2013950 1449740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via6_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal7] ROUTED
odb::dbWireEncoder_addPoint $enc 2027390 1449740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via7_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2009470 1460060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal6] ROUTED
odb::dbWireEncoder_addPoint $enc 2008350 1555340
odb::dbWireEncoder_addTechVia $enc [$tech findVia via6_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2181770 1549660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2181770 1549660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2181390 1549660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 2181390 1549660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 2181390 1549660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1683550 1547980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1683550 1550780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1692510 1550780
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 1692510 1547980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1835870 1547980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 1836990 1548540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via5_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1936290 1837500
odb::dbWireEncoder_addPoint $enc 1936295 1837500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1936295 1837500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1936220 1837360
odb::dbWireEncoder_addRect $enc 0 0 140 280
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db local-candidate.odb
write_def local-candidate.def
drt::check_drc_cmd local-native-drc.rpt 0 0 0 0 native_whole_drc
