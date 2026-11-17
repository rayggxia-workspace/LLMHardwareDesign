set_thread_count $::env(SLURM_CPUS_PER_TASK)
set p /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $p/lib/NangateOpenCellLibrary_typical.lib
read_liberty {/public/home/yuzelu/project-circuit/issue250-m-physical-20261111-60/candidate-views/m_native_leaf_s32.lib}
read_liberty {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s/audit08/base0/local_s_base.lib}
read_liberty {/public/home/yuzelu/project-circuit/issue250-g32-coplacement-20261111-02/g_s32.lib}
read_db {/public/home/yuzelu/PingyangHuang/hpy-nine-native.lHJoC3yv/P-west/place250/placed.odb}
set b [ord::get_db_block]
set db [ord::get_db]
set tech [ord::get_db_tech]
set selected {}
set selected_ports {}
set term [$b findBTerm {aux_address[0]}]
if {$term eq "NULL"} {error {Missing native port aux_address[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2327790 1063740 2331790 1067740
lappend selected_ports {aux_address[0]}
set term [$b findBTerm {aux_address[1]}]
if {$term eq "NULL"} {error {Missing native port aux_address[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2311790 1079740 2315790 1083740
lappend selected_ports {aux_address[1]}
set term [$b findBTerm {aux_address[2]}]
if {$term eq "NULL"} {error {Missing native port aux_address[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2311790 1191740 2315790 1195740
lappend selected_ports {aux_address[2]}
set term [$b findBTerm {aux_address[3]}]
if {$term eq "NULL"} {error {Missing native port aux_address[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2343790 1143740 2347790 1147740
lappend selected_ports {aux_address[3]}
set term [$b findBTerm {aux_address[4]}]
if {$term eq "NULL"} {error {Missing native port aux_address[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2327790 1111740 2331790 1115740
lappend selected_ports {aux_address[4]}
set term [$b findBTerm {aux_address[5]}]
if {$term eq "NULL"} {error {Missing native port aux_address[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2343790 1127740 2347790 1131740
lappend selected_ports {aux_address[5]}
set term [$b findBTerm {aux_address[6]}]
if {$term eq "NULL"} {error {Missing native port aux_address[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2327790 1191740 2331790 1195740
lappend selected_ports {aux_address[6]}
set term [$b findBTerm {aux_address[7]}]
if {$term eq "NULL"} {error {Missing native port aux_address[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2327790 1047740 2331790 1051740
lappend selected_ports {aux_address[7]}
set term [$b findBTerm {aux_address[8]}]
if {$term eq "NULL"} {error {Missing native port aux_address[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2359790 1159740 2363790 1163740
lappend selected_ports {aux_address[8]}
set term [$b findBTerm {aux_address[9]}]
if {$term eq "NULL"} {error {Missing native port aux_address[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2359790 1143740 2363790 1147740
lappend selected_ports {aux_address[9]}
set term [$b findBTerm {aux_ready}]
if {$term eq "NULL"} {error {Missing native port aux_ready}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2295790 1063740 2299790 1067740
lappend selected_ports {aux_ready}
set term [$b findBTerm {aux_rsp_data[0]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2887790 1559740 2891790 1563740
lappend selected_ports {aux_rsp_data[0]}
set term [$b findBTerm {aux_rsp_data[100]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[100]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 919790 1367740 923790 1371740
lappend selected_ports {aux_rsp_data[100]}
set term [$b findBTerm {aux_rsp_data[101]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[101]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1095790 1415740 1099790 1419740
lappend selected_ports {aux_rsp_data[101]}
set term [$b findBTerm {aux_rsp_data[102]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[102]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 983790 1319740 987790 1323740
lappend selected_ports {aux_rsp_data[102]}
set term [$b findBTerm {aux_rsp_data[103]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[103]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1031790 1527740 1035790 1531740
lappend selected_ports {aux_rsp_data[103]}
set term [$b findBTerm {aux_rsp_data[104]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[104]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1095790 1351740 1099790 1355740
lappend selected_ports {aux_rsp_data[104]}
set term [$b findBTerm {aux_rsp_data[105]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[105]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1159790 1415740 1163790 1419740
lappend selected_ports {aux_rsp_data[105]}
set term [$b findBTerm {aux_rsp_data[106]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[106]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1159790 1383740 1163790 1387740
lappend selected_ports {aux_rsp_data[106]}
set term [$b findBTerm {aux_rsp_data[107]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[107]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1095790 1303740 1099790 1307740
lappend selected_ports {aux_rsp_data[107]}
set term [$b findBTerm {aux_rsp_data[108]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[108]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1383790 1223740 1387790 1227740
lappend selected_ports {aux_rsp_data[108]}
set term [$b findBTerm {aux_rsp_data[109]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[109]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1143790 1351740 1147790 1355740
lappend selected_ports {aux_rsp_data[109]}
set term [$b findBTerm {aux_rsp_data[10]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[10]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3271790 1447740 3275790 1451740
lappend selected_ports {aux_rsp_data[10]}
set term [$b findBTerm {aux_rsp_data[110]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[110]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1399790 1239740 1403790 1243740
lappend selected_ports {aux_rsp_data[110]}
set term [$b findBTerm {aux_rsp_data[111]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[111]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1383790 1159740 1387790 1163740
lappend selected_ports {aux_rsp_data[111]}
set term [$b findBTerm {aux_rsp_data[112]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[112]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 919790 1463740 923790 1467740
lappend selected_ports {aux_rsp_data[112]}
set term [$b findBTerm {aux_rsp_data[113]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[113]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1111790 1303740 1115790 1307740
lappend selected_ports {aux_rsp_data[113]}
set term [$b findBTerm {aux_rsp_data[114]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[114]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 967790 1495740 971790 1499740
lappend selected_ports {aux_rsp_data[114]}
set term [$b findBTerm {aux_rsp_data[115]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[115]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 919790 1543740 923790 1547740
lappend selected_ports {aux_rsp_data[115]}
set term [$b findBTerm {aux_rsp_data[116]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[116]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 807790 1447740 811790 1451740
lappend selected_ports {aux_rsp_data[116]}
set term [$b findBTerm {aux_rsp_data[117]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[117]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1015790 1351740 1019790 1355740
lappend selected_ports {aux_rsp_data[117]}
set term [$b findBTerm {aux_rsp_data[118]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[118]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 727790 1479740 731790 1483740
lappend selected_ports {aux_rsp_data[118]}
set term [$b findBTerm {aux_rsp_data[119]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[119]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1159790 1511740 1163790 1515740
lappend selected_ports {aux_rsp_data[119]}
set term [$b findBTerm {aux_rsp_data[11]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[11]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3271790 1383740 3275790 1387740
lappend selected_ports {aux_rsp_data[11]}
set term [$b findBTerm {aux_rsp_data[120]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[120]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 759790 1479740 763790 1483740
lappend selected_ports {aux_rsp_data[120]}
set term [$b findBTerm {aux_rsp_data[121]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[121]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1047790 1591740 1051790 1595740
lappend selected_ports {aux_rsp_data[121]}
set term [$b findBTerm {aux_rsp_data[122]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[122]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1095790 1495740 1099790 1499740
lappend selected_ports {aux_rsp_data[122]}
set term [$b findBTerm {aux_rsp_data[123]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[123]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1031790 1591740 1035790 1595740
lappend selected_ports {aux_rsp_data[123]}
set term [$b findBTerm {aux_rsp_data[124]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[124]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 807790 1527740 811790 1531740
lappend selected_ports {aux_rsp_data[124]}
set term [$b findBTerm {aux_rsp_data[125]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[125]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1335790 1255740 1339790 1259740
lappend selected_ports {aux_rsp_data[125]}
set term [$b findBTerm {aux_rsp_data[126]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[126]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 743790 1303740 747790 1307740
lappend selected_ports {aux_rsp_data[126]}
set term [$b findBTerm {aux_rsp_data[127]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[127]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1127790 1463740 1131790 1467740
lappend selected_ports {aux_rsp_data[127]}
set term [$b findBTerm {aux_rsp_data[12]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[12]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3207790 999740 3211790 1003740
lappend selected_ports {aux_rsp_data[12]}
set term [$b findBTerm {aux_rsp_data[13]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[13]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3159790 1015740 3163790 1019740
lappend selected_ports {aux_rsp_data[13]}
set term [$b findBTerm {aux_rsp_data[14]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[14]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3271790 1479740 3275790 1483740
lappend selected_ports {aux_rsp_data[14]}
set term [$b findBTerm {aux_rsp_data[15]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[15]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3175790 1367740 3179790 1371740
lappend selected_ports {aux_rsp_data[15]}
set term [$b findBTerm {aux_rsp_data[16]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[16]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 791790 1239740 795790 1243740
lappend selected_ports {aux_rsp_data[16]}
set term [$b findBTerm {aux_rsp_data[17]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[17]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 807790 1415740 811790 1419740
lappend selected_ports {aux_rsp_data[17]}
set term [$b findBTerm {aux_rsp_data[18]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[18]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 791790 1383740 795790 1387740
lappend selected_ports {aux_rsp_data[18]}
set term [$b findBTerm {aux_rsp_data[19]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[19]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 727790 1575740 731790 1579740
lappend selected_ports {aux_rsp_data[19]}
set term [$b findBTerm {aux_rsp_data[1]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3143790 1031740 3147790 1035740
lappend selected_ports {aux_rsp_data[1]}
set term [$b findBTerm {aux_rsp_data[20]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[20]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 775790 1319740 779790 1323740
lappend selected_ports {aux_rsp_data[20]}
set term [$b findBTerm {aux_rsp_data[21]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[21]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1255790 1239740 1259790 1243740
lappend selected_ports {aux_rsp_data[21]}
set term [$b findBTerm {aux_rsp_data[22]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[22]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1639790 1191740 1643790 1195740
lappend selected_ports {aux_rsp_data[22]}
set term [$b findBTerm {aux_rsp_data[23]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[23]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1943790 1431740 1947790 1435740
lappend selected_ports {aux_rsp_data[23]}
set term [$b findBTerm {aux_rsp_data[24]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[24]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2967790 1175740 2971790 1179740
lappend selected_ports {aux_rsp_data[24]}
set term [$b findBTerm {aux_rsp_data[25]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[25]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2839790 631740 2843790 635740
lappend selected_ports {aux_rsp_data[25]}
set term [$b findBTerm {aux_rsp_data[26]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[26]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3015790 1127740 3019790 1131740
lappend selected_ports {aux_rsp_data[26]}
set term [$b findBTerm {aux_rsp_data[27]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[27]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1943790 1591740 1947790 1595740
lappend selected_ports {aux_rsp_data[27]}
set term [$b findBTerm {aux_rsp_data[28]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[28]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2823790 1623740 2827790 1627740
lappend selected_ports {aux_rsp_data[28]}
set term [$b findBTerm {aux_rsp_data[29]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[29]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2839790 1607740 2843790 1611740
lappend selected_ports {aux_rsp_data[29]}
set term [$b findBTerm {aux_rsp_data[2]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3191790 1623740 3195790 1627740
lappend selected_ports {aux_rsp_data[2]}
set term [$b findBTerm {aux_rsp_data[30]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[30]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2823790 1639740 2827790 1643740
lappend selected_ports {aux_rsp_data[30]}
set term [$b findBTerm {aux_rsp_data[31]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[31]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2935790 1607740 2939790 1611740
lappend selected_ports {aux_rsp_data[31]}
set term [$b findBTerm {aux_rsp_data[32]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[32]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 807790 1239740 811790 1243740
lappend selected_ports {aux_rsp_data[32]}
set term [$b findBTerm {aux_rsp_data[33]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[33]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 807790 1207740 811790 1211740
lappend selected_ports {aux_rsp_data[33]}
set term [$b findBTerm {aux_rsp_data[34]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[34]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 807790 1399740 811790 1403740
lappend selected_ports {aux_rsp_data[34]}
set term [$b findBTerm {aux_rsp_data[35]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[35]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 855790 1319740 859790 1323740
lappend selected_ports {aux_rsp_data[35]}
set term [$b findBTerm {aux_rsp_data[36]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[36]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 871790 1383740 875790 1387740
lappend selected_ports {aux_rsp_data[36]}
set term [$b findBTerm {aux_rsp_data[37]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[37]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 887790 1175740 891790 1179740
lappend selected_ports {aux_rsp_data[37]}
set term [$b findBTerm {aux_rsp_data[38]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[38]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 855790 1479740 859790 1483740
lappend selected_ports {aux_rsp_data[38]}
set term [$b findBTerm {aux_rsp_data[39]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[39]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 903790 1367740 907790 1371740
lappend selected_ports {aux_rsp_data[39]}
set term [$b findBTerm {aux_rsp_data[3]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3255790 1463740 3259790 1467740
lappend selected_ports {aux_rsp_data[3]}
set term [$b findBTerm {aux_rsp_data[40]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[40]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 919790 1239740 923790 1243740
lappend selected_ports {aux_rsp_data[40]}
set term [$b findBTerm {aux_rsp_data[41]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[41]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 871790 1335740 875790 1339740
lappend selected_ports {aux_rsp_data[41]}
set term [$b findBTerm {aux_rsp_data[42]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[42]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 903790 1287740 907790 1291740
lappend selected_ports {aux_rsp_data[42]}
set term [$b findBTerm {aux_rsp_data[43]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[43]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 903790 1239740 907790 1243740
lappend selected_ports {aux_rsp_data[43]}
set term [$b findBTerm {aux_rsp_data[44]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[44]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 903790 1543740 907790 1547740
lappend selected_ports {aux_rsp_data[44]}
set term [$b findBTerm {aux_rsp_data[45]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[45]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 919790 1271740 923790 1275740
lappend selected_ports {aux_rsp_data[45]}
set term [$b findBTerm {aux_rsp_data[46]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[46]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 919790 1335740 923790 1339740
lappend selected_ports {aux_rsp_data[46]}
set term [$b findBTerm {aux_rsp_data[47]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[47]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1015790 1175740 1019790 1179740
lappend selected_ports {aux_rsp_data[47]}
set term [$b findBTerm {aux_rsp_data[48]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[48]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 743790 1399740 747790 1403740
lappend selected_ports {aux_rsp_data[48]}
set term [$b findBTerm {aux_rsp_data[49]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[49]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 743790 1559740 747790 1563740
lappend selected_ports {aux_rsp_data[49]}
set term [$b findBTerm {aux_rsp_data[4]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3271790 1591740 3275790 1595740
lappend selected_ports {aux_rsp_data[4]}
set term [$b findBTerm {aux_rsp_data[50]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[50]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 855790 1303740 859790 1307740
lappend selected_ports {aux_rsp_data[50]}
set term [$b findBTerm {aux_rsp_data[51]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[51]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 759790 1175740 763790 1179740
lappend selected_ports {aux_rsp_data[51]}
set term [$b findBTerm {aux_rsp_data[52]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[52]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 807790 1351740 811790 1355740
lappend selected_ports {aux_rsp_data[52]}
set term [$b findBTerm {aux_rsp_data[53]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[53]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 727790 1159740 731790 1163740
lappend selected_ports {aux_rsp_data[53]}
set term [$b findBTerm {aux_rsp_data[54]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[54]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 855790 1559740 859790 1563740
lappend selected_ports {aux_rsp_data[54]}
set term [$b findBTerm {aux_rsp_data[55]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[55]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 775790 1479740 779790 1483740
lappend selected_ports {aux_rsp_data[55]}
set term [$b findBTerm {aux_rsp_data[56]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[56]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 759790 1207740 763790 1211740
lappend selected_ports {aux_rsp_data[56]}
set term [$b findBTerm {aux_rsp_data[57]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[57]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 727790 1303740 731790 1307740
lappend selected_ports {aux_rsp_data[57]}
set term [$b findBTerm {aux_rsp_data[58]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[58]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 727790 1351740 731790 1355740
lappend selected_ports {aux_rsp_data[58]}
set term [$b findBTerm {aux_rsp_data[59]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[59]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 727790 1495740 731790 1499740
lappend selected_ports {aux_rsp_data[59]}
set term [$b findBTerm {aux_rsp_data[5]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3271790 999740 3275790 1003740
lappend selected_ports {aux_rsp_data[5]}
set term [$b findBTerm {aux_rsp_data[60]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[60]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 807790 1287740 811790 1291740
lappend selected_ports {aux_rsp_data[60]}
set term [$b findBTerm {aux_rsp_data[61]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[61]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 727790 1447740 731790 1451740
lappend selected_ports {aux_rsp_data[61]}
set term [$b findBTerm {aux_rsp_data[62]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[62]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 679790 1159740 683790 1163740
lappend selected_ports {aux_rsp_data[62]}
set term [$b findBTerm {aux_rsp_data[63]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[63]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 727790 1399740 731790 1403740
lappend selected_ports {aux_rsp_data[63]}
set term [$b findBTerm {aux_rsp_data[64]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[64]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3255790 903740 3259790 907740
lappend selected_ports {aux_rsp_data[64]}
set term [$b findBTerm {aux_rsp_data[65]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[65]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3271790 887740 3275790 891740
lappend selected_ports {aux_rsp_data[65]}
set term [$b findBTerm {aux_rsp_data[66]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[66]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3287790 871740 3291790 875740
lappend selected_ports {aux_rsp_data[66]}
set term [$b findBTerm {aux_rsp_data[67]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[67]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3287790 1367740 3291790 1371740
lappend selected_ports {aux_rsp_data[67]}
set term [$b findBTerm {aux_rsp_data[68]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[68]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3255790 1607740 3259790 1611740
lappend selected_ports {aux_rsp_data[68]}
set term [$b findBTerm {aux_rsp_data[69]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[69]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3271790 903740 3275790 907740
lappend selected_ports {aux_rsp_data[69]}
set term [$b findBTerm {aux_rsp_data[6]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3255790 1207740 3259790 1211740
lappend selected_ports {aux_rsp_data[6]}
set term [$b findBTerm {aux_rsp_data[70]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[70]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3175790 1447740 3179790 1451740
lappend selected_ports {aux_rsp_data[70]}
set term [$b findBTerm {aux_rsp_data[71]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[71]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3255790 983740 3259790 987740
lappend selected_ports {aux_rsp_data[71]}
set term [$b findBTerm {aux_rsp_data[72]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[72]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3207790 1607740 3211790 1611740
lappend selected_ports {aux_rsp_data[72]}
set term [$b findBTerm {aux_rsp_data[73]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[73]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3287790 1287740 3291790 1291740
lappend selected_ports {aux_rsp_data[73]}
set term [$b findBTerm {aux_rsp_data[74]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[74]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3207790 1271740 3211790 1275740
lappend selected_ports {aux_rsp_data[74]}
set term [$b findBTerm {aux_rsp_data[75]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[75]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3319790 823740 3323790 827740
lappend selected_ports {aux_rsp_data[75]}
set term [$b findBTerm {aux_rsp_data[76]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[76]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3303790 855740 3307790 859740
lappend selected_ports {aux_rsp_data[76]}
set term [$b findBTerm {aux_rsp_data[77]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[77]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3207790 1031740 3211790 1035740
lappend selected_ports {aux_rsp_data[77]}
set term [$b findBTerm {aux_rsp_data[78]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[78]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3319790 839740 3323790 843740
lappend selected_ports {aux_rsp_data[78]}
set term [$b findBTerm {aux_rsp_data[79]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[79]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3255790 919740 3259790 923740
lappend selected_ports {aux_rsp_data[79]}
set term [$b findBTerm {aux_rsp_data[7]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3255790 935740 3259790 939740
lappend selected_ports {aux_rsp_data[7]}
set term [$b findBTerm {aux_rsp_data[80]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[80]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 983790 1399740 987790 1403740
lappend selected_ports {aux_rsp_data[80]}
set term [$b findBTerm {aux_rsp_data[81]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[81]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 999790 1223740 1003790 1227740
lappend selected_ports {aux_rsp_data[81]}
set term [$b findBTerm {aux_rsp_data[82]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[82]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 967790 1239740 971790 1243740
lappend selected_ports {aux_rsp_data[82]}
set term [$b findBTerm {aux_rsp_data[83]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[83]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 967790 1559740 971790 1563740
lappend selected_ports {aux_rsp_data[83]}
set term [$b findBTerm {aux_rsp_data[84]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[84]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 967790 1303740 971790 1307740
lappend selected_ports {aux_rsp_data[84]}
set term [$b findBTerm {aux_rsp_data[85]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[85]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1047790 1463740 1051790 1467740
lappend selected_ports {aux_rsp_data[85]}
set term [$b findBTerm {aux_rsp_data[86]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[86]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1031790 1447740 1035790 1451740
lappend selected_ports {aux_rsp_data[86]}
set term [$b findBTerm {aux_rsp_data[87]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[87]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 919790 1591740 923790 1595740
lappend selected_ports {aux_rsp_data[87]}
set term [$b findBTerm {aux_rsp_data[88]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[88]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1031790 1479740 1035790 1483740
lappend selected_ports {aux_rsp_data[88]}
set term [$b findBTerm {aux_rsp_data[89]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[89]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1127790 1527740 1131790 1531740
lappend selected_ports {aux_rsp_data[89]}
set term [$b findBTerm {aux_rsp_data[8]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3255790 999740 3259790 1003740
lappend selected_ports {aux_rsp_data[8]}
set term [$b findBTerm {aux_rsp_data[90]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[90]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1143790 1559740 1147790 1563740
lappend selected_ports {aux_rsp_data[90]}
set term [$b findBTerm {aux_rsp_data[91]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[91]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1127790 1543740 1131790 1547740
lappend selected_ports {aux_rsp_data[91]}
set term [$b findBTerm {aux_rsp_data[92]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[92]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1015790 1287740 1019790 1291740
lappend selected_ports {aux_rsp_data[92]}
set term [$b findBTerm {aux_rsp_data[93]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[93]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1095790 1463740 1099790 1467740
lappend selected_ports {aux_rsp_data[93]}
set term [$b findBTerm {aux_rsp_data[94]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[94]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1207790 1415740 1211790 1419740
lappend selected_ports {aux_rsp_data[94]}
set term [$b findBTerm {aux_rsp_data[95]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[95]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1031790 1239740 1035790 1243740
lappend selected_ports {aux_rsp_data[95]}
set term [$b findBTerm {aux_rsp_data[96]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[96]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 919790 1303740 923790 1307740
lappend selected_ports {aux_rsp_data[96]}
set term [$b findBTerm {aux_rsp_data[97]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[97]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 967790 1431740 971790 1435740
lappend selected_ports {aux_rsp_data[97]}
set term [$b findBTerm {aux_rsp_data[98]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[98]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 999790 1367740 1003790 1371740
lappend selected_ports {aux_rsp_data[98]}
set term [$b findBTerm {aux_rsp_data[99]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[99]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 967790 1383740 971790 1387740
lappend selected_ports {aux_rsp_data[99]}
set term [$b findBTerm {aux_rsp_data[9]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_data[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3207790 967740 3211790 971740
lappend selected_ports {aux_rsp_data[9]}
set term [$b findBTerm {aux_rsp_ready}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_ready}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2247790 1095740 2251790 1099740
lappend selected_ports {aux_rsp_ready}
set term [$b findBTerm {aux_rsp_tag[0]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1975790 1319740 1979790 1323740
lappend selected_ports {aux_rsp_tag[0]}
set term [$b findBTerm {aux_rsp_tag[10]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[10]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2679790 1127740 2683790 1131740
lappend selected_ports {aux_rsp_tag[10]}
set term [$b findBTerm {aux_rsp_tag[11]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[11]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1991790 1335740 1995790 1339740
lappend selected_ports {aux_rsp_tag[11]}
set term [$b findBTerm {aux_rsp_tag[12]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[12]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2007790 1351740 2011790 1355740
lappend selected_ports {aux_rsp_tag[12]}
set term [$b findBTerm {aux_rsp_tag[13]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[13]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2695790 1143740 2699790 1147740
lappend selected_ports {aux_rsp_tag[13]}
set term [$b findBTerm {aux_rsp_tag[14]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[14]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1927790 1287740 1931790 1291740
lappend selected_ports {aux_rsp_tag[14]}
set term [$b findBTerm {aux_rsp_tag[15]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[15]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2711790 1159740 2715790 1163740
lappend selected_ports {aux_rsp_tag[15]}
set term [$b findBTerm {aux_rsp_tag[16]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[16]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1943790 1303740 1947790 1307740
lappend selected_ports {aux_rsp_tag[16]}
set term [$b findBTerm {aux_rsp_tag[17]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[17]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1959790 1319740 1963790 1323740
lappend selected_ports {aux_rsp_tag[17]}
set term [$b findBTerm {aux_rsp_tag[18]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[18]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1991790 1351740 1995790 1355740
lappend selected_ports {aux_rsp_tag[18]}
set term [$b findBTerm {aux_rsp_tag[19]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[19]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2007790 1367740 2011790 1371740
lappend selected_ports {aux_rsp_tag[19]}
set term [$b findBTerm {aux_rsp_tag[1]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1927790 1303740 1931790 1307740
lappend selected_ports {aux_rsp_tag[1]}
set term [$b findBTerm {aux_rsp_tag[20]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[20]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1943790 1319740 1947790 1323740
lappend selected_ports {aux_rsp_tag[20]}
set term [$b findBTerm {aux_rsp_tag[21]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[21]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1959790 1335740 1963790 1339740
lappend selected_ports {aux_rsp_tag[21]}
set term [$b findBTerm {aux_rsp_tag[22]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[22]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1975790 1351740 1979790 1355740
lappend selected_ports {aux_rsp_tag[22]}
set term [$b findBTerm {aux_rsp_tag[23]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[23]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1991790 1367740 1995790 1371740
lappend selected_ports {aux_rsp_tag[23]}
set term [$b findBTerm {aux_rsp_tag[24]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[24]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1879790 1271740 1883790 1275740
lappend selected_ports {aux_rsp_tag[24]}
set term [$b findBTerm {aux_rsp_tag[25]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[25]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1927790 1319740 1931790 1323740
lappend selected_ports {aux_rsp_tag[25]}
set term [$b findBTerm {aux_rsp_tag[26]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[26]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1943790 1335740 1947790 1339740
lappend selected_ports {aux_rsp_tag[26]}
set term [$b findBTerm {aux_rsp_tag[27]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[27]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1975790 1367740 1979790 1371740
lappend selected_ports {aux_rsp_tag[27]}
set term [$b findBTerm {aux_rsp_tag[28]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[28]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1991790 1383740 1995790 1387740
lappend selected_ports {aux_rsp_tag[28]}
set term [$b findBTerm {aux_rsp_tag[29]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[29]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1863790 1271740 1867790 1275740
lappend selected_ports {aux_rsp_tag[29]}
set term [$b findBTerm {aux_rsp_tag[2]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1879790 1287740 1883790 1291740
lappend selected_ports {aux_rsp_tag[2]}
set term [$b findBTerm {aux_rsp_tag[30]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[30]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1927790 1335740 1931790 1339740
lappend selected_ports {aux_rsp_tag[30]}
set term [$b findBTerm {aux_rsp_tag[31]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[31]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2695790 1127740 2699790 1131740
lappend selected_ports {aux_rsp_tag[31]}
set term [$b findBTerm {aux_rsp_tag[3]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1943790 1351740 1947790 1355740
lappend selected_ports {aux_rsp_tag[3]}
set term [$b findBTerm {aux_rsp_tag[4]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1959790 1367740 1963790 1371740
lappend selected_ports {aux_rsp_tag[4]}
set term [$b findBTerm {aux_rsp_tag[5]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1975790 1383740 1979790 1387740
lappend selected_ports {aux_rsp_tag[5]}
set term [$b findBTerm {aux_rsp_tag[6]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1831790 1255740 1835790 1259740
lappend selected_ports {aux_rsp_tag[6]}
set term [$b findBTerm {aux_rsp_tag[7]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1863790 1287740 1867790 1291740
lappend selected_ports {aux_rsp_tag[7]}
set term [$b findBTerm {aux_rsp_tag[8]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2711790 1143740 2715790 1147740
lappend selected_ports {aux_rsp_tag[8]}
set term [$b findBTerm {aux_rsp_tag[9]}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_tag[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2695790 1111740 2699790 1115740
lappend selected_ports {aux_rsp_tag[9]}
set term [$b findBTerm {aux_rsp_valid}]
if {$term eq "NULL"} {error {Missing native port aux_rsp_valid}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2295790 1095740 2299790 1099740
lappend selected_ports {aux_rsp_valid}
set term [$b findBTerm {aux_tag[0]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2087790 1143740 2091790 1147740
lappend selected_ports {aux_tag[0]}
set term [$b findBTerm {aux_tag[10]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[10]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2311790 1111740 2315790 1115740
lappend selected_ports {aux_tag[10]}
set term [$b findBTerm {aux_tag[11]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[11]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2295790 1223740 2299790 1227740
lappend selected_ports {aux_tag[11]}
set term [$b findBTerm {aux_tag[12]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[12]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2311790 1207740 2315790 1211740
lappend selected_ports {aux_tag[12]}
set term [$b findBTerm {aux_tag[13]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[13]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2295790 1079740 2299790 1083740
lappend selected_ports {aux_tag[13]}
set term [$b findBTerm {aux_tag[14]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[14]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2311790 1095740 2315790 1099740
lappend selected_ports {aux_tag[14]}
set term [$b findBTerm {aux_tag[15]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[15]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2327790 1095740 2331790 1099740
lappend selected_ports {aux_tag[15]}
set term [$b findBTerm {aux_tag[16]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[16]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2215790 1255740 2219790 1259740
lappend selected_ports {aux_tag[16]}
set term [$b findBTerm {aux_tag[17]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[17]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2247790 1255740 2251790 1259740
lappend selected_ports {aux_tag[17]}
set term [$b findBTerm {aux_tag[18]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[18]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2183790 1239740 2187790 1243740
lappend selected_ports {aux_tag[18]}
set term [$b findBTerm {aux_tag[19]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[19]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2183790 1095740 2187790 1099740
lappend selected_ports {aux_tag[19]}
set term [$b findBTerm {aux_tag[1]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2119790 1191740 2123790 1195740
lappend selected_ports {aux_tag[1]}
set term [$b findBTerm {aux_tag[20]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[20]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2167790 1239740 2171790 1243740
lappend selected_ports {aux_tag[20]}
set term [$b findBTerm {aux_tag[21]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[21]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2183790 1255740 2187790 1259740
lappend selected_ports {aux_tag[21]}
set term [$b findBTerm {aux_tag[22]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[22]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2199790 1255740 2203790 1259740
lappend selected_ports {aux_tag[22]}
set term [$b findBTerm {aux_tag[23]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[23]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2199790 1095740 2203790 1099740
lappend selected_ports {aux_tag[23]}
set term [$b findBTerm {aux_tag[24]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[24]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2199790 1271740 2203790 1275740
lappend selected_ports {aux_tag[24]}
set term [$b findBTerm {aux_tag[25]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[25]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2231790 1271740 2235790 1275740
lappend selected_ports {aux_tag[25]}
set term [$b findBTerm {aux_tag[26]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[26]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2215790 1271740 2219790 1275740
lappend selected_ports {aux_tag[26]}
set term [$b findBTerm {aux_tag[27]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[27]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2247790 1271740 2251790 1275740
lappend selected_ports {aux_tag[27]}
set term [$b findBTerm {aux_tag[28]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[28]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2087790 1175740 2091790 1179740
lappend selected_ports {aux_tag[28]}
set term [$b findBTerm {aux_tag[29]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[29]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2231790 1287740 2235790 1291740
lappend selected_ports {aux_tag[29]}
set term [$b findBTerm {aux_tag[2]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2119790 1111740 2123790 1115740
lappend selected_ports {aux_tag[2]}
set term [$b findBTerm {aux_tag[30]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[30]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2103790 1191740 2107790 1195740
lappend selected_ports {aux_tag[30]}
set term [$b findBTerm {aux_tag[31]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[31]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2343790 1111740 2347790 1115740
lappend selected_ports {aux_tag[31]}
set term [$b findBTerm {aux_tag[3]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2103790 1111740 2107790 1115740
lappend selected_ports {aux_tag[3]}
set term [$b findBTerm {aux_tag[4]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2087790 1159740 2091790 1163740
lappend selected_ports {aux_tag[4]}
set term [$b findBTerm {aux_tag[5]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2103790 1143740 2107790 1147740
lappend selected_ports {aux_tag[5]}
set term [$b findBTerm {aux_tag[6]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2119790 1095740 2123790 1099740
lappend selected_ports {aux_tag[6]}
set term [$b findBTerm {aux_tag[7]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2071790 1143740 2075790 1147740
lappend selected_ports {aux_tag[7]}
set term [$b findBTerm {aux_tag[8]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2359790 1127740 2363790 1131740
lappend selected_ports {aux_tag[8]}
set term [$b findBTerm {aux_tag[9]}]
if {$term eq "NULL"} {error {Missing native port aux_tag[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2295790 1047740 2299790 1051740
lappend selected_ports {aux_tag[9]}
set term [$b findBTerm {aux_valid}]
if {$term eq "NULL"} {error {Missing native port aux_valid}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2311790 1047740 2315790 1051740
lappend selected_ports {aux_valid}
set term [$b findBTerm {down_s_address[0]}]
if {$term eq "NULL"} {error {Missing native port down_s_address[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1018940 46190 1022940
lappend selected_ports {down_s_address[0]}
set term [$b findBTerm {down_s_address[1]}]
if {$term eq "NULL"} {error {Missing native port down_s_address[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 790940 113390 794940
lappend selected_ports {down_s_address[1]}
set term [$b findBTerm {down_s_address[2]}]
if {$term eq "NULL"} {error {Missing native port down_s_address[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 781340 46190 785340
lappend selected_ports {down_s_address[2]}
set term [$b findBTerm {down_s_address[3]}]
if {$term eq "NULL"} {error {Missing native port down_s_address[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 618140 113390 622140
lappend selected_ports {down_s_address[3]}
set term [$b findBTerm {down_s_address[4]}]
if {$term eq "NULL"} {error {Missing native port down_s_address[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1076540 46190 1080540
lappend selected_ports {down_s_address[4]}
set term [$b findBTerm {down_s_address[5]}]
if {$term eq "NULL"} {error {Missing native port down_s_address[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 634940 46190 638940
lappend selected_ports {down_s_address[5]}
set term [$b findBTerm {down_s_address[6]}]
if {$term eq "NULL"} {error {Missing native port down_s_address[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 867740 46190 871740
lappend selected_ports {down_s_address[6]}
set term [$b findBTerm {down_s_address[7]}]
if {$term eq "NULL"} {error {Missing native port down_s_address[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 807740 46190 811740
lappend selected_ports {down_s_address[7]}
set term [$b findBTerm {down_s_address[8]}]
if {$term eq "NULL"} {error {Missing native port down_s_address[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 176590 618140 180590 622140
lappend selected_ports {down_s_address[8]}
set term [$b findBTerm {down_s_address[9]}]
if {$term eq "NULL"} {error {Missing native port down_s_address[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 519740 46190 523740
lappend selected_ports {down_s_address[9]}
set term [$b findBTerm {down_s_ready}]
if {$term eq "NULL"} {error {Missing native port down_s_ready}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 771740 46190 775740
lappend selected_ports {down_s_ready}
set term [$b findBTerm {down_s_rsp_data[0]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1626140 46190 1630140
lappend selected_ports {down_s_rsp_data[0]}
set term [$b findBTerm {down_s_rsp_data[100]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[100]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2134940 46190 2138940
lappend selected_ports {down_s_rsp_data[100]}
set term [$b findBTerm {down_s_rsp_data[101]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[101]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2010140 46190 2014140
lappend selected_ports {down_s_rsp_data[101]}
set term [$b findBTerm {down_s_rsp_data[102]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[102]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2067740 46190 2071740
lappend selected_ports {down_s_rsp_data[102]}
set term [$b findBTerm {down_s_rsp_data[103]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[103]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2029340 46190 2033340
lappend selected_ports {down_s_rsp_data[103]}
set term [$b findBTerm {down_s_rsp_data[104]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[104]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 704540 46190 708540
lappend selected_ports {down_s_rsp_data[104]}
set term [$b findBTerm {down_s_rsp_data[105]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[105]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1837340 46190 1841340
lappend selected_ports {down_s_rsp_data[105]}
set term [$b findBTerm {down_s_rsp_data[106]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[106]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1827740 46190 1831740
lappend selected_ports {down_s_rsp_data[106]}
set term [$b findBTerm {down_s_rsp_data[107]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[107]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 598940 46190 602940
lappend selected_ports {down_s_rsp_data[107]}
set term [$b findBTerm {down_s_rsp_data[108]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[108]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 733340 46190 737340
lappend selected_ports {down_s_rsp_data[108]}
set term [$b findBTerm {down_s_rsp_data[109]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[109]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1962140 46190 1966140
lappend selected_ports {down_s_rsp_data[109]}
set term [$b findBTerm {down_s_rsp_data[10]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[10]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1904540 46190 1908540
lappend selected_ports {down_s_rsp_data[10]}
set term [$b findBTerm {down_s_rsp_data[110]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[110]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 762140 46190 766140
lappend selected_ports {down_s_rsp_data[110]}
set term [$b findBTerm {down_s_rsp_data[111]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[111]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 742940 46190 746940
lappend selected_ports {down_s_rsp_data[111]}
set term [$b findBTerm {down_s_rsp_data[112]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[112]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2125340 46190 2129340
lappend selected_ports {down_s_rsp_data[112]}
set term [$b findBTerm {down_s_rsp_data[113]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[113]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 714140 46190 718140
lappend selected_ports {down_s_rsp_data[113]}
set term [$b findBTerm {down_s_rsp_data[114]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[114]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1530140 46190 1534140
lappend selected_ports {down_s_rsp_data[114]}
set term [$b findBTerm {down_s_rsp_data[115]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[115]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2115740 46190 2119740
lappend selected_ports {down_s_rsp_data[115]}
set term [$b findBTerm {down_s_rsp_data[116]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[116]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1366940 46190 1370940
lappend selected_ports {down_s_rsp_data[116]}
set term [$b findBTerm {down_s_rsp_data[117]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[117]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1616540 46190 1620540
lappend selected_ports {down_s_rsp_data[117]}
set term [$b findBTerm {down_s_rsp_data[118]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[118]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1460540 46190 1464540
lappend selected_ports {down_s_rsp_data[118]}
set term [$b findBTerm {down_s_rsp_data[119]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[119]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1808540 46190 1812540
lappend selected_ports {down_s_rsp_data[119]}
set term [$b findBTerm {down_s_rsp_data[11]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[11]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1942940 46190 1946940
lappend selected_ports {down_s_rsp_data[11]}
set term [$b findBTerm {down_s_rsp_data[120]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[120]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1479740 46190 1483740
lappend selected_ports {down_s_rsp_data[120]}
set term [$b findBTerm {down_s_rsp_data[121]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[121]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2019740 46190 2023740
lappend selected_ports {down_s_rsp_data[121]}
set term [$b findBTerm {down_s_rsp_data[122]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[122]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1990940 46190 1994940
lappend selected_ports {down_s_rsp_data[122]}
set term [$b findBTerm {down_s_rsp_data[123]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[123]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1606940 46190 1610940
lappend selected_ports {down_s_rsp_data[123]}
set term [$b findBTerm {down_s_rsp_data[124]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[124]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2211740 46190 2215740
lappend selected_ports {down_s_rsp_data[124]}
set term [$b findBTerm {down_s_rsp_data[125]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[125]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 723740 46190 727740
lappend selected_ports {down_s_rsp_data[125]}
set term [$b findBTerm {down_s_rsp_data[126]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[126]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1318940 46190 1322940
lappend selected_ports {down_s_rsp_data[126]}
set term [$b findBTerm {down_s_rsp_data[127]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[127]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1846940 46190 1850940
lappend selected_ports {down_s_rsp_data[127]}
set term [$b findBTerm {down_s_rsp_data[12]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[12]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 310990 1251740 314990 1255740
lappend selected_ports {down_s_rsp_data[12]}
set term [$b findBTerm {down_s_rsp_data[13]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[13]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 243790 1290140 247790 1294140
lappend selected_ports {down_s_rsp_data[13]}
set term [$b findBTerm {down_s_rsp_data[14]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[14]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1894940 46190 1898940
lappend selected_ports {down_s_rsp_data[14]}
set term [$b findBTerm {down_s_rsp_data[15]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[15]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 397340 46190 401340
lappend selected_ports {down_s_rsp_data[15]}
set term [$b findBTerm {down_s_rsp_data[16]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[16]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 310940 46190 314940
lappend selected_ports {down_s_rsp_data[16]}
set term [$b findBTerm {down_s_rsp_data[17]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[17]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1232540 46190 1236540
lappend selected_ports {down_s_rsp_data[17]}
set term [$b findBTerm {down_s_rsp_data[18]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[18]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1328540 46190 1332540
lappend selected_ports {down_s_rsp_data[18]}
set term [$b findBTerm {down_s_rsp_data[19]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[19]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1594940 46190 1598940
lappend selected_ports {down_s_rsp_data[19]}
set term [$b findBTerm {down_s_rsp_data[1]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 838940 46190 842940
lappend selected_ports {down_s_rsp_data[1]}
set term [$b findBTerm {down_s_rsp_data[20]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[20]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 301340 46190 305340
lappend selected_ports {down_s_rsp_data[20]}
set term [$b findBTerm {down_s_rsp_data[21]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[21]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1249340 46190 1253340
lappend selected_ports {down_s_rsp_data[21]}
set term [$b findBTerm {down_s_rsp_data[22]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[22]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1117340 46190 1121340
lappend selected_ports {down_s_rsp_data[22]}
set term [$b findBTerm {down_s_rsp_data[23]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[23]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1002140 46190 1006140
lappend selected_ports {down_s_rsp_data[23]}
set term [$b findBTerm {down_s_rsp_data[24]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[24]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 858140 46190 862140
lappend selected_ports {down_s_rsp_data[24]}
set term [$b findBTerm {down_s_rsp_data[25]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[25]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 118940 46190 122940
lappend selected_ports {down_s_rsp_data[25]}
set term [$b findBTerm {down_s_rsp_data[26]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[26]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 406940 46190 410940
lappend selected_ports {down_s_rsp_data[26]}
set term [$b findBTerm {down_s_rsp_data[27]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[27]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1933340 46190 1937340
lappend selected_ports {down_s_rsp_data[27]}
set term [$b findBTerm {down_s_rsp_data[28]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[28]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1786940 46190 1790940
lappend selected_ports {down_s_rsp_data[28]}
set term [$b findBTerm {down_s_rsp_data[29]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[29]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1875740 46190 1879740
lappend selected_ports {down_s_rsp_data[29]}
set term [$b findBTerm {down_s_rsp_data[2]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1863740 46190 1867740
lappend selected_ports {down_s_rsp_data[2]}
set term [$b findBTerm {down_s_rsp_data[30]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[30]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1748540 46190 1752540
lappend selected_ports {down_s_rsp_data[30]}
set term [$b findBTerm {down_s_rsp_data[31]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[31]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1729340 46190 1733340
lappend selected_ports {down_s_rsp_data[31]}
set term [$b findBTerm {down_s_rsp_data[32]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[32]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 378140 46190 382140
lappend selected_ports {down_s_rsp_data[32]}
set term [$b findBTerm {down_s_rsp_data[33]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[33]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1191740 46190 1195740
lappend selected_ports {down_s_rsp_data[33]}
set term [$b findBTerm {down_s_rsp_data[34]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[34]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2230940 46190 2234940
lappend selected_ports {down_s_rsp_data[34]}
set term [$b findBTerm {down_s_rsp_data[35]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[35]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1357340 46190 1361340
lappend selected_ports {down_s_rsp_data[35]}
set term [$b findBTerm {down_s_rsp_data[36]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[36]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1309340 46190 1313340
lappend selected_ports {down_s_rsp_data[36]}
set term [$b findBTerm {down_s_rsp_data[37]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[37]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1299740 46190 1303740
lappend selected_ports {down_s_rsp_data[37]}
set term [$b findBTerm {down_s_rsp_data[38]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[38]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1510940 46190 1514940
lappend selected_ports {down_s_rsp_data[38]}
set term [$b findBTerm {down_s_rsp_data[39]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[39]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2182940 46190 2186940
lappend selected_ports {down_s_rsp_data[39]}
set term [$b findBTerm {down_s_rsp_data[3]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1923740 46190 1927740
lappend selected_ports {down_s_rsp_data[3]}
set term [$b findBTerm {down_s_rsp_data[40]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[40]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 426140 46190 430140
lappend selected_ports {down_s_rsp_data[40]}
set term [$b findBTerm {down_s_rsp_data[41]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[41]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2192540 46190 2196540
lappend selected_ports {down_s_rsp_data[41]}
set term [$b findBTerm {down_s_rsp_data[42]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[42]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 416540 46190 420540
lappend selected_ports {down_s_rsp_data[42]}
set term [$b findBTerm {down_s_rsp_data[43]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[43]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 387740 46190 391740
lappend selected_ports {down_s_rsp_data[43]}
set term [$b findBTerm {down_s_rsp_data[44]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[44]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2173340 46190 2177340
lappend selected_ports {down_s_rsp_data[44]}
set term [$b findBTerm {down_s_rsp_data[45]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[45]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 435740 46190 439740
lappend selected_ports {down_s_rsp_data[45]}
set term [$b findBTerm {down_s_rsp_data[46]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[46]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2163740 46190 2167740
lappend selected_ports {down_s_rsp_data[46]}
set term [$b findBTerm {down_s_rsp_data[47]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[47]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 502940 46190 506940
lappend selected_ports {down_s_rsp_data[47]}
set term [$b findBTerm {down_s_rsp_data[48]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[48]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2240540 46190 2244540
lappend selected_ports {down_s_rsp_data[48]}
set term [$b findBTerm {down_s_rsp_data[49]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[49]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1575740 46190 1579740
lappend selected_ports {down_s_rsp_data[49]}
set term [$b findBTerm {down_s_rsp_data[4]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1914140 46190 1918140
lappend selected_ports {down_s_rsp_data[4]}
set term [$b findBTerm {down_s_rsp_data[50]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[50]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2202140 46190 2206140
lappend selected_ports {down_s_rsp_data[50]}
set term [$b findBTerm {down_s_rsp_data[51]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[51]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1222940 46190 1226940
lappend selected_ports {down_s_rsp_data[51]}
set term [$b findBTerm {down_s_rsp_data[52]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[52]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2221340 46190 2225340
lappend selected_ports {down_s_rsp_data[52]}
set term [$b findBTerm {down_s_rsp_data[53]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[53]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1165340 46190 1169340
lappend selected_ports {down_s_rsp_data[53]}
set term [$b findBTerm {down_s_rsp_data[54]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[54]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1556540 46190 1560540
lappend selected_ports {down_s_rsp_data[54]}
set term [$b findBTerm {down_s_rsp_data[55]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[55]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1520540 46190 1524540
lappend selected_ports {down_s_rsp_data[55]}
set term [$b findBTerm {down_s_rsp_data[56]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[56]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1210940 46190 1214940
lappend selected_ports {down_s_rsp_data[56]}
set term [$b findBTerm {down_s_rsp_data[57]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[57]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1287740 46190 1291740
lappend selected_ports {down_s_rsp_data[57]}
set term [$b findBTerm {down_s_rsp_data[58]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[58]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1345340 46190 1349340
lappend selected_ports {down_s_rsp_data[58]}
set term [$b findBTerm {down_s_rsp_data[59]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[59]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1498940 46190 1502940
lappend selected_ports {down_s_rsp_data[59]}
set term [$b findBTerm {down_s_rsp_data[5]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 176590 1002140 180590 1006140
lappend selected_ports {down_s_rsp_data[5]}
set term [$b findBTerm {down_s_rsp_data[60]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[60]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1268540 46190 1272540
lappend selected_ports {down_s_rsp_data[60]}
set term [$b findBTerm {down_s_rsp_data[61]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[61]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1441340 46190 1445340
lappend selected_ports {down_s_rsp_data[61]}
set term [$b findBTerm {down_s_rsp_data[62]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[62]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1153340 46190 1157340
lappend selected_ports {down_s_rsp_data[62]}
set term [$b findBTerm {down_s_rsp_data[63]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[63]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1414940 46190 1418940
lappend selected_ports {down_s_rsp_data[63]}
set term [$b findBTerm {down_s_rsp_data[64]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[64]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 99740 46190 103740
lappend selected_ports {down_s_rsp_data[64]}
set term [$b findBTerm {down_s_rsp_data[65]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[65]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 176590 896540 180590 900540
lappend selected_ports {down_s_rsp_data[65]}
set term [$b findBTerm {down_s_rsp_data[66]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[66]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 138140 46190 142140
lappend selected_ports {down_s_rsp_data[66]}
set term [$b findBTerm {down_s_rsp_data[67]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[67]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 310990 1290140 314990 1294140
lappend selected_ports {down_s_rsp_data[67]}
set term [$b findBTerm {down_s_rsp_data[68]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[68]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1710140 46190 1714140
lappend selected_ports {down_s_rsp_data[68]}
set term [$b findBTerm {down_s_rsp_data[69]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[69]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 838940 113390 842940
lappend selected_ports {down_s_rsp_data[69]}
set term [$b findBTerm {down_s_rsp_data[6]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 982940 46190 986940
lappend selected_ports {down_s_rsp_data[6]}
set term [$b findBTerm {down_s_rsp_data[70]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[70]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1885340 46190 1889340
lappend selected_ports {down_s_rsp_data[70]}
set term [$b findBTerm {down_s_rsp_data[71]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[71]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 570140 46190 574140
lappend selected_ports {down_s_rsp_data[71]}
set term [$b findBTerm {down_s_rsp_data[72]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[72]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1693340 46190 1697340
lappend selected_ports {down_s_rsp_data[72]}
set term [$b findBTerm {down_s_rsp_data[73]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[73]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 666140 46190 670140
lappend selected_ports {down_s_rsp_data[73]}
set term [$b findBTerm {down_s_rsp_data[74]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[74]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 819740 46190 823740
lappend selected_ports {down_s_rsp_data[74]}
set term [$b findBTerm {down_s_rsp_data[75]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[75]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 176590 570140 180590 574140
lappend selected_ports {down_s_rsp_data[75]}
set term [$b findBTerm {down_s_rsp_data[76]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[76]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 445340 46190 449340
lappend selected_ports {down_s_rsp_data[76]}
set term [$b findBTerm {down_s_rsp_data[77]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[77]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 51790 1347740 55790 1351740
lappend selected_ports {down_s_rsp_data[77]}
set term [$b findBTerm {down_s_rsp_data[78]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[78]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 1386140 113390 1390140
lappend selected_ports {down_s_rsp_data[78]}
set term [$b findBTerm {down_s_rsp_data[79]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[79]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1386140 46190 1390140
lappend selected_ports {down_s_rsp_data[79]}
set term [$b findBTerm {down_s_rsp_data[7]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 368540 46190 372540
lappend selected_ports {down_s_rsp_data[7]}
set term [$b findBTerm {down_s_rsp_data[80]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[80]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2106140 46190 2110140
lappend selected_ports {down_s_rsp_data[80]}
set term [$b findBTerm {down_s_rsp_data[81]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[81]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1395740 46190 1399740
lappend selected_ports {down_s_rsp_data[81]}
set term [$b findBTerm {down_s_rsp_data[82]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[82]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 483740 46190 487740
lappend selected_ports {down_s_rsp_data[82]}
set term [$b findBTerm {down_s_rsp_data[83]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[83]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2096540 46190 2100540
lappend selected_ports {down_s_rsp_data[83]}
set term [$b findBTerm {down_s_rsp_data[84]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[84]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2086940 46190 2090940
lappend selected_ports {down_s_rsp_data[84]}
set term [$b findBTerm {down_s_rsp_data[85]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[85]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1405340 46190 1409340
lappend selected_ports {down_s_rsp_data[85]}
set term [$b findBTerm {down_s_rsp_data[86]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[86]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2048540 46190 2052540
lappend selected_ports {down_s_rsp_data[86]}
set term [$b findBTerm {down_s_rsp_data[87]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[87]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2154140 46190 2158140
lappend selected_ports {down_s_rsp_data[87]}
set term [$b findBTerm {down_s_rsp_data[88]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[88]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2038940 46190 2042940
lappend selected_ports {down_s_rsp_data[88]}
set term [$b findBTerm {down_s_rsp_data[89]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[89]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1981340 46190 1985340
lappend selected_ports {down_s_rsp_data[89]}
set term [$b findBTerm {down_s_rsp_data[8]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 176590 1040540 180590 1044540
lappend selected_ports {down_s_rsp_data[8]}
set term [$b findBTerm {down_s_rsp_data[90]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[90]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1818140 46190 1822140
lappend selected_ports {down_s_rsp_data[90]}
set term [$b findBTerm {down_s_rsp_data[91]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[91]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1971740 46190 1975740
lappend selected_ports {down_s_rsp_data[91]}
set term [$b findBTerm {down_s_rsp_data[92]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[92]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 560540 46190 564540
lappend selected_ports {down_s_rsp_data[92]}
set term [$b findBTerm {down_s_rsp_data[93]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[93]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2000540 46190 2004540
lappend selected_ports {down_s_rsp_data[93]}
set term [$b findBTerm {down_s_rsp_data[94]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[94]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1798940 46190 1802940
lappend selected_ports {down_s_rsp_data[94]}
set term [$b findBTerm {down_s_rsp_data[95]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[95]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 589340 46190 593340
lappend selected_ports {down_s_rsp_data[95]}
set term [$b findBTerm {down_s_rsp_data[96]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[96]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2144540 46190 2148540
lappend selected_ports {down_s_rsp_data[96]}
set term [$b findBTerm {down_s_rsp_data[97]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[97]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1539740 46190 1543740
lappend selected_ports {down_s_rsp_data[97]}
set term [$b findBTerm {down_s_rsp_data[98]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[98]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2058140 46190 2062140
lappend selected_ports {down_s_rsp_data[98]}
set term [$b findBTerm {down_s_rsp_data[99]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[99]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 2077340 46190 2081340
lappend selected_ports {down_s_rsp_data[99]}
set term [$b findBTerm {down_s_rsp_data[9]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_data[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 618140 46190 622140
lappend selected_ports {down_s_rsp_data[9]}
set term [$b findBTerm {down_s_rsp_ready}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_ready}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 656540 46190 660540
lappend selected_ports {down_s_rsp_ready}
set term [$b findBTerm {down_s_rsp_tag[0]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 944540 46190 948540
lappend selected_ports {down_s_rsp_tag[0]}
set term [$b findBTerm {down_s_rsp_tag[10]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[10]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 358940 46190 362940
lappend selected_ports {down_s_rsp_tag[10]}
set term [$b findBTerm {down_s_rsp_tag[11]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[11]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1126940 46190 1130940
lappend selected_ports {down_s_rsp_tag[11]}
set term [$b findBTerm {down_s_rsp_tag[12]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[12]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 176590 1405340 180590 1409340
lappend selected_ports {down_s_rsp_tag[12]}
set term [$b findBTerm {down_s_rsp_tag[13]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[13]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 829340 46190 833340
lappend selected_ports {down_s_rsp_tag[13]}
set term [$b findBTerm {down_s_rsp_tag[14]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[14]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1136540 46190 1140540
lappend selected_ports {down_s_rsp_tag[14]}
set term [$b findBTerm {down_s_rsp_tag[15]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[15]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 896540 113390 900540
lappend selected_ports {down_s_rsp_tag[15]}
set term [$b findBTerm {down_s_rsp_tag[16]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[16]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 963740 46190 967740
lappend selected_ports {down_s_rsp_tag[16]}
set term [$b findBTerm {down_s_rsp_tag[17]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[17]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 973340 46190 977340
lappend selected_ports {down_s_rsp_tag[17]}
set term [$b findBTerm {down_s_rsp_tag[18]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[18]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1683740 46190 1687740
lappend selected_ports {down_s_rsp_tag[18]}
set term [$b findBTerm {down_s_rsp_tag[19]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[19]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 176590 1386140 180590 1390140
lappend selected_ports {down_s_rsp_tag[19]}
set term [$b findBTerm {down_s_rsp_tag[1]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 954140 46190 958140
lappend selected_ports {down_s_rsp_tag[1]}
set term [$b findBTerm {down_s_rsp_tag[20]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[20]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1674140 46190 1678140
lappend selected_ports {down_s_rsp_tag[20]}
set term [$b findBTerm {down_s_rsp_tag[21]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[21]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1664540 46190 1668540
lappend selected_ports {down_s_rsp_tag[21]}
set term [$b findBTerm {down_s_rsp_tag[22]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[22]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1654940 46190 1658940
lappend selected_ports {down_s_rsp_tag[22]}
set term [$b findBTerm {down_s_rsp_tag[23]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[23]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1645340 46190 1649340
lappend selected_ports {down_s_rsp_tag[23]}
set term [$b findBTerm {down_s_rsp_tag[24]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[24]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 176590 1290140 180590 1294140
lappend selected_ports {down_s_rsp_tag[24]}
set term [$b findBTerm {down_s_rsp_tag[25]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[25]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 992540 46190 996540
lappend selected_ports {down_s_rsp_tag[25]}
set term [$b findBTerm {down_s_rsp_tag[26]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[26]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1635740 46190 1639740
lappend selected_ports {down_s_rsp_tag[26]}
set term [$b findBTerm {down_s_rsp_tag[27]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[27]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1098140 46190 1102140
lappend selected_ports {down_s_rsp_tag[27]}
set term [$b findBTerm {down_s_rsp_tag[28]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[28]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 1002140 113390 1006140
lappend selected_ports {down_s_rsp_tag[28]}
set term [$b findBTerm {down_s_rsp_tag[29]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[29]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1107740 46190 1111740
lappend selected_ports {down_s_rsp_tag[29]}
set term [$b findBTerm {down_s_rsp_tag[2]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 176590 1270940 180590 1274940
lappend selected_ports {down_s_rsp_tag[2]}
set term [$b findBTerm {down_s_rsp_tag[30]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[30]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 1021340 113390 1025340
lappend selected_ports {down_s_rsp_tag[30]}
set term [$b findBTerm {down_s_rsp_tag[31]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[31]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 454940 46190 458940
lappend selected_ports {down_s_rsp_tag[31]}
set term [$b findBTerm {down_s_rsp_tag[3]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1770140 46190 1774140
lappend selected_ports {down_s_rsp_tag[3]}
set term [$b findBTerm {down_s_rsp_tag[4]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1952540 46190 1956540
lappend selected_ports {down_s_rsp_tag[4]}
set term [$b findBTerm {down_s_rsp_tag[5]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1760540 46190 1764540
lappend selected_ports {down_s_rsp_tag[5]}
set term [$b findBTerm {down_s_rsp_tag[6]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 243790 1251740 247790 1255740
lappend selected_ports {down_s_rsp_tag[6]}
set term [$b findBTerm {down_s_rsp_tag[7]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 243790 1270940 247790 1274940
lappend selected_ports {down_s_rsp_tag[7]}
set term [$b findBTerm {down_s_rsp_tag[8]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 915740 113390 919740
lappend selected_ports {down_s_rsp_tag[8]}
set term [$b findBTerm {down_s_rsp_tag[9]}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_tag[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 810140 113390 814140
lappend selected_ports {down_s_rsp_tag[9]}
set term [$b findBTerm {down_s_rsp_valid}]
if {$term eq "NULL"} {error {Missing native port down_s_rsp_valid}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 848540 46190 852540
lappend selected_ports {down_s_rsp_valid}
set term [$b findBTerm {down_s_tag[0]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 790940 46190 794940
lappend selected_ports {down_s_tag[0]}
set term [$b findBTerm {down_s_tag[10]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[10]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 109340 46190 113340
lappend selected_ports {down_s_tag[10]}
set term [$b findBTerm {down_s_tag[11]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[11]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1088540 46190 1092540
lappend selected_ports {down_s_tag[11]}
set term [$b findBTerm {down_s_tag[12]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[12]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 1213340 113390 1217340
lappend selected_ports {down_s_tag[12]}
set term [$b findBTerm {down_s_tag[13]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[13]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 349340 46190 353340
lappend selected_ports {down_s_tag[13]}
set term [$b findBTerm {down_s_tag[14]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[14]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 903740 46190 907740
lappend selected_ports {down_s_tag[14]}
set term [$b findBTerm {down_s_tag[15]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[15]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 13340 46190 17340
lappend selected_ports {down_s_tag[15]}
set term [$b findBTerm {down_s_tag[16]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[16]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 877340 46190 881340
lappend selected_ports {down_s_tag[16]}
set term [$b findBTerm {down_s_tag[17]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[17]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 886940 46190 890940
lappend selected_ports {down_s_tag[17]}
set term [$b findBTerm {down_s_tag[18]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[18]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 550940 46190 554940
lappend selected_ports {down_s_tag[18]}
set term [$b findBTerm {down_s_tag[19]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[19]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 320540 46190 324540
lappend selected_ports {down_s_tag[19]}
set term [$b findBTerm {down_s_tag[1]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 608540 46190 612540
lappend selected_ports {down_s_tag[1]}
set term [$b findBTerm {down_s_tag[20]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[20]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 925340 46190 929340
lappend selected_ports {down_s_tag[20]}
set term [$b findBTerm {down_s_tag[21]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[21]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 1270940 113390 1274940
lappend selected_ports {down_s_tag[21]}
set term [$b findBTerm {down_s_tag[22]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[22]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 1251740 113390 1255740
lappend selected_ports {down_s_tag[22]}
set term [$b findBTerm {down_s_tag[23]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[23]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 493340 46190 497340
lappend selected_ports {down_s_tag[23]}
set term [$b findBTerm {down_s_tag[24]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[24]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 330140 46190 334140
lappend selected_ports {down_s_tag[24]}
set term [$b findBTerm {down_s_tag[25]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[25]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 579740 46190 583740
lappend selected_ports {down_s_tag[25]}
set term [$b findBTerm {down_s_tag[26]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[26]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 1232540 113390 1236540
lappend selected_ports {down_s_tag[26]}
set term [$b findBTerm {down_s_tag[27]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[27]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 176590 1251740 180590 1255740
lappend selected_ports {down_s_tag[27]}
set term [$b findBTerm {down_s_tag[28]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[28]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 915740 46190 919740
lappend selected_ports {down_s_tag[28]}
set term [$b findBTerm {down_s_tag[29]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[29]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 934940 46190 938940
lappend selected_ports {down_s_tag[29]}
set term [$b findBTerm {down_s_tag[2]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1038140 46190 1042140
lappend selected_ports {down_s_tag[2]}
set term [$b findBTerm {down_s_tag[30]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[30]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 646940 46190 650940
lappend selected_ports {down_s_tag[30]}
set term [$b findBTerm {down_s_tag[31]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[31]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 694940 46190 698940
lappend selected_ports {down_s_tag[31]}
set term [$b findBTerm {down_s_tag[3]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 637340 113390 641340
lappend selected_ports {down_s_tag[3]}
set term [$b findBTerm {down_s_tag[4]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 685340 46190 689340
lappend selected_ports {down_s_tag[4]}
set term [$b findBTerm {down_s_tag[5]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 339740 46190 343740
lappend selected_ports {down_s_tag[5]}
set term [$b findBTerm {down_s_tag[6]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 1057340 46190 1061340
lappend selected_ports {down_s_tag[6]}
set term [$b findBTerm {down_s_tag[7]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 109390 570140 113390 574140
lappend selected_ports {down_s_tag[7]}
set term [$b findBTerm {down_s_tag[8]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 538940 46190 542940
lappend selected_ports {down_s_tag[8]}
set term [$b findBTerm {down_s_tag[9]}]
if {$term eq "NULL"} {error {Missing native port down_s_tag[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 752540 46190 756540
lappend selected_ports {down_s_tag[9]}
set term [$b findBTerm {down_s_valid}]
if {$term eq "NULL"} {error {Missing native port down_s_valid}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 42190 675740 46190 679740
lappend selected_ports {down_s_valid}
set tie_index 0
foreach name $selected_ports {
 set term [$b findBTerm $name]
 set net [$term getNet]
 if {[$net getName] in {zero_ one_}} {
  if {[$term getIoType] ne "OUTPUT"} {error "Unexpected constant input port"}
  set master [expr {[$net getName] eq "zero_" ? "LOGIC0_X1" : "LOGIC1_X1"}]
  set tie [odb::dbInst_create $b [$db findMaster $master] NATIVE_PORT_TIE_$tie_index]
  $tie setLocation 2400000 [expr {1400000+$tie_index*5600}]
  $tie setPlacementStatus PLACED
  set split [odb::dbNet_create $b NATIVE_PORT_CONST_$tie_index]
  $split setSigType SIGNAL
  [$tie findITerm Z] connect $split
  $term disconnect
  $term connect $split
  incr tie_index
 }
 lappend selected [[$term getNet] getName]
}
if {$tie_index} {detailed_placement; check_placement}
foreach net [$b getNets] {
 if {[$net getSigType] in {POWER GROUND}} {$net setSpecial}
}
foreach grid [$b getTrackGrids] {odb::dbTrackGrid_destroy $grid}
source $p/make_tracks.tcl
write_db full-native.odb
set selected_ports [lsearch -all -inline -glob $selected_ports down_s_*]
set selected {}
foreach name $selected_ports {lappend selected [[[$b findBTerm $name] getNet] getName]}

set gc [$b getGCellGrid]
if {$gc ne "NULL"} {odb::dbGCellGrid_destroy $gc}
# The routing scratch DB keeps physical obstacles, cells and power conductors.
# The full native connectivity is retained in full-native.odb and restored below.
foreach term [$b getBTerms] {
 if {[$term getName] ni $selected_ports && [$term getSigType] ni {POWER GROUND}} {odb::dbBTerm_destroy $term}
}
foreach net [$b getNets] {
 if {[$net getName] ni $selected && [$net getSigType] ni {POWER GROUND}} {odb::dbNet_destroy $net}
}
set_routing_layers -signal metal2-metal10 -clock metal2-metal10
set_global_routing_layer_adjustment metal2-metal10 0.10
global_route -guide_file native.guide -allow_congestion -congestion_iterations 5
detailed_route -output_drc native.drc -droute_end_iter 24
write_db routed-subset.odb
write_def routed-subset.def
set f [open selected-nets.txt w]
foreach n [lsort -unique $selected] {puts $f $n}
close $f
