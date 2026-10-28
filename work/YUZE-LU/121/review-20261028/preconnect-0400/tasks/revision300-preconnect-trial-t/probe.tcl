set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261028-249/tasks/revision300-final-source-t/flow/results/nangate45/bv1_transaction6k/base/6_final.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set via [$tech findVia via9_0]
if {$via eq "NULL"} {error "Native via9 missing"}
if {[$block findNet bv1_p3_probe_0] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_0]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 812940
odb::dbWireEncoder_addPoint $enc 2000190 812940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 812940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 812940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_0_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 810940 82190 814940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 812940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 812940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_0_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 810940 2002190 814940
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_1] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_1]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 835340
odb::dbWireEncoder_addPoint $enc 2000190 835340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 835340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 835340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_1_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 833340 82190 837340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 835340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 835340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_1_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 833340 2002190 837340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_2] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_2]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 851340
odb::dbWireEncoder_addPoint $enc 2000190 851340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 851340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 851340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_2_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 849340 82190 853340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 851340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 851340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_2_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 849340 2002190 853340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_3] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_3]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 876940
odb::dbWireEncoder_addPoint $enc 2000190 876940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 876940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 876940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_3_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 874940 82190 878940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 876940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 876940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_3_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 874940 2002190 878940
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_4] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_4]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 905740
odb::dbWireEncoder_addPoint $enc 2000190 905740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 905740
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 905740
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_4_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 903740 82190 907740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 905740
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 905740
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_4_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 903740 2002190 907740
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_5] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_5]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 931340
odb::dbWireEncoder_addPoint $enc 2000190 931340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 931340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 931340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_5_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 929340 82190 933340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 931340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 931340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_5_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 929340 2002190 933340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_6] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_6]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 966540
odb::dbWireEncoder_addPoint $enc 2000190 966540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 966540
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 966540
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_6_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 964540 82190 968540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 966540
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 966540
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_6_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 964540 2002190 968540
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_7] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_7]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 988940
odb::dbWireEncoder_addPoint $enc 2000190 988940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 988940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 988940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_7_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 986940 82190 990940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 988940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 988940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_7_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 986940 2002190 990940
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_8] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_8]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1011340
odb::dbWireEncoder_addPoint $enc 2000190 1011340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1011340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1011340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_8_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 1009340 82190 1013340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1011340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1011340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_8_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 1009340 2002190 1013340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_9] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_9]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1027340
odb::dbWireEncoder_addPoint $enc 2000190 1027340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1027340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1027340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_9_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 1025340 82190 1029340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1027340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1027340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_9_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 1025340 2002190 1029340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_10] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_10]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1065740
odb::dbWireEncoder_addPoint $enc 2000190 1065740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1065740
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1065740
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_10_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 1063740 82190 1067740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1065740
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1065740
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_10_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 1063740 2002190 1067740
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_11] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_11]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1091340
odb::dbWireEncoder_addPoint $enc 2000190 1091340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1091340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1091340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_11_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 1089340 82190 1093340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1091340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1091340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_11_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 1089340 2002190 1093340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_12] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_12]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1107340
odb::dbWireEncoder_addPoint $enc 2000190 1107340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1107340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1107340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_12_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 1105340 82190 1109340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1107340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1107340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_12_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 1105340 2002190 1109340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_13] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_13]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1116940
odb::dbWireEncoder_addPoint $enc 2000190 1116940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1116940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1116940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_13_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 1114940 82190 1118940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1116940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1116940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_13_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 1114940 2002190 1118940
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_14] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_14]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1129740
odb::dbWireEncoder_addPoint $enc 2000190 1129740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1129740
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1129740
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_14_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 1127740 82190 1131740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1129740
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1129740
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_14_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 1127740 2002190 1131740
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_15] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_15]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1171340
odb::dbWireEncoder_addPoint $enc 2000190 1171340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1171340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 1171340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_15_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 1169340 82190 1173340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1171340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 2000190 1171340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_15_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1998190 1169340 2002190 1173340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db probe.odb
write_def probe.def
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-282/tasks/revision300-preconnect-trial-t/probe-geometry.tcl}
bvgeom::export probe-geometry.tsv
drt::check_drc_cmd probe-native-drc.rpt 0 0 0 0 native_whole_drc
