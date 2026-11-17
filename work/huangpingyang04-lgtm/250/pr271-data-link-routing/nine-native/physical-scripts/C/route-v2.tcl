set_thread_count $::env(SLURM_CPUS_PER_TASK)
set p /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $p/lib/NangateOpenCellLibrary_typical.lib
read_liberty {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s/audit08/base0/local_s_base.lib}
read_liberty {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/release/e_compact/block_v2_e_compact.lib}
read_liberty {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/release/g/block_v2_g.lib}
read_liberty {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt252/delivery/abstract/r_stream_local_typ.lib}
read_liberty {/public/home/yuzelu/project-circuit/issue250-j-e32-native-20261111-02/views/e_s32_ap64.lib}
read_liberty {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib}
read_db {/public/home/yuzelu/PingyangHuang/hpy-nine-native.lHJoC3yv/C/native-contacts.odb}
set b [ord::get_db_block]
set db [ord::get_db]
set tech [ord::get_db_tech]
set selected {}
set selected_ports {}
set term [$b findBTerm {outgoing_ack}]
if {$term eq "NULL"} {error {Missing native port outgoing_ack}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3153390 109340 3157390 113340
lappend selected_ports {outgoing_ack}
set term [$b findBTerm {outgoing_ack_ready}]
if {$term eq "NULL"} {error {Missing native port outgoing_ack_ready}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3237390 109340 3241390 113340
lappend selected_ports {outgoing_ack_ready}
set term [$b findBTerm {outgoing_addr[0]}]
if {$term eq "NULL"} {error {Missing native port outgoing_addr[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3226990 118940 3230990 122940
lappend selected_ports {outgoing_addr[0]}
set term [$b findBTerm {outgoing_addr[1]}]
if {$term eq "NULL"} {error {Missing native port outgoing_addr[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3203790 109340 3207790 113340
lappend selected_ports {outgoing_addr[1]}
set term [$b findBTerm {outgoing_addr[2]}]
if {$term eq "NULL"} {error {Missing native port outgoing_addr[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3237390 92540 3241390 96540
lappend selected_ports {outgoing_addr[2]}
set term [$b findBTerm {outgoing_addr[3]}]
if {$term eq "NULL"} {error {Missing native port outgoing_addr[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3270990 109340 3274990 113340
lappend selected_ports {outgoing_addr[3]}
set term [$b findBTerm {outgoing_addr[4]}]
if {$term eq "NULL"} {error {Missing native port outgoing_addr[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3170190 109340 3174190 113340
lappend selected_ports {outgoing_addr[4]}
set term [$b findBTerm {outgoing_addr[5]}]
if {$term eq "NULL"} {error {Missing native port outgoing_addr[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3213790 83740 3217790 87740
lappend selected_ports {outgoing_addr[5]}
set term [$b findBTerm {outgoing_addr[6]}]
if {$term eq "NULL"} {error {Missing native port outgoing_addr[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3203790 92540 3207790 96540
lappend selected_ports {outgoing_addr[6]}
set term [$b findBTerm {outgoing_addr[7]}]
if {$term eq "NULL"} {error {Missing native port outgoing_addr[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3203790 75740 3207790 79740
lappend selected_ports {outgoing_addr[7]}
set term [$b findBTerm {outgoing_addr[8]}]
if {$term eq "NULL"} {error {Missing native port outgoing_addr[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3237390 75740 3241390 79740
lappend selected_ports {outgoing_addr[8]}
set term [$b findBTerm {outgoing_addr[9]}]
if {$term eq "NULL"} {error {Missing native port outgoing_addr[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3170190 92540 3174190 96540
lappend selected_ports {outgoing_addr[9]}
set term [$b findBTerm {outgoing_data[0]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1086990 109340 1090990 113340
lappend selected_ports {outgoing_data[0]}
set term [$b findBTerm {outgoing_data[100]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[100]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1053390 109340 1057390 113340
lappend selected_ports {outgoing_data[100]}
set term [$b findBTerm {outgoing_data[101]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[101]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 801390 109340 805390 113340
lappend selected_ports {outgoing_data[101]}
set term [$b findBTerm {outgoing_data[102]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[102]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 926190 109340 930190 113340
lappend selected_ports {outgoing_data[102]}
set term [$b findBTerm {outgoing_data[103]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[103]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 918990 92540 922990 96540
lappend selected_ports {outgoing_data[103]}
set term [$b findBTerm {outgoing_data[104]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[104]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 894990 109340 898990 113340
lappend selected_ports {outgoing_data[104]}
set term [$b findBTerm {outgoing_data[105]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[105]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 868590 109340 872590 113340
lappend selected_ports {outgoing_data[105]}
set term [$b findBTerm {outgoing_data[106]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[106]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1204590 109340 1208590 113340
lappend selected_ports {outgoing_data[106]}
set term [$b findBTerm {outgoing_data[107]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[107]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 894990 92540 898990 96540
lappend selected_ports {outgoing_data[107]}
set term [$b findBTerm {outgoing_data[108]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[108]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 851790 109340 855790 113340
lappend selected_ports {outgoing_data[108]}
set term [$b findBTerm {outgoing_data[109]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[109]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 952590 109340 956590 113340
lappend selected_ports {outgoing_data[109]}
set term [$b findBTerm {outgoing_data[10]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[10]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1187790 92540 1191790 96540
lappend selected_ports {outgoing_data[10]}
set term [$b findBTerm {outgoing_data[110]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[110]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 851790 92540 855790 96540
lappend selected_ports {outgoing_data[110]}
set term [$b findBTerm {outgoing_data[111]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[111]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1154190 109340 1158190 113340
lappend selected_ports {outgoing_data[111]}
set term [$b findBTerm {outgoing_data[112]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[112]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 952590 92540 956590 96540
lappend selected_ports {outgoing_data[112]}
set term [$b findBTerm {outgoing_data[113]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[113]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1137390 109340 1141390 113340
lappend selected_ports {outgoing_data[113]}
set term [$b findBTerm {outgoing_data[114]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[114]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1154190 92540 1158190 96540
lappend selected_ports {outgoing_data[114]}
set term [$b findBTerm {outgoing_data[115]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[115]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 986190 109340 990190 113340
lappend selected_ports {outgoing_data[115]}
set term [$b findBTerm {outgoing_data[116]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[116]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1009390 125340 1013390 129340
lappend selected_ports {outgoing_data[116]}
set term [$b findBTerm {outgoing_data[117]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[117]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 961390 92540 965390 96540
lappend selected_ports {outgoing_data[117]}
set term [$b findBTerm {outgoing_data[118]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[118]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 54990 260540 58990 264540
lappend selected_ports {outgoing_data[118]}
set term [$b findBTerm {outgoing_data[119]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[119]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 54990 277340 58990 281340
lappend selected_ports {outgoing_data[119]}
set term [$b findBTerm {outgoing_data[11]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[11]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1221390 109340 1225390 113340
lappend selected_ports {outgoing_data[11]}
set term [$b findBTerm {outgoing_data[120]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[120]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 54990 310940 58990 314940
lappend selected_ports {outgoing_data[120]}
set term [$b findBTerm {outgoing_data[121]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[121]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1288590 109340 1292590 113340
lappend selected_ports {outgoing_data[121]}
set term [$b findBTerm {outgoing_data[122]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[122]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 54990 226940 58990 230940
lappend selected_ports {outgoing_data[122]}
set term [$b findBTerm {outgoing_data[123]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[123]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 54990 210140 58990 214140
lappend selected_ports {outgoing_data[123]}
set term [$b findBTerm {outgoing_data[124]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[124]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 532590 109340 536590 113340
lappend selected_ports {outgoing_data[124]}
set term [$b findBTerm {outgoing_data[125]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[125]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 54990 243740 58990 247740
lappend selected_ports {outgoing_data[125]}
set term [$b findBTerm {outgoing_data[126]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[126]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 750990 109340 754990 113340
lappend selected_ports {outgoing_data[126]}
set term [$b findBTerm {outgoing_data[127]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[127]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1110990 109340 1114990 113340
lappend selected_ports {outgoing_data[127]}
set term [$b findBTerm {outgoing_data[12]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[12]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1187790 75740 1191790 79740
lappend selected_ports {outgoing_data[12]}
set term [$b findBTerm {outgoing_data[13]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[13]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1204590 92540 1208590 96540
lappend selected_ports {outgoing_data[13]}
set term [$b findBTerm {outgoing_data[14]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[14]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1101390 92540 1105390 96540
lappend selected_ports {outgoing_data[14]}
set term [$b findBTerm {outgoing_data[15]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[15]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1137390 92540 1141390 96540
lappend selected_ports {outgoing_data[15]}
set term [$b findBTerm {outgoing_data[16]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[16]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1254990 109340 1258990 113340
lappend selected_ports {outgoing_data[16]}
set term [$b findBTerm {outgoing_data[17]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[17]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1110990 75740 1114990 79740
lappend selected_ports {outgoing_data[17]}
set term [$b findBTerm {outgoing_data[18]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[18]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 801390 92540 805390 96540
lappend selected_ports {outgoing_data[18]}
set term [$b findBTerm {outgoing_data[19]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[19]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 734190 109340 738190 113340
lappend selected_ports {outgoing_data[19]}
set term [$b findBTerm {outgoing_data[1]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1070190 109340 1074190 113340
lappend selected_ports {outgoing_data[1]}
set term [$b findBTerm {outgoing_data[20]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[20]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 784590 75740 788590 79740
lappend selected_ports {outgoing_data[20]}
set term [$b findBTerm {outgoing_data[21]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[21]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 827790 92540 831790 96540
lappend selected_ports {outgoing_data[21]}
set term [$b findBTerm {outgoing_data[22]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[22]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 868590 92540 872590 96540
lappend selected_ports {outgoing_data[22]}
set term [$b findBTerm {outgoing_data[23]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[23]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 986190 92540 990190 96540
lappend selected_ports {outgoing_data[23]}
set term [$b findBTerm {outgoing_data[24]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[24]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 851790 75740 855790 79740
lappend selected_ports {outgoing_data[24]}
set term [$b findBTerm {outgoing_data[25]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[25]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 827790 75740 831790 79740
lappend selected_ports {outgoing_data[25]}
set term [$b findBTerm {outgoing_data[26]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[26]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 801390 75740 805390 79740
lappend selected_ports {outgoing_data[26]}
set term [$b findBTerm {outgoing_data[27]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[27]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 868590 75740 872590 79740
lappend selected_ports {outgoing_data[27]}
set term [$b findBTerm {outgoing_data[28]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[28]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1019790 109340 1023790 113340
lappend selected_ports {outgoing_data[28]}
set term [$b findBTerm {outgoing_data[29]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[29]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1086990 92540 1090990 96540
lappend selected_ports {outgoing_data[29]}
set term [$b findBTerm {outgoing_data[2]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1137390 75740 1141390 79740
lappend selected_ports {outgoing_data[2]}
set term [$b findBTerm {outgoing_data[30]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[30]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1154190 75740 1158190 79740
lappend selected_ports {outgoing_data[30]}
set term [$b findBTerm {outgoing_data[31]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[31]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1019790 92540 1023790 96540
lappend selected_ports {outgoing_data[31]}
set term [$b findBTerm {outgoing_data[32]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[32]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1070190 92540 1074190 96540
lappend selected_ports {outgoing_data[32]}
set term [$b findBTerm {outgoing_data[33]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[33]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1086990 75740 1090990 79740
lappend selected_ports {outgoing_data[33]}
set term [$b findBTerm {outgoing_data[34]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[34]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1034990 82940 1038990 86940
lappend selected_ports {outgoing_data[34]}
set term [$b findBTerm {outgoing_data[35]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[35]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1019790 75740 1023790 79740
lappend selected_ports {outgoing_data[35]}
set term [$b findBTerm {outgoing_data[36]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[36]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1009390 50140 1013390 54140
lappend selected_ports {outgoing_data[36]}
set term [$b findBTerm {outgoing_data[37]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[37]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 986190 75740 990190 79740
lappend selected_ports {outgoing_data[37]}
set term [$b findBTerm {outgoing_data[38]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[38]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 179790 109340 183790 113340
lappend selected_ports {outgoing_data[38]}
set term [$b findBTerm {outgoing_data[39]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[39]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 474990 109340 478990 113340
lappend selected_ports {outgoing_data[39]}
set term [$b findBTerm {outgoing_data[3]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1070190 75740 1074190 79740
lappend selected_ports {outgoing_data[3]}
set term [$b findBTerm {outgoing_data[40]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[40]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 213390 109340 217390 113340
lappend selected_ports {outgoing_data[40]}
set term [$b findBTerm {outgoing_data[41]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[41]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 391790 99740 395790 103740
lappend selected_ports {outgoing_data[41]}
set term [$b findBTerm {outgoing_data[42]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[42]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 414990 109340 418990 113340
lappend selected_ports {outgoing_data[42]}
set term [$b findBTerm {outgoing_data[43]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[43]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 196590 92540 200590 96540
lappend selected_ports {outgoing_data[43]}
set term [$b findBTerm {outgoing_data[44]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[44]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 146190 109340 150190 113340
lappend selected_ports {outgoing_data[44]}
set term [$b findBTerm {outgoing_data[45]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[45]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 381390 109340 385390 113340
lappend selected_ports {outgoing_data[45]}
set term [$b findBTerm {outgoing_data[46]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[46]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 506190 109340 510190 113340
lappend selected_ports {outgoing_data[46]}
set term [$b findBTerm {outgoing_data[47]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[47]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 314190 109340 318190 113340
lappend selected_ports {outgoing_data[47]}
set term [$b findBTerm {outgoing_data[48]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[48]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 290190 109340 294190 113340
lappend selected_ports {outgoing_data[48]}
set term [$b findBTerm {outgoing_data[49]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[49]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 246990 109340 250990 113340
lappend selected_ports {outgoing_data[49]}
set term [$b findBTerm {outgoing_data[4]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1137390 58940 1141390 62940
lappend selected_ports {outgoing_data[4]}
set term [$b findBTerm {outgoing_data[50]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[50]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 683790 109340 687790 113340
lappend selected_ports {outgoing_data[50]}
set term [$b findBTerm {outgoing_data[51]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[51]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 482190 92540 486190 96540
lappend selected_ports {outgoing_data[51]}
set term [$b findBTerm {outgoing_data[52]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[52]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 330990 109340 334990 113340
lappend selected_ports {outgoing_data[52]}
set term [$b findBTerm {outgoing_data[53]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[53]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 750990 92540 754990 96540
lappend selected_ports {outgoing_data[53]}
set term [$b findBTerm {outgoing_data[54]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[54]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 448590 109340 452590 113340
lappend selected_ports {outgoing_data[54]}
set term [$b findBTerm {outgoing_data[55]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[55]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 263790 109340 267790 113340
lappend selected_ports {outgoing_data[55]}
set term [$b findBTerm {outgoing_data[56]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[56]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 717390 109340 721390 113340
lappend selected_ports {outgoing_data[56]}
set term [$b findBTerm {outgoing_data[57]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[57]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 734190 92540 738190 96540
lappend selected_ports {outgoing_data[57]}
set term [$b findBTerm {outgoing_data[58]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[58]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1111790 100540 1115790 104540
lappend selected_ports {outgoing_data[58]}
set term [$b findBTerm {outgoing_data[59]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[59]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 952590 75740 956590 79740
lappend selected_ports {outgoing_data[59]}
set term [$b findBTerm {outgoing_data[5]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1110990 58940 1114990 62940
lappend selected_ports {outgoing_data[5]}
set term [$b findBTerm {outgoing_data[60]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[60]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 827790 58940 831790 62940
lappend selected_ports {outgoing_data[60]}
set term [$b findBTerm {outgoing_data[61]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[61]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 910190 75740 914190 79740
lappend selected_ports {outgoing_data[61]}
set term [$b findBTerm {outgoing_data[62]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[62]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 918990 75740 922990 79740
lappend selected_ports {outgoing_data[62]}
set term [$b findBTerm {outgoing_data[63]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[63]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 986190 58940 990190 62940
lappend selected_ports {outgoing_data[63]}
set term [$b findBTerm {outgoing_data[64]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[64]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 851790 58940 855790 62940
lappend selected_ports {outgoing_data[64]}
set term [$b findBTerm {outgoing_data[65]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[65]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1019790 58940 1023790 62940
lappend selected_ports {outgoing_data[65]}
set term [$b findBTerm {outgoing_data[66]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[66]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1053390 92540 1057390 96540
lappend selected_ports {outgoing_data[66]}
set term [$b findBTerm {outgoing_data[67]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[67]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 801390 58940 805390 62940
lappend selected_ports {outgoing_data[67]}
set term [$b findBTerm {outgoing_data[68]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[68]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1086990 58940 1090990 62940
lappend selected_ports {outgoing_data[68]}
set term [$b findBTerm {outgoing_data[69]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[69]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1154190 58940 1158190 62940
lappend selected_ports {outgoing_data[69]}
set term [$b findBTerm {outgoing_data[6]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1137390 42140 1141390 46140
lappend selected_ports {outgoing_data[6]}
set term [$b findBTerm {outgoing_data[70]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[70]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1053390 75740 1057390 79740
lappend selected_ports {outgoing_data[70]}
set term [$b findBTerm {outgoing_data[71]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[71]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1053390 58940 1057390 62940
lappend selected_ports {outgoing_data[71]}
set term [$b findBTerm {outgoing_data[72]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[72]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1154190 42140 1158190 46140
lappend selected_ports {outgoing_data[72]}
set term [$b findBTerm {outgoing_data[73]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[73]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1070190 58940 1074190 62940
lappend selected_ports {outgoing_data[73]}
set term [$b findBTerm {outgoing_data[74]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[74]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1086990 42140 1090990 46140
lappend selected_ports {outgoing_data[74]}
set term [$b findBTerm {outgoing_data[75]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[75]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1053390 42140 1057390 46140
lappend selected_ports {outgoing_data[75]}
set term [$b findBTerm {outgoing_data[76]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[76]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1070190 42140 1074190 46140
lappend selected_ports {outgoing_data[76]}
set term [$b findBTerm {outgoing_data[77]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[77]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1053390 25340 1057390 29340
lappend selected_ports {outgoing_data[77]}
set term [$b findBTerm {outgoing_data[78]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[78]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 717390 92540 721390 96540
lappend selected_ports {outgoing_data[78]}
set term [$b findBTerm {outgoing_data[79]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[79]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 894990 75740 898990 79740
lappend selected_ports {outgoing_data[79]}
set term [$b findBTerm {outgoing_data[7]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1110990 42140 1114990 46140
lappend selected_ports {outgoing_data[7]}
set term [$b findBTerm {outgoing_data[80]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[80]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 750990 75740 754990 79740
lappend selected_ports {outgoing_data[80]}
set term [$b findBTerm {outgoing_data[81]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[81]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1120590 25340 1124590 29340
lappend selected_ports {outgoing_data[81]}
set term [$b findBTerm {outgoing_data[82]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[82]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 784590 58940 788590 62940
lappend selected_ports {outgoing_data[82]}
set term [$b findBTerm {outgoing_data[83]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[83]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 801390 42140 805390 46140
lappend selected_ports {outgoing_data[83]}
set term [$b findBTerm {outgoing_data[84]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[84]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 734190 75740 738190 79740
lappend selected_ports {outgoing_data[84]}
set term [$b findBTerm {outgoing_data[85]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[85]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 666990 109340 670990 113340
lappend selected_ports {outgoing_data[85]}
set term [$b findBTerm {outgoing_data[86]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[86]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 868590 58940 872590 62940
lappend selected_ports {outgoing_data[86]}
set term [$b findBTerm {outgoing_data[87]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[87]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 932590 49340 936590 53340
lappend selected_ports {outgoing_data[87]}
set term [$b findBTerm {outgoing_data[88]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[88]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1137390 25340 1141390 29340
lappend selected_ports {outgoing_data[88]}
set term [$b findBTerm {outgoing_data[89]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[89]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 851790 42140 855790 46140
lappend selected_ports {outgoing_data[89]}
set term [$b findBTerm {outgoing_data[8]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1221390 92540 1225390 96540
lappend selected_ports {outgoing_data[8]}
set term [$b findBTerm {outgoing_data[90]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[90]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 894990 58940 898990 62940
lappend selected_ports {outgoing_data[90]}
set term [$b findBTerm {outgoing_data[91]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[91]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1154190 25340 1158190 29340
lappend selected_ports {outgoing_data[91]}
set term [$b findBTerm {outgoing_data[92]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[92]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 868590 42140 872590 46140
lappend selected_ports {outgoing_data[92]}
set term [$b findBTerm {outgoing_data[93]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[93]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 918990 58940 922990 62940
lappend selected_ports {outgoing_data[93]}
set term [$b findBTerm {outgoing_data[94]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[94]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 894990 42140 898990 46140
lappend selected_ports {outgoing_data[94]}
set term [$b findBTerm {outgoing_data[95]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[95]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 952590 58940 956590 62940
lappend selected_ports {outgoing_data[95]}
set term [$b findBTerm {outgoing_data[96]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[96]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 952590 42140 956590 46140
lappend selected_ports {outgoing_data[96]}
set term [$b findBTerm {outgoing_data[97]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[97]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1204590 75740 1208590 79740
lappend selected_ports {outgoing_data[97]}
set term [$b findBTerm {outgoing_data[98]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[98]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 868590 25340 872590 29340
lappend selected_ports {outgoing_data[98]}
set term [$b findBTerm {outgoing_data[99]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[99]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1187790 58940 1191790 62940
lappend selected_ports {outgoing_data[99]}
set term [$b findBTerm {outgoing_data[9]}]
if {$term eq "NULL"} {error {Missing native port outgoing_data[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1221390 75740 1225390 79740
lappend selected_ports {outgoing_data[9]}
set term [$b findBTerm {outgoing_ready}]
if {$term eq "NULL"} {error {Missing native port outgoing_ready}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3246190 75740 3250190 79740
lappend selected_ports {outgoing_ready}
set term [$b findBTerm {outgoing_valid}]
if {$term eq "NULL"} {error {Missing native port outgoing_valid}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3170190 75740 3174190 79740
lappend selected_ports {outgoing_valid}
set term [$b findBTerm {peer_addr[0]}]
if {$term eq "NULL"} {error {Missing native port peer_addr[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3203790 58940 3207790 62940
lappend selected_ports {peer_addr[0]}
set term [$b findBTerm {peer_addr[1]}]
if {$term eq "NULL"} {error {Missing native port peer_addr[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3287790 109340 3291790 113340
lappend selected_ports {peer_addr[1]}
set term [$b findBTerm {peer_addr[2]}]
if {$term eq "NULL"} {error {Missing native port peer_addr[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3153390 92540 3157390 96540
lappend selected_ports {peer_addr[2]}
set term [$b findBTerm {peer_addr[3]}]
if {$term eq "NULL"} {error {Missing native port peer_addr[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3270990 92540 3274990 96540
lappend selected_ports {peer_addr[3]}
set term [$b findBTerm {peer_addr[4]}]
if {$term eq "NULL"} {error {Missing native port peer_addr[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3237390 58940 3241390 62940
lappend selected_ports {peer_addr[4]}
set term [$b findBTerm {peer_addr[5]}]
if {$term eq "NULL"} {error {Missing native port peer_addr[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3304590 109340 3308590 113340
lappend selected_ports {peer_addr[5]}
set term [$b findBTerm {peer_addr[6]}]
if {$term eq "NULL"} {error {Missing native port peer_addr[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3270990 75740 3274990 79740
lappend selected_ports {peer_addr[6]}
set term [$b findBTerm {peer_addr[7]}]
if {$term eq "NULL"} {error {Missing native port peer_addr[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3252590 58940 3256590 62940
lappend selected_ports {peer_addr[7]}
set term [$b findBTerm {peer_addr[8]}]
if {$term eq "NULL"} {error {Missing native port peer_addr[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3230190 42140 3234190 46140
lappend selected_ports {peer_addr[8]}
set term [$b findBTerm {peer_addr[9]}]
if {$term eq "NULL"} {error {Missing native port peer_addr[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3287790 92540 3291790 96540
lappend selected_ports {peer_addr[9]}
set term [$b findBTerm {peer_reserved}]
if {$term eq "NULL"} {error {Missing native port peer_reserved}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 3203790 42140 3207790 46140
lappend selected_ports {peer_reserved}
set term [$b findBTerm {projection_s_address[0]}]
if {$term eq "NULL"} {error {Missing native port projection_s_address[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1106940 18190 1110940
lappend selected_ports {projection_s_address[0]}
set term [$b findBTerm {projection_s_address[1]}]
if {$term eq "NULL"} {error {Missing native port projection_s_address[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1135740 18190 1139740
lappend selected_ports {projection_s_address[1]}
set term [$b findBTerm {projection_s_address[2]}]
if {$term eq "NULL"} {error {Missing native port projection_s_address[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 396540 18190 400540
lappend selected_ports {projection_s_address[2]}
set term [$b findBTerm {projection_s_address[3]}]
if {$term eq "NULL"} {error {Missing native port projection_s_address[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 367740 18190 371740
lappend selected_ports {projection_s_address[3]}
set term [$b findBTerm {projection_s_address[4]}]
if {$term eq "NULL"} {error {Missing native port projection_s_address[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1097340 18190 1101340
lappend selected_ports {projection_s_address[4]}
set term [$b findBTerm {projection_s_address[5]}]
if {$term eq "NULL"} {error {Missing native port projection_s_address[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 377340 18190 381340
lappend selected_ports {projection_s_address[5]}
set term [$b findBTerm {projection_s_address[6]}]
if {$term eq "NULL"} {error {Missing native port projection_s_address[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2230140 18190 2234140
lappend selected_ports {projection_s_address[6]}
set term [$b findBTerm {projection_s_address[7]}]
if {$term eq "NULL"} {error {Missing native port projection_s_address[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1087740 18190 1091740
lappend selected_ports {projection_s_address[7]}
set term [$b findBTerm {projection_s_address[8]}]
if {$term eq "NULL"} {error {Missing native port projection_s_address[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2249340 18190 2253340
lappend selected_ports {projection_s_address[8]}
set term [$b findBTerm {projection_s_address[9]}]
if {$term eq "NULL"} {error {Missing native port projection_s_address[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2239740 18190 2243740
lappend selected_ports {projection_s_address[9]}
set term [$b findBTerm {projection_s_ready}]
if {$term eq "NULL"} {error {Missing native port projection_s_ready}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1116540 18190 1120540
lappend selected_ports {projection_s_ready}
set term [$b findBTerm {projection_s_rsp_data[0]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2278140 18190 2282140
lappend selected_ports {projection_s_rsp_data[0]}
set term [$b findBTerm {projection_s_rsp_data[100]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[100]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1932540 18190 1936540
lappend selected_ports {projection_s_rsp_data[100]}
set term [$b findBTerm {projection_s_rsp_data[101]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[101]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1586940 18190 1590940
lappend selected_ports {projection_s_rsp_data[101]}
set term [$b findBTerm {projection_s_rsp_data[102]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[102]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1990140 18190 1994140
lappend selected_ports {projection_s_rsp_data[102]}
set term [$b findBTerm {projection_s_rsp_data[103]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[103]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2038140 18190 2042140
lappend selected_ports {projection_s_rsp_data[103]}
set term [$b findBTerm {projection_s_rsp_data[104]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[104]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1577340 18190 1581340
lappend selected_ports {projection_s_rsp_data[104]}
set term [$b findBTerm {projection_s_rsp_data[105]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[105]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2134140 18190 2138140
lappend selected_ports {projection_s_rsp_data[105]}
set term [$b findBTerm {projection_s_rsp_data[106]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[106]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1481340 18190 1485340
lappend selected_ports {projection_s_rsp_data[106]}
set term [$b findBTerm {projection_s_rsp_data[107]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[107]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 732540 18190 736540
lappend selected_ports {projection_s_rsp_data[107]}
set term [$b findBTerm {projection_s_rsp_data[108]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[108]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 703740 18190 707740
lappend selected_ports {projection_s_rsp_data[108]}
set term [$b findBTerm {projection_s_rsp_data[109]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[109]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2105340 18190 2109340
lappend selected_ports {projection_s_rsp_data[109]}
set term [$b findBTerm {projection_s_rsp_data[10]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[10]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1519740 18190 1523740
lappend selected_ports {projection_s_rsp_data[10]}
set term [$b findBTerm {projection_s_rsp_data[110]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[110]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 694140 18190 698140
lappend selected_ports {projection_s_rsp_data[110]}
set term [$b findBTerm {projection_s_rsp_data[111]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[111]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 713340 18190 717340
lappend selected_ports {projection_s_rsp_data[111]}
set term [$b findBTerm {projection_s_rsp_data[112]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[112]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1922940 18190 1926940
lappend selected_ports {projection_s_rsp_data[112]}
set term [$b findBTerm {projection_s_rsp_data[113]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[113]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1558140 18190 1562140
lappend selected_ports {projection_s_rsp_data[113]}
set term [$b findBTerm {projection_s_rsp_data[114]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[114]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1471740 18190 1475740
lappend selected_ports {projection_s_rsp_data[114]}
set term [$b findBTerm {projection_s_rsp_data[115]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[115]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1913340 18190 1917340
lappend selected_ports {projection_s_rsp_data[115]}
set term [$b findBTerm {projection_s_rsp_data[116]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[116]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1788540 18190 1792540
lappend selected_ports {projection_s_rsp_data[116]}
set term [$b findBTerm {projection_s_rsp_data[117]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[117]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2018940 18190 2022940
lappend selected_ports {projection_s_rsp_data[117]}
set term [$b findBTerm {projection_s_rsp_data[118]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[118]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1625340 18190 1629340
lappend selected_ports {projection_s_rsp_data[118]}
set term [$b findBTerm {projection_s_rsp_data[119]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[119]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2124540 18190 2128540
lappend selected_ports {projection_s_rsp_data[119]}
set term [$b findBTerm {projection_s_rsp_data[11]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[11]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1462140 18190 1466140
lappend selected_ports {projection_s_rsp_data[11]}
set term [$b findBTerm {projection_s_rsp_data[120]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[120]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 914940 18190 918940
lappend selected_ports {projection_s_rsp_data[120]}
set term [$b findBTerm {projection_s_rsp_data[121]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[121]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1548540 18190 1552540
lappend selected_ports {projection_s_rsp_data[121]}
set term [$b findBTerm {projection_s_rsp_data[122]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[122]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2076540 18190 2080540
lappend selected_ports {projection_s_rsp_data[122]}
set term [$b findBTerm {projection_s_rsp_data[123]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[123]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2028540 18190 2032540
lappend selected_ports {projection_s_rsp_data[123]}
set term [$b findBTerm {projection_s_rsp_data[124]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[124]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1778940 18190 1782940
lappend selected_ports {projection_s_rsp_data[124]}
set term [$b findBTerm {projection_s_rsp_data[125]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[125]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 722940 18190 726940
lappend selected_ports {projection_s_rsp_data[125]}
set term [$b findBTerm {projection_s_rsp_data[126]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[126]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1721340 18190 1725340
lappend selected_ports {projection_s_rsp_data[126]}
set term [$b findBTerm {projection_s_rsp_data[127]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[127]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1567740 18190 1571740
lappend selected_ports {projection_s_rsp_data[127]}
set term [$b findBTerm {projection_s_rsp_data[12]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[12]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2306940 18190 2310940
lappend selected_ports {projection_s_rsp_data[12]}
set term [$b findBTerm {projection_s_rsp_data[13]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[13]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2287740 18190 2291740
lappend selected_ports {projection_s_rsp_data[13]}
set term [$b findBTerm {projection_s_rsp_data[14]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[14]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1538940 18190 1542940
lappend selected_ports {projection_s_rsp_data[14]}
set term [$b findBTerm {projection_s_rsp_data[15]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[15]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1318140 18190 1322140
lappend selected_ports {projection_s_rsp_data[15]}
set term [$b findBTerm {projection_s_rsp_data[16]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[16]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 886140 18190 890140
lappend selected_ports {projection_s_rsp_data[16]}
set term [$b findBTerm {projection_s_rsp_data[17]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[17]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1826940 18190 1830940
lappend selected_ports {projection_s_rsp_data[17]}
set term [$b findBTerm {projection_s_rsp_data[18]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[18]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1769340 18190 1773340
lappend selected_ports {projection_s_rsp_data[18]}
set term [$b findBTerm {projection_s_rsp_data[19]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[19]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1711740 18190 1715740
lappend selected_ports {projection_s_rsp_data[19]}
set term [$b findBTerm {projection_s_rsp_data[1]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1068540 18190 1072540
lappend selected_ports {projection_s_rsp_data[1]}
set term [$b findBTerm {projection_s_rsp_data[20]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[20]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1759740 18190 1763740
lappend selected_ports {projection_s_rsp_data[20]}
set term [$b findBTerm {projection_s_rsp_data[21]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[21]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1490940 18190 1494940
lappend selected_ports {projection_s_rsp_data[21]}
set term [$b findBTerm {projection_s_rsp_data[22]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[22]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 684540 18190 688540
lappend selected_ports {projection_s_rsp_data[22]}
set term [$b findBTerm {projection_s_rsp_data[23]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[23]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2162940 18190 2166940
lappend selected_ports {projection_s_rsp_data[23]}
set term [$b findBTerm {projection_s_rsp_data[24]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[24]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1222140 18190 1226140
lappend selected_ports {projection_s_rsp_data[24]}
set term [$b findBTerm {projection_s_rsp_data[25]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[25]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 742140 18190 746140
lappend selected_ports {projection_s_rsp_data[25]}
set term [$b findBTerm {projection_s_rsp_data[26]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[26]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1164540 18190 1168540
lappend selected_ports {projection_s_rsp_data[26]}
set term [$b findBTerm {projection_s_rsp_data[27]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[27]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1510140 18190 1514140
lappend selected_ports {projection_s_rsp_data[27]}
set term [$b findBTerm {projection_s_rsp_data[28]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[28]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1202940 18190 1206940
lappend selected_ports {projection_s_rsp_data[28]}
set term [$b findBTerm {projection_s_rsp_data[29]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[29]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1615740 18190 1619740
lappend selected_ports {projection_s_rsp_data[29]}
set term [$b findBTerm {projection_s_rsp_data[2]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1663740 18190 1667740
lappend selected_ports {projection_s_rsp_data[2]}
set term [$b findBTerm {projection_s_rsp_data[30]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[30]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1673340 18190 1677340
lappend selected_ports {projection_s_rsp_data[30]}
set term [$b findBTerm {projection_s_rsp_data[31]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[31]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1606140 18190 1610140
lappend selected_ports {projection_s_rsp_data[31]}
set term [$b findBTerm {projection_s_rsp_data[32]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[32]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 866940 18190 870940
lappend selected_ports {projection_s_rsp_data[32]}
set term [$b findBTerm {projection_s_rsp_data[33]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[33]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 876540 18190 880540
lappend selected_ports {projection_s_rsp_data[33]}
set term [$b findBTerm {projection_s_rsp_data[34]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[34]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1817340 18190 1821340
lappend selected_ports {projection_s_rsp_data[34]}
set term [$b findBTerm {projection_s_rsp_data[35]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[35]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1865340 18190 1869340
lappend selected_ports {projection_s_rsp_data[35]}
set term [$b findBTerm {projection_s_rsp_data[36]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[36]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1884540 18190 1888540
lappend selected_ports {projection_s_rsp_data[36]}
set term [$b findBTerm {projection_s_rsp_data[37]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[37]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 857340 18190 861340
lappend selected_ports {projection_s_rsp_data[37]}
set term [$b findBTerm {projection_s_rsp_data[38]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[38]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1855740 18190 1859740
lappend selected_ports {projection_s_rsp_data[38]}
set term [$b findBTerm {projection_s_rsp_data[39]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[39]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1903740 18190 1907740
lappend selected_ports {projection_s_rsp_data[39]}
set term [$b findBTerm {projection_s_rsp_data[3]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1529340 18190 1533340
lappend selected_ports {projection_s_rsp_data[3]}
set term [$b findBTerm {projection_s_rsp_data[40]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[40]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 809340 18190 813340
lappend selected_ports {projection_s_rsp_data[40]}
set term [$b findBTerm {projection_s_rsp_data[41]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[41]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1874940 18190 1878940
lappend selected_ports {projection_s_rsp_data[41]}
set term [$b findBTerm {projection_s_rsp_data[42]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[42]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 838140 18190 842140
lappend selected_ports {projection_s_rsp_data[42]}
set term [$b findBTerm {projection_s_rsp_data[43]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[43]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 847740 18190 851740
lappend selected_ports {projection_s_rsp_data[43]}
set term [$b findBTerm {projection_s_rsp_data[44]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[44]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1894140 18190 1898140
lappend selected_ports {projection_s_rsp_data[44]}
set term [$b findBTerm {projection_s_rsp_data[45]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[45]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 818940 18190 822940
lappend selected_ports {projection_s_rsp_data[45]}
set term [$b findBTerm {projection_s_rsp_data[46]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[46]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1951740 18190 1955740
lappend selected_ports {projection_s_rsp_data[46]}
set term [$b findBTerm {projection_s_rsp_data[47]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[47]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 761340 18190 765340
lappend selected_ports {projection_s_rsp_data[47]}
set term [$b findBTerm {projection_s_rsp_data[48]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[48]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1740540 18190 1744540
lappend selected_ports {projection_s_rsp_data[48]}
set term [$b findBTerm {projection_s_rsp_data[49]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[49]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1730940 18190 1734940
lappend selected_ports {projection_s_rsp_data[49]}
set term [$b findBTerm {projection_s_rsp_data[4]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1644540 18190 1648540
lappend selected_ports {projection_s_rsp_data[4]}
set term [$b findBTerm {projection_s_rsp_data[50]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[50]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1846140 18190 1850140
lappend selected_ports {projection_s_rsp_data[50]}
set term [$b findBTerm {projection_s_rsp_data[51]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[51]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 895740 18190 899740
lappend selected_ports {projection_s_rsp_data[51]}
set term [$b findBTerm {projection_s_rsp_data[52]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[52]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1807740 18190 1811740
lappend selected_ports {projection_s_rsp_data[52]}
set term [$b findBTerm {projection_s_rsp_data[53]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[53]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 924540 18190 928540
lappend selected_ports {projection_s_rsp_data[53]}
set term [$b findBTerm {projection_s_rsp_data[54]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[54]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1836540 18190 1840540
lappend selected_ports {projection_s_rsp_data[54]}
set term [$b findBTerm {projection_s_rsp_data[55]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[55]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1750140 18190 1754140
lappend selected_ports {projection_s_rsp_data[55]}
set term [$b findBTerm {projection_s_rsp_data[56]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[56]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 905340 18190 909340
lappend selected_ports {projection_s_rsp_data[56]}
set term [$b findBTerm {projection_s_rsp_data[57]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[57]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1020540 18190 1024540
lappend selected_ports {projection_s_rsp_data[57]}
set term [$b findBTerm {projection_s_rsp_data[58]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[58]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1702140 18190 1706140
lappend selected_ports {projection_s_rsp_data[58]}
set term [$b findBTerm {projection_s_rsp_data[59]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[59]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1692540 18190 1696540
lappend selected_ports {projection_s_rsp_data[59]}
set term [$b findBTerm {projection_s_rsp_data[5]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1058940 18190 1062940
lappend selected_ports {projection_s_rsp_data[5]}
set term [$b findBTerm {projection_s_rsp_data[60]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[60]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1798140 18190 1802140
lappend selected_ports {projection_s_rsp_data[60]}
set term [$b findBTerm {projection_s_rsp_data[61]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[61]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1634940 18190 1638940
lappend selected_ports {projection_s_rsp_data[61]}
set term [$b findBTerm {projection_s_rsp_data[62]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[62]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1030140 18190 1034140
lappend selected_ports {projection_s_rsp_data[62]}
set term [$b findBTerm {projection_s_rsp_data[63]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[63]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1682940 18190 1686940
lappend selected_ports {projection_s_rsp_data[63]}
set term [$b findBTerm {projection_s_rsp_data[64]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[64]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1001340 18190 1005340
lappend selected_ports {projection_s_rsp_data[64]}
set term [$b findBTerm {projection_s_rsp_data[65]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[65]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 972540 18190 976540
lappend selected_ports {projection_s_rsp_data[65]}
set term [$b findBTerm {projection_s_rsp_data[66]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[66]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 962940 18190 966940
lappend selected_ports {projection_s_rsp_data[66]}
set term [$b findBTerm {projection_s_rsp_data[67]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[67]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1442940 18190 1446940
lappend selected_ports {projection_s_rsp_data[67]}
set term [$b findBTerm {projection_s_rsp_data[68]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[68]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1654140 18190 1658140
lappend selected_ports {projection_s_rsp_data[68]}
set term [$b findBTerm {projection_s_rsp_data[69]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[69]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 982140 18190 986140
lappend selected_ports {projection_s_rsp_data[69]}
set term [$b findBTerm {projection_s_rsp_data[6]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1250940 18190 1254940
lappend selected_ports {projection_s_rsp_data[6]}
set term [$b findBTerm {projection_s_rsp_data[70]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[70]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1327740 18190 1331740
lappend selected_ports {projection_s_rsp_data[70]}
set term [$b findBTerm {projection_s_rsp_data[71]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[71]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1049340 18190 1053340
lappend selected_ports {projection_s_rsp_data[71]}
set term [$b findBTerm {projection_s_rsp_data[72]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[72]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1039740 18190 1043740
lappend selected_ports {projection_s_rsp_data[72]}
set term [$b findBTerm {projection_s_rsp_data[73]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[73]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1337340 18190 1341340
lappend selected_ports {projection_s_rsp_data[73]}
set term [$b findBTerm {projection_s_rsp_data[74]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[74]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2297340 18190 2301340
lappend selected_ports {projection_s_rsp_data[74]}
set term [$b findBTerm {projection_s_rsp_data[75]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[75]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 934140 18190 938140
lappend selected_ports {projection_s_rsp_data[75]}
set term [$b findBTerm {projection_s_rsp_data[76]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[76]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 953340 18190 957340
lappend selected_ports {projection_s_rsp_data[76]}
set term [$b findBTerm {projection_s_rsp_data[77]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[77]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1078140 18190 1082140
lappend selected_ports {projection_s_rsp_data[77]}
set term [$b findBTerm {projection_s_rsp_data[78]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[78]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 943740 18190 947740
lappend selected_ports {projection_s_rsp_data[78]}
set term [$b findBTerm {projection_s_rsp_data[79]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[79]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 991740 18190 995740
lappend selected_ports {projection_s_rsp_data[79]}
set term [$b findBTerm {projection_s_rsp_data[7]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2326140 18190 2330140
lappend selected_ports {projection_s_rsp_data[7]}
set term [$b findBTerm {projection_s_rsp_data[80]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[80]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1999740 18190 2003740
lappend selected_ports {projection_s_rsp_data[80]}
set term [$b findBTerm {projection_s_rsp_data[81]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[81]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 780540 18190 784540
lappend selected_ports {projection_s_rsp_data[81]}
set term [$b findBTerm {projection_s_rsp_data[82]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[82]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 790140 18190 794140
lappend selected_ports {projection_s_rsp_data[82]}
set term [$b findBTerm {projection_s_rsp_data[83]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[83]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1980540 18190 1984540
lappend selected_ports {projection_s_rsp_data[83]}
set term [$b findBTerm {projection_s_rsp_data[84]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[84]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 799740 18190 803740
lappend selected_ports {projection_s_rsp_data[84]}
set term [$b findBTerm {projection_s_rsp_data[85]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[85]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2066940 18190 2070940
lappend selected_ports {projection_s_rsp_data[85]}
set term [$b findBTerm {projection_s_rsp_data[86]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[86]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2057340 18190 2061340
lappend selected_ports {projection_s_rsp_data[86]}
set term [$b findBTerm {projection_s_rsp_data[87]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[87]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1942140 18190 1946140
lappend selected_ports {projection_s_rsp_data[87]}
set term [$b findBTerm {projection_s_rsp_data[88]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[88]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2047740 18190 2051740
lappend selected_ports {projection_s_rsp_data[88]}
set term [$b findBTerm {projection_s_rsp_data[89]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[89]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2095740 18190 2099740
lappend selected_ports {projection_s_rsp_data[89]}
set term [$b findBTerm {projection_s_rsp_data[8]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1010940 18190 1014940
lappend selected_ports {projection_s_rsp_data[8]}
set term [$b findBTerm {projection_s_rsp_data[90]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[90]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2114940 18190 2118940
lappend selected_ports {projection_s_rsp_data[90]}
set term [$b findBTerm {projection_s_rsp_data[91]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[91]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1596540 18190 1600540
lappend selected_ports {projection_s_rsp_data[91]}
set term [$b findBTerm {projection_s_rsp_data[92]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[92]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 770940 18190 774940
lappend selected_ports {projection_s_rsp_data[92]}
set term [$b findBTerm {projection_s_rsp_data[93]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[93]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2086140 18190 2090140
lappend selected_ports {projection_s_rsp_data[93]}
set term [$b findBTerm {projection_s_rsp_data[94]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[94]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2143740 18190 2147740
lappend selected_ports {projection_s_rsp_data[94]}
set term [$b findBTerm {projection_s_rsp_data[95]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[95]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 751740 18190 755740
lappend selected_ports {projection_s_rsp_data[95]}
set term [$b findBTerm {projection_s_rsp_data[96]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[96]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 828540 18190 832540
lappend selected_ports {projection_s_rsp_data[96]}
set term [$b findBTerm {projection_s_rsp_data[97]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[97]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1970940 18190 1974940
lappend selected_ports {projection_s_rsp_data[97]}
set term [$b findBTerm {projection_s_rsp_data[98]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[98]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2009340 18190 2013340
lappend selected_ports {projection_s_rsp_data[98]}
set term [$b findBTerm {projection_s_rsp_data[99]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[99]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1961340 18190 1965340
lappend selected_ports {projection_s_rsp_data[99]}
set term [$b findBTerm {projection_s_rsp_data[9]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_data[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2316540 18190 2320540
lappend selected_ports {projection_s_rsp_data[9]}
set term [$b findBTerm {projection_s_rsp_ready}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_ready}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 454140 18190 458140
lappend selected_ports {projection_s_rsp_ready}
set term [$b findBTerm {projection_s_rsp_tag[0]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1385340 18190 1389340
lappend selected_ports {projection_s_rsp_tag[0]}
set term [$b findBTerm {projection_s_rsp_tag[10]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[10]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2258940 18190 2262940
lappend selected_ports {projection_s_rsp_tag[10]}
set term [$b findBTerm {projection_s_rsp_tag[11]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[11]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1404540 18190 1408540
lappend selected_ports {projection_s_rsp_tag[11]}
set term [$b findBTerm {projection_s_rsp_tag[12]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[12]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1433340 18190 1437340
lappend selected_ports {projection_s_rsp_tag[12]}
set term [$b findBTerm {projection_s_rsp_tag[13]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[13]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1154940 18190 1158940
lappend selected_ports {projection_s_rsp_tag[13]}
set term [$b findBTerm {projection_s_rsp_tag[14]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[14]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1346940 18190 1350940
lappend selected_ports {projection_s_rsp_tag[14]}
set term [$b findBTerm {projection_s_rsp_tag[15]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[15]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1212540 18190 1216540
lappend selected_ports {projection_s_rsp_tag[15]}
set term [$b findBTerm {projection_s_rsp_tag[16]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[16]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1356540 18190 1360540
lappend selected_ports {projection_s_rsp_tag[16]}
set term [$b findBTerm {projection_s_rsp_tag[17]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[17]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 607740 18190 611740
lappend selected_ports {projection_s_rsp_tag[17]}
set term [$b findBTerm {projection_s_rsp_tag[18]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[18]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1366140 18190 1370140
lappend selected_ports {projection_s_rsp_tag[18]}
set term [$b findBTerm {projection_s_rsp_tag[19]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[19]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1394940 18190 1398940
lappend selected_ports {projection_s_rsp_tag[19]}
set term [$b findBTerm {projection_s_rsp_tag[1]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 617340 18190 621340
lappend selected_ports {projection_s_rsp_tag[1]}
set term [$b findBTerm {projection_s_rsp_tag[20]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[20]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2172540 18190 2176540
lappend selected_ports {projection_s_rsp_tag[20]}
set term [$b findBTerm {projection_s_rsp_tag[21]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[21]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1375740 18190 1379740
lappend selected_ports {projection_s_rsp_tag[21]}
set term [$b findBTerm {projection_s_rsp_tag[22]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[22]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2210940 18190 2214940
lappend selected_ports {projection_s_rsp_tag[22]}
set term [$b findBTerm {projection_s_rsp_tag[23]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[23]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1414140 18190 1418140
lappend selected_ports {projection_s_rsp_tag[23]}
set term [$b findBTerm {projection_s_rsp_tag[24]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[24]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 646140 18190 650140
lappend selected_ports {projection_s_rsp_tag[24]}
set term [$b findBTerm {projection_s_rsp_tag[25]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[25]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 626940 18190 630940
lappend selected_ports {projection_s_rsp_tag[25]}
set term [$b findBTerm {projection_s_rsp_tag[26]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[26]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1500540 18190 1504540
lappend selected_ports {projection_s_rsp_tag[26]}
set term [$b findBTerm {projection_s_rsp_tag[27]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[27]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2201340 18190 2205340
lappend selected_ports {projection_s_rsp_tag[27]}
set term [$b findBTerm {projection_s_rsp_tag[28]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[28]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1423740 18190 1427740
lappend selected_ports {projection_s_rsp_tag[28]}
set term [$b findBTerm {projection_s_rsp_tag[29]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[29]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 665340 18190 669340
lappend selected_ports {projection_s_rsp_tag[29]}
set term [$b findBTerm {projection_s_rsp_tag[2]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 636540 18190 640540
lappend selected_ports {projection_s_rsp_tag[2]}
set term [$b findBTerm {projection_s_rsp_tag[30]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[30]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2153340 18190 2157340
lappend selected_ports {projection_s_rsp_tag[30]}
set term [$b findBTerm {projection_s_rsp_tag[31]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[31]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1174140 18190 1178140
lappend selected_ports {projection_s_rsp_tag[31]}
set term [$b findBTerm {projection_s_rsp_tag[3]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2182140 18190 2186140
lappend selected_ports {projection_s_rsp_tag[3]}
set term [$b findBTerm {projection_s_rsp_tag[4]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2191740 18190 2195740
lappend selected_ports {projection_s_rsp_tag[4]}
set term [$b findBTerm {projection_s_rsp_tag[5]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1452540 18190 1456540
lappend selected_ports {projection_s_rsp_tag[5]}
set term [$b findBTerm {projection_s_rsp_tag[6]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 674940 18190 678940
lappend selected_ports {projection_s_rsp_tag[6]}
set term [$b findBTerm {projection_s_rsp_tag[7]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 655740 18190 659740
lappend selected_ports {projection_s_rsp_tag[7]}
set term [$b findBTerm {projection_s_rsp_tag[8]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1183740 18190 1187740
lappend selected_ports {projection_s_rsp_tag[8]}
set term [$b findBTerm {projection_s_rsp_tag[9]}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_tag[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2268540 18190 2272540
lappend selected_ports {projection_s_rsp_tag[9]}
set term [$b findBTerm {projection_s_rsp_valid}]
if {$term eq "NULL"} {error {Missing native port projection_s_rsp_valid}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1260540 18190 1264540
lappend selected_ports {projection_s_rsp_valid}
set term [$b findBTerm {projection_s_tag[0]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1193340 18190 1197340
lappend selected_ports {projection_s_tag[0]}
set term [$b findBTerm {projection_s_tag[10]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[10]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 406140 18190 410140
lappend selected_ports {projection_s_tag[10]}
set term [$b findBTerm {projection_s_tag[11]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[11]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 425340 18190 429340
lappend selected_ports {projection_s_tag[11]}
set term [$b findBTerm {projection_s_tag[12]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[12]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1241340 18190 1245340
lappend selected_ports {projection_s_tag[12]}
set term [$b findBTerm {projection_s_tag[13]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[13]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 434940 18190 438940
lappend selected_ports {projection_s_tag[13]}
set term [$b findBTerm {projection_s_tag[14]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[14]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1126140 18190 1130140
lappend selected_ports {projection_s_tag[14]}
set term [$b findBTerm {projection_s_tag[15]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[15]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1145340 18190 1149340
lappend selected_ports {projection_s_tag[15]}
set term [$b findBTerm {projection_s_tag[16]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[16]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 473340 18190 477340
lappend selected_ports {projection_s_tag[16]}
set term [$b findBTerm {projection_s_tag[17]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[17]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 444540 18190 448540
lappend selected_ports {projection_s_tag[17]}
set term [$b findBTerm {projection_s_tag[18]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[18]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1289340 18190 1293340
lappend selected_ports {projection_s_tag[18]}
set term [$b findBTerm {projection_s_tag[19]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[19]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1279740 18190 1283740
lappend selected_ports {projection_s_tag[19]}
set term [$b findBTerm {projection_s_tag[1]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 521340 18190 525340
lappend selected_ports {projection_s_tag[1]}
set term [$b findBTerm {projection_s_tag[20]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[20]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 511740 18190 515740
lappend selected_ports {projection_s_tag[20]}
set term [$b findBTerm {projection_s_tag[21]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[21]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1298940 18190 1302940
lappend selected_ports {projection_s_tag[21]}
set term [$b findBTerm {projection_s_tag[22]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[22]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 2220540 18190 2224540
lappend selected_ports {projection_s_tag[22]}
set term [$b findBTerm {projection_s_tag[23]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[23]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 492540 18190 496540
lappend selected_ports {projection_s_tag[23]}
set term [$b findBTerm {projection_s_tag[24]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[24]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 502140 18190 506140
lappend selected_ports {projection_s_tag[24]}
set term [$b findBTerm {projection_s_tag[25]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[25]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 463740 18190 467740
lappend selected_ports {projection_s_tag[25]}
set term [$b findBTerm {projection_s_tag[26]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[26]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 482940 18190 486940
lappend selected_ports {projection_s_tag[26]}
set term [$b findBTerm {projection_s_tag[27]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[27]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1270140 18190 1274140
lappend selected_ports {projection_s_tag[27]}
set term [$b findBTerm {projection_s_tag[28]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[28]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 588540 18190 592540
lappend selected_ports {projection_s_tag[28]}
set term [$b findBTerm {projection_s_tag[29]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[29]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1308540 18190 1312540
lappend selected_ports {projection_s_tag[29]}
set term [$b findBTerm {projection_s_tag[2]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 530940 18190 534940
lappend selected_ports {projection_s_tag[2]}
set term [$b findBTerm {projection_s_tag[30]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[30]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 569340 18190 573340
lappend selected_ports {projection_s_tag[30]}
set term [$b findBTerm {projection_s_tag[31]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[31]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 1231740 18190 1235740
lappend selected_ports {projection_s_tag[31]}
set term [$b findBTerm {projection_s_tag[3]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 550140 18190 554140
lappend selected_ports {projection_s_tag[3]}
set term [$b findBTerm {projection_s_tag[4]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 578940 18190 582940
lappend selected_ports {projection_s_tag[4]}
set term [$b findBTerm {projection_s_tag[5]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 559740 18190 563740
lappend selected_ports {projection_s_tag[5]}
set term [$b findBTerm {projection_s_tag[6]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 540540 18190 544540
lappend selected_ports {projection_s_tag[6]}
set term [$b findBTerm {projection_s_tag[7]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 598140 18190 602140
lappend selected_ports {projection_s_tag[7]}
set term [$b findBTerm {projection_s_tag[8]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 358140 18190 362140
lappend selected_ports {projection_s_tag[8]}
set term [$b findBTerm {projection_s_tag[9]}]
if {$term eq "NULL"} {error {Missing native port projection_s_tag[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 415740 18190 419740
lappend selected_ports {projection_s_tag[9]}
set term [$b findBTerm {projection_s_valid}]
if {$term eq "NULL"} {error {Missing native port projection_s_valid}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 14190 386940 18190 390940
lappend selected_ports {projection_s_valid}
set term [$b findBTerm {rx_addr[0]}]
if {$term eq "NULL"} {error {Missing native port rx_addr[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2531790 109340 2535790 113340
lappend selected_ports {rx_addr[0]}
set term [$b findBTerm {rx_addr[1]}]
if {$term eq "NULL"} {error {Missing native port rx_addr[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2507790 109340 2511790 113340
lappend selected_ports {rx_addr[1]}
set term [$b findBTerm {rx_addr[2]}]
if {$term eq "NULL"} {error {Missing native port rx_addr[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2574990 109340 2578990 113340
lappend selected_ports {rx_addr[2]}
set term [$b findBTerm {rx_addr[3]}]
if {$term eq "NULL"} {error {Missing native port rx_addr[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2531790 92540 2535790 96540
lappend selected_ports {rx_addr[3]}
set term [$b findBTerm {rx_addr[4]}]
if {$term eq "NULL"} {error {Missing native port rx_addr[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2548590 92540 2552590 96540
lappend selected_ports {rx_addr[4]}
set term [$b findBTerm {rx_addr[5]}]
if {$term eq "NULL"} {error {Missing native port rx_addr[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2574990 92540 2578990 96540
lappend selected_ports {rx_addr[5]}
set term [$b findBTerm {rx_addr[6]}]
if {$term eq "NULL"} {error {Missing native port rx_addr[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2598990 109340 2602990 113340
lappend selected_ports {rx_addr[6]}
set term [$b findBTerm {rx_addr[7]}]
if {$term eq "NULL"} {error {Missing native port rx_addr[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2481390 109340 2485390 113340
lappend selected_ports {rx_addr[7]}
set term [$b findBTerm {rx_addr[8]}]
if {$term eq "NULL"} {error {Missing native port rx_addr[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2430990 109340 2434990 113340
lappend selected_ports {rx_addr[8]}
set term [$b findBTerm {rx_addr[9]}]
if {$term eq "NULL"} {error {Missing native port rx_addr[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2531790 75740 2535790 79740
lappend selected_ports {rx_addr[9]}
set term [$b findBTerm {rx_data[0]}]
if {$term eq "NULL"} {error {Missing native port rx_data[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2574990 75740 2578990 79740
lappend selected_ports {rx_data[0]}
set term [$b findBTerm {rx_data[100]}]
if {$term eq "NULL"} {error {Missing native port rx_data[100]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2229390 109340 2233390 113340
lappend selected_ports {rx_data[100]}
set term [$b findBTerm {rx_data[101]}]
if {$term eq "NULL"} {error {Missing native port rx_data[101]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2296590 109340 2300590 113340
lappend selected_ports {rx_data[101]}
set term [$b findBTerm {rx_data[102]}]
if {$term eq "NULL"} {error {Missing native port rx_data[102]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2212590 109340 2216590 113340
lappend selected_ports {rx_data[102]}
set term [$b findBTerm {rx_data[103]}]
if {$term eq "NULL"} {error {Missing native port rx_data[103]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2330190 109340 2334190 113340
lappend selected_ports {rx_data[103]}
set term [$b findBTerm {rx_data[104]}]
if {$term eq "NULL"} {error {Missing native port rx_data[104]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2229390 92540 2233390 96540
lappend selected_ports {rx_data[104]}
set term [$b findBTerm {rx_data[105]}]
if {$term eq "NULL"} {error {Missing native port rx_data[105]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2061390 109340 2065390 113340
lappend selected_ports {rx_data[105]}
set term [$b findBTerm {rx_data[106]}]
if {$term eq "NULL"} {error {Missing native port rx_data[106]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2296590 92540 2300590 96540
lappend selected_ports {rx_data[106]}
set term [$b findBTerm {rx_data[107]}]
if {$term eq "NULL"} {error {Missing native port rx_data[107]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2346990 109340 2350990 113340
lappend selected_ports {rx_data[107]}
set term [$b findBTerm {rx_data[108]}]
if {$term eq "NULL"} {error {Missing native port rx_data[108]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2087790 109340 2091790 113340
lappend selected_ports {rx_data[108]}
set term [$b findBTerm {rx_data[109]}]
if {$term eq "NULL"} {error {Missing native port rx_data[109]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2162190 109340 2166190 113340
lappend selected_ports {rx_data[109]}
set term [$b findBTerm {rx_data[10]}]
if {$term eq "NULL"} {error {Missing native port rx_data[10]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2628590 118940 2632590 122940
lappend selected_ports {rx_data[10]}
set term [$b findBTerm {rx_data[110]}]
if {$term eq "NULL"} {error {Missing native port rx_data[110]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2132590 118940 2136590 122940
lappend selected_ports {rx_data[110]}
set term [$b findBTerm {rx_data[111]}]
if {$term eq "NULL"} {error {Missing native port rx_data[111]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2253390 109340 2257390 113340
lappend selected_ports {rx_data[111]}
set term [$b findBTerm {rx_data[112]}]
if {$term eq "NULL"} {error {Missing native port rx_data[112]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2279790 92540 2283790 96540
lappend selected_ports {rx_data[112]}
set term [$b findBTerm {rx_data[113]}]
if {$term eq "NULL"} {error {Missing native port rx_data[113]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2363790 109340 2367790 113340
lappend selected_ports {rx_data[113]}
set term [$b findBTerm {rx_data[114]}]
if {$term eq "NULL"} {error {Missing native port rx_data[114]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2330190 92540 2334190 96540
lappend selected_ports {rx_data[114]}
set term [$b findBTerm {rx_data[115]}]
if {$term eq "NULL"} {error {Missing native port rx_data[115]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2346990 92540 2350990 96540
lappend selected_ports {rx_data[115]}
set term [$b findBTerm {rx_data[116]}]
if {$term eq "NULL"} {error {Missing native port rx_data[116]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2598990 92540 2602990 96540
lappend selected_ports {rx_data[116]}
set term [$b findBTerm {rx_data[117]}]
if {$term eq "NULL"} {error {Missing native port rx_data[117]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2632590 109340 2636590 113340
lappend selected_ports {rx_data[117]}
set term [$b findBTerm {rx_data[118]}]
if {$term eq "NULL"} {error {Missing native port rx_data[118]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2612590 66940 2616590 70940
lappend selected_ports {rx_data[118]}
set term [$b findBTerm {rx_data[119]}]
if {$term eq "NULL"} {error {Missing native port rx_data[119]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2598990 75740 2602990 79740
lappend selected_ports {rx_data[119]}
set term [$b findBTerm {rx_data[11]}]
if {$term eq "NULL"} {error {Missing native port rx_data[11]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2212590 92540 2216590 96540
lappend selected_ports {rx_data[11]}
set term [$b findBTerm {rx_data[120]}]
if {$term eq "NULL"} {error {Missing native port rx_data[120]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2632590 92540 2636590 96540
lappend selected_ports {rx_data[120]}
set term [$b findBTerm {rx_data[121]}]
if {$term eq "NULL"} {error {Missing native port rx_data[121]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2590190 75740 2594190 79740
lappend selected_ports {rx_data[121]}
set term [$b findBTerm {rx_data[122]}]
if {$term eq "NULL"} {error {Missing native port rx_data[122]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2598990 58940 2602990 62940
lappend selected_ports {rx_data[122]}
set term [$b findBTerm {rx_data[123]}]
if {$term eq "NULL"} {error {Missing native port rx_data[123]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2632590 75740 2636590 79740
lappend selected_ports {rx_data[123]}
set term [$b findBTerm {rx_data[124]}]
if {$term eq "NULL"} {error {Missing native port rx_data[124]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2666190 109340 2670190 113340
lappend selected_ports {rx_data[124]}
set term [$b findBTerm {rx_data[125]}]
if {$term eq "NULL"} {error {Missing native port rx_data[125]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2612590 49340 2616590 53340
lappend selected_ports {rx_data[125]}
set term [$b findBTerm {rx_data[126]}]
if {$term eq "NULL"} {error {Missing native port rx_data[126]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2692590 109340 2696590 113340
lappend selected_ports {rx_data[126]}
set term [$b findBTerm {rx_data[127]}]
if {$term eq "NULL"} {error {Missing native port rx_data[127]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2632590 58940 2636590 62940
lappend selected_ports {rx_data[127]}
set term [$b findBTerm {rx_data[12]}]
if {$term eq "NULL"} {error {Missing native port rx_data[12]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2548590 75740 2552590 79740
lappend selected_ports {rx_data[12]}
set term [$b findBTerm {rx_data[13]}]
if {$term eq "NULL"} {error {Missing native port rx_data[13]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2128590 109340 2132590 113340
lappend selected_ports {rx_data[13]}
set term [$b findBTerm {rx_data[14]}]
if {$term eq "NULL"} {error {Missing native port rx_data[14]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2574990 58940 2578990 62940
lappend selected_ports {rx_data[14]}
set term [$b findBTerm {rx_data[15]}]
if {$term eq "NULL"} {error {Missing native port rx_data[15]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2116590 92540 2120590 96540
lappend selected_ports {rx_data[15]}
set term [$b findBTerm {rx_data[16]}]
if {$term eq "NULL"} {error {Missing native port rx_data[16]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2253390 92540 2257390 96540
lappend selected_ports {rx_data[16]}
set term [$b findBTerm {rx_data[17]}]
if {$term eq "NULL"} {error {Missing native port rx_data[17]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2186190 92540 2190190 96540
lappend selected_ports {rx_data[17]}
set term [$b findBTerm {rx_data[18]}]
if {$term eq "NULL"} {error {Missing native port rx_data[18]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2212590 75740 2216590 79740
lappend selected_ports {rx_data[18]}
set term [$b findBTerm {rx_data[19]}]
if {$term eq "NULL"} {error {Missing native port rx_data[19]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2363790 92540 2367790 96540
lappend selected_ports {rx_data[19]}
set term [$b findBTerm {rx_data[1]}]
if {$term eq "NULL"} {error {Missing native port rx_data[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2397390 109340 2401390 113340
lappend selected_ports {rx_data[1]}
set term [$b findBTerm {rx_data[20]}]
if {$term eq "NULL"} {error {Missing native port rx_data[20]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2346990 75740 2350990 79740
lappend selected_ports {rx_data[20]}
set term [$b findBTerm {rx_data[21]}]
if {$term eq "NULL"} {error {Missing native port rx_data[21]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2279790 75740 2283790 79740
lappend selected_ports {rx_data[21]}
set term [$b findBTerm {rx_data[22]}]
if {$term eq "NULL"} {error {Missing native port rx_data[22]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2061390 92540 2065390 96540
lappend selected_ports {rx_data[22]}
set term [$b findBTerm {rx_data[23]}]
if {$term eq "NULL"} {error {Missing native port rx_data[23]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2666190 92540 2670190 96540
lappend selected_ports {rx_data[23]}
set term [$b findBTerm {rx_data[24]}]
if {$term eq "NULL"} {error {Missing native port rx_data[24]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2128590 92540 2132590 96540
lappend selected_ports {rx_data[24]}
set term [$b findBTerm {rx_data[25]}]
if {$term eq "NULL"} {error {Missing native port rx_data[25]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2632590 42140 2636590 46140
lappend selected_ports {rx_data[25]}
set term [$b findBTerm {rx_data[26]}]
if {$term eq "NULL"} {error {Missing native port rx_data[26]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2330190 75740 2334190 79740
lappend selected_ports {rx_data[26]}
set term [$b findBTerm {rx_data[27]}]
if {$term eq "NULL"} {error {Missing native port rx_data[27]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2296590 75740 2300590 79740
lappend selected_ports {rx_data[27]}
set term [$b findBTerm {rx_data[28]}]
if {$term eq "NULL"} {error {Missing native port rx_data[28]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2330190 58940 2334190 62940
lappend selected_ports {rx_data[28]}
set term [$b findBTerm {rx_data[29]}]
if {$term eq "NULL"} {error {Missing native port rx_data[29]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2162190 92540 2166190 96540
lappend selected_ports {rx_data[29]}
set term [$b findBTerm {rx_data[2]}]
if {$term eq "NULL"} {error {Missing native port rx_data[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2363790 75740 2367790 79740
lappend selected_ports {rx_data[2]}
set term [$b findBTerm {rx_data[30]}]
if {$term eq "NULL"} {error {Missing native port rx_data[30]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2186190 75740 2190190 79740
lappend selected_ports {rx_data[30]}
set term [$b findBTerm {rx_data[31]}]
if {$term eq "NULL"} {error {Missing native port rx_data[31]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2148590 101340 2152590 105340
lappend selected_ports {rx_data[31]}
set term [$b findBTerm {rx_data[32]}]
if {$term eq "NULL"} {error {Missing native port rx_data[32]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2253390 75740 2257390 79740
lappend selected_ports {rx_data[32]}
set term [$b findBTerm {rx_data[33]}]
if {$term eq "NULL"} {error {Missing native port rx_data[33]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2229390 75740 2233390 79740
lappend selected_ports {rx_data[33]}
set term [$b findBTerm {rx_data[34]}]
if {$term eq "NULL"} {error {Missing native port rx_data[34]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2296590 58940 2300590 62940
lappend selected_ports {rx_data[34]}
set term [$b findBTerm {rx_data[35]}]
if {$term eq "NULL"} {error {Missing native port rx_data[35]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2162190 75740 2166190 79740
lappend selected_ports {rx_data[35]}
set term [$b findBTerm {rx_data[36]}]
if {$term eq "NULL"} {error {Missing native port rx_data[36]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2186190 58940 2190190 62940
lappend selected_ports {rx_data[36]}
set term [$b findBTerm {rx_data[37]}]
if {$term eq "NULL"} {error {Missing native port rx_data[37]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2087790 92540 2091790 96540
lappend selected_ports {rx_data[37]}
set term [$b findBTerm {rx_data[38]}]
if {$term eq "NULL"} {error {Missing native port rx_data[38]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2253390 58940 2257390 62940
lappend selected_ports {rx_data[38]}
set term [$b findBTerm {rx_data[39]}]
if {$term eq "NULL"} {error {Missing native port rx_data[39]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2128590 75740 2132590 79740
lappend selected_ports {rx_data[39]}
set term [$b findBTerm {rx_data[3]}]
if {$term eq "NULL"} {error {Missing native port rx_data[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2094990 75740 2098990 79740
lappend selected_ports {rx_data[3]}
set term [$b findBTerm {rx_data[40]}]
if {$term eq "NULL"} {error {Missing native port rx_data[40]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2229390 58940 2233390 62940
lappend selected_ports {rx_data[40]}
set term [$b findBTerm {rx_data[41]}]
if {$term eq "NULL"} {error {Missing native port rx_data[41]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2212590 58940 2216590 62940
lappend selected_ports {rx_data[41]}
set term [$b findBTerm {rx_data[42]}]
if {$term eq "NULL"} {error {Missing native port rx_data[42]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2279790 58940 2283790 62940
lappend selected_ports {rx_data[42]}
set term [$b findBTerm {rx_data[43]}]
if {$term eq "NULL"} {error {Missing native port rx_data[43]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2128590 58940 2132590 62940
lappend selected_ports {rx_data[43]}
set term [$b findBTerm {rx_data[44]}]
if {$term eq "NULL"} {error {Missing native port rx_data[44]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2027790 109340 2031790 113340
lappend selected_ports {rx_data[44]}
set term [$b findBTerm {rx_data[45]}]
if {$term eq "NULL"} {error {Missing native port rx_data[45]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2162190 58940 2166190 62940
lappend selected_ports {rx_data[45]}
set term [$b findBTerm {rx_data[46]}]
if {$term eq "NULL"} {error {Missing native port rx_data[46]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2346990 58940 2350990 62940
lappend selected_ports {rx_data[46]}
set term [$b findBTerm {rx_data[47]}]
if {$term eq "NULL"} {error {Missing native port rx_data[47]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2119790 58940 2123790 62940
lappend selected_ports {rx_data[47]}
set term [$b findBTerm {rx_data[48]}]
if {$term eq "NULL"} {error {Missing native port rx_data[48]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2162190 42140 2166190 46140
lappend selected_ports {rx_data[48]}
set term [$b findBTerm {rx_data[49]}]
if {$term eq "NULL"} {error {Missing native port rx_data[49]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2145390 26140 2149390 30140
lappend selected_ports {rx_data[49]}
set term [$b findBTerm {rx_data[4]}]
if {$term eq "NULL"} {error {Missing native port rx_data[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2068590 75740 2072590 79740
lappend selected_ports {rx_data[4]}
set term [$b findBTerm {rx_data[50]}]
if {$term eq "NULL"} {error {Missing native port rx_data[50]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2186190 42140 2190190 46140
lappend selected_ports {rx_data[50]}
set term [$b findBTerm {rx_data[51]}]
if {$term eq "NULL"} {error {Missing native port rx_data[51]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2363790 58940 2367790 62940
lappend selected_ports {rx_data[51]}
set term [$b findBTerm {rx_data[52]}]
if {$term eq "NULL"} {error {Missing native port rx_data[52]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2229390 42140 2233390 46140
lappend selected_ports {rx_data[52]}
set term [$b findBTerm {rx_data[53]}]
if {$term eq "NULL"} {error {Missing native port rx_data[53]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2272590 42140 2276590 46140
lappend selected_ports {rx_data[53]}
set term [$b findBTerm {rx_data[54]}]
if {$term eq "NULL"} {error {Missing native port rx_data[54]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2010990 109340 2014990 113340
lappend selected_ports {rx_data[54]}
set term [$b findBTerm {rx_data[55]}]
if {$term eq "NULL"} {error {Missing native port rx_data[55]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 2212590 42140 2216590 46140
lappend selected_ports {rx_data[55]}
set term [$b findBTerm {rx_data[56]}]
if {$term eq "NULL"} {error {Missing native port rx_data[56]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1624590 109340 1628590 113340
lappend selected_ports {rx_data[56]}
set term [$b findBTerm {rx_data[57]}]
if {$term eq "NULL"} {error {Missing native port rx_data[57]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1994190 109340 1998190 113340
lappend selected_ports {rx_data[57]}
set term [$b findBTerm {rx_data[58]}]
if {$term eq "NULL"} {error {Missing native port rx_data[58]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1970190 109340 1974190 113340
lappend selected_ports {rx_data[58]}
set term [$b findBTerm {rx_data[59]}]
if {$term eq "NULL"} {error {Missing native port rx_data[59]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1994190 92540 1998190 96540
lappend selected_ports {rx_data[59]}
set term [$b findBTerm {rx_data[5]}]
if {$term eq "NULL"} {error {Missing native port rx_data[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1943790 109340 1947790 113340
lappend selected_ports {rx_data[5]}
set term [$b findBTerm {rx_data[60]}]
if {$term eq "NULL"} {error {Missing native port rx_data[60]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1970190 92540 1974190 96540
lappend selected_ports {rx_data[60]}
set term [$b findBTerm {rx_data[61]}]
if {$term eq "NULL"} {error {Missing native port rx_data[61]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1926990 109340 1930990 113340
lappend selected_ports {rx_data[61]}
set term [$b findBTerm {rx_data[62]}]
if {$term eq "NULL"} {error {Missing native port rx_data[62]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1943790 92540 1947790 96540
lappend selected_ports {rx_data[62]}
set term [$b findBTerm {rx_data[63]}]
if {$term eq "NULL"} {error {Missing native port rx_data[63]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1970190 75740 1974190 79740
lappend selected_ports {rx_data[63]}
set term [$b findBTerm {rx_data[64]}]
if {$term eq "NULL"} {error {Missing native port rx_data[64]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1943790 75740 1947790 79740
lappend selected_ports {rx_data[64]}
set term [$b findBTerm {rx_data[65]}]
if {$term eq "NULL"} {error {Missing native port rx_data[65]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1926990 92540 1930990 96540
lappend selected_ports {rx_data[65]}
set term [$b findBTerm {rx_data[66]}]
if {$term eq "NULL"} {error {Missing native port rx_data[66]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1970190 58940 1974190 62940
lappend selected_ports {rx_data[66]}
set term [$b findBTerm {rx_data[67]}]
if {$term eq "NULL"} {error {Missing native port rx_data[67]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1926990 75740 1930990 79740
lappend selected_ports {rx_data[67]}
set term [$b findBTerm {rx_data[68]}]
if {$term eq "NULL"} {error {Missing native port rx_data[68]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1893390 109340 1897390 113340
lappend selected_ports {rx_data[68]}
set term [$b findBTerm {rx_data[69]}]
if {$term eq "NULL"} {error {Missing native port rx_data[69]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1943790 58940 1947790 62940
lappend selected_ports {rx_data[69]}
set term [$b findBTerm {rx_data[6]}]
if {$term eq "NULL"} {error {Missing native port rx_data[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1876590 109340 1880590 113340
lappend selected_ports {rx_data[6]}
set term [$b findBTerm {rx_data[70]}]
if {$term eq "NULL"} {error {Missing native port rx_data[70]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1926990 58940 1930990 62940
lappend selected_ports {rx_data[70]}
set term [$b findBTerm {rx_data[71]}]
if {$term eq "NULL"} {error {Missing native port rx_data[71]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1893390 92540 1897390 96540
lappend selected_ports {rx_data[71]}
set term [$b findBTerm {rx_data[72]}]
if {$term eq "NULL"} {error {Missing native port rx_data[72]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1859790 109340 1863790 113340
lappend selected_ports {rx_data[72]}
set term [$b findBTerm {rx_data[73]}]
if {$term eq "NULL"} {error {Missing native port rx_data[73]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1876590 92540 1880590 96540
lappend selected_ports {rx_data[73]}
set term [$b findBTerm {rx_data[74]}]
if {$term eq "NULL"} {error {Missing native port rx_data[74]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1893390 75740 1897390 79740
lappend selected_ports {rx_data[74]}
set term [$b findBTerm {rx_data[75]}]
if {$term eq "NULL"} {error {Missing native port rx_data[75]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1926990 42140 1930990 46140
lappend selected_ports {rx_data[75]}
set term [$b findBTerm {rx_data[76]}]
if {$term eq "NULL"} {error {Missing native port rx_data[76]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1876590 75740 1880590 79740
lappend selected_ports {rx_data[76]}
set term [$b findBTerm {rx_data[77]}]
if {$term eq "NULL"} {error {Missing native port rx_data[77]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1859790 92540 1863790 96540
lappend selected_ports {rx_data[77]}
set term [$b findBTerm {rx_data[78]}]
if {$term eq "NULL"} {error {Missing native port rx_data[78]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1893390 58940 1897390 62940
lappend selected_ports {rx_data[78]}
set term [$b findBTerm {rx_data[79]}]
if {$term eq "NULL"} {error {Missing native port rx_data[79]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1859790 75740 1863790 79740
lappend selected_ports {rx_data[79]}
set term [$b findBTerm {rx_data[7]}]
if {$term eq "NULL"} {error {Missing native port rx_data[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1876590 58940 1880590 62940
lappend selected_ports {rx_data[7]}
set term [$b findBTerm {rx_data[80]}]
if {$term eq "NULL"} {error {Missing native port rx_data[80]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1826190 109340 1830190 113340
lappend selected_ports {rx_data[80]}
set term [$b findBTerm {rx_data[81]}]
if {$term eq "NULL"} {error {Missing native port rx_data[81]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1893390 42140 1897390 46140
lappend selected_ports {rx_data[81]}
set term [$b findBTerm {rx_data[82]}]
if {$term eq "NULL"} {error {Missing native port rx_data[82]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1809390 109340 1813390 113340
lappend selected_ports {rx_data[82]}
set term [$b findBTerm {rx_data[83]}]
if {$term eq "NULL"} {error {Missing native port rx_data[83]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1859790 58940 1863790 62940
lappend selected_ports {rx_data[83]}
set term [$b findBTerm {rx_data[84]}]
if {$term eq "NULL"} {error {Missing native port rx_data[84]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1876590 42140 1880590 46140
lappend selected_ports {rx_data[84]}
set term [$b findBTerm {rx_data[85]}]
if {$term eq "NULL"} {error {Missing native port rx_data[85]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1826190 92540 1830190 96540
lappend selected_ports {rx_data[85]}
set term [$b findBTerm {rx_data[86]}]
if {$term eq "NULL"} {error {Missing native port rx_data[86]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1792590 109340 1796590 113340
lappend selected_ports {rx_data[86]}
set term [$b findBTerm {rx_data[87]}]
if {$term eq "NULL"} {error {Missing native port rx_data[87]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1859790 42140 1863790 46140
lappend selected_ports {rx_data[87]}
set term [$b findBTerm {rx_data[88]}]
if {$term eq "NULL"} {error {Missing native port rx_data[88]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1809390 92540 1813390 96540
lappend selected_ports {rx_data[88]}
set term [$b findBTerm {rx_data[89]}]
if {$term eq "NULL"} {error {Missing native port rx_data[89]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1826190 75740 1830190 79740
lappend selected_ports {rx_data[89]}
set term [$b findBTerm {rx_data[8]}]
if {$term eq "NULL"} {error {Missing native port rx_data[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1876590 25340 1880590 29340
lappend selected_ports {rx_data[8]}
set term [$b findBTerm {rx_data[90]}]
if {$term eq "NULL"} {error {Missing native port rx_data[90]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1809390 75740 1813390 79740
lappend selected_ports {rx_data[90]}
set term [$b findBTerm {rx_data[91]}]
if {$term eq "NULL"} {error {Missing native port rx_data[91]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1792590 92540 1796590 96540
lappend selected_ports {rx_data[91]}
set term [$b findBTerm {rx_data[92]}]
if {$term eq "NULL"} {error {Missing native port rx_data[92]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1826190 58940 1830190 62940
lappend selected_ports {rx_data[92]}
set term [$b findBTerm {rx_data[93]}]
if {$term eq "NULL"} {error {Missing native port rx_data[93]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1758990 109340 1762990 113340
lappend selected_ports {rx_data[93]}
set term [$b findBTerm {rx_data[94]}]
if {$term eq "NULL"} {error {Missing native port rx_data[94]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1859790 25340 1863790 29340
lappend selected_ports {rx_data[94]}
set term [$b findBTerm {rx_data[95]}]
if {$term eq "NULL"} {error {Missing native port rx_data[95]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1792590 75740 1796590 79740
lappend selected_ports {rx_data[95]}
set term [$b findBTerm {rx_data[96]}]
if {$term eq "NULL"} {error {Missing native port rx_data[96]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1809390 58940 1813390 62940
lappend selected_ports {rx_data[96]}
set term [$b findBTerm {rx_data[97]}]
if {$term eq "NULL"} {error {Missing native port rx_data[97]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1826190 42140 1830190 46140
lappend selected_ports {rx_data[97]}
set term [$b findBTerm {rx_data[98]}]
if {$term eq "NULL"} {error {Missing native port rx_data[98]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1809390 42140 1813390 46140
lappend selected_ports {rx_data[98]}
set term [$b findBTerm {rx_data[99]}]
if {$term eq "NULL"} {error {Missing native port rx_data[99]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1792590 58940 1796590 62940
lappend selected_ports {rx_data[99]}
set term [$b findBTerm {rx_data[9]}]
if {$term eq "NULL"} {error {Missing native port rx_data[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1826190 25340 1830190 29340
lappend selected_ports {rx_data[9]}
set term [$b findBTerm {rx_ready}]
if {$term eq "NULL"} {error {Missing native port rx_ready}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1742190 109340 1746190 113340
lappend selected_ports {rx_ready}
set term [$b findBTerm {rx_reserved}]
if {$term eq "NULL"} {error {Missing native port rx_reserved}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 5085390 613340 5089390 617340
lappend selected_ports {rx_reserved}
set term [$b findBTerm {rx_reserved_addr[0]}]
if {$term eq "NULL"} {error {Missing native port rx_reserved_addr[0]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 5085390 260540 5089390 264540
lappend selected_ports {rx_reserved_addr[0]}
set term [$b findBTerm {rx_reserved_addr[1]}]
if {$term eq "NULL"} {error {Missing native port rx_reserved_addr[1]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 5085390 663740 5089390 667740
lappend selected_ports {rx_reserved_addr[1]}
set term [$b findBTerm {rx_reserved_addr[2]}]
if {$term eq "NULL"} {error {Missing native port rx_reserved_addr[2]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 5085390 378140 5089390 382140
lappend selected_ports {rx_reserved_addr[2]}
set term [$b findBTerm {rx_reserved_addr[3]}]
if {$term eq "NULL"} {error {Missing native port rx_reserved_addr[3]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 5085390 411740 5089390 415740
lappend selected_ports {rx_reserved_addr[3]}
set term [$b findBTerm {rx_reserved_addr[4]}]
if {$term eq "NULL"} {error {Missing native port rx_reserved_addr[4]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 5085390 680540 5089390 684540
lappend selected_ports {rx_reserved_addr[4]}
set term [$b findBTerm {rx_reserved_addr[5]}]
if {$term eq "NULL"} {error {Missing native port rx_reserved_addr[5]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 5085390 579740 5089390 583740
lappend selected_ports {rx_reserved_addr[5]}
set term [$b findBTerm {rx_reserved_addr[6]}]
if {$term eq "NULL"} {error {Missing native port rx_reserved_addr[6]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 5085390 361340 5089390 365340
lappend selected_ports {rx_reserved_addr[6]}
set term [$b findBTerm {rx_reserved_addr[7]}]
if {$term eq "NULL"} {error {Missing native port rx_reserved_addr[7]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 5085390 596540 5089390 600540
lappend selected_ports {rx_reserved_addr[7]}
set term [$b findBTerm {rx_reserved_addr[8]}]
if {$term eq "NULL"} {error {Missing native port rx_reserved_addr[8]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 5085390 394940 5089390 398940
lappend selected_ports {rx_reserved_addr[8]}
set term [$b findBTerm {rx_reserved_addr[9]}]
if {$term eq "NULL"} {error {Missing native port rx_reserved_addr[9]}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 5085390 294140 5089390 298140
lappend selected_ports {rx_reserved_addr[9]}
set term [$b findBTerm {rx_stored}]
if {$term eq "NULL"} {error {Missing native port rx_stored}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 5085390 529340 5089390 533340
lappend selected_ports {rx_stored}
set term [$b findBTerm {rx_stored_ready}]
if {$term eq "NULL"} {error {Missing native port rx_stored_ready}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 5102190 411740 5106190 415740
lappend selected_ports {rx_stored_ready}
set term [$b findBTerm {rx_valid}]
if {$term eq "NULL"} {error {Missing native port rx_valid}}
foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}
set pin [odb::dbBPin_create $term]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1758990 92540 1762990 96540
lappend selected_ports {rx_valid}
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
