set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-258/tasks/revision300-final-source-m/flow/results/nangate45/bv1_block_v1_m/base/6_final.odb}
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
odb::dbWireEncoder_addPoint $enc 80190 531340
odb::dbWireEncoder_addPoint $enc 1398590 531340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 531340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 531340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_0_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 529340 82190 533340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 531340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 531340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_0_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 529340 1400590 533340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_1] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_1]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 547340
odb::dbWireEncoder_addPoint $enc 1398590 547340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 547340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 547340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_1_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 545340 82190 549340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 547340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 547340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_1_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 545340 1400590 549340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_2] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_2]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 595340
odb::dbWireEncoder_addPoint $enc 1398590 595340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 595340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 595340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_2_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 593340 82190 597340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 595340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 595340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_2_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 593340 1400590 597340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_3] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_3]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 611340
odb::dbWireEncoder_addPoint $enc 1398590 611340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 611340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 611340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_3_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 609340 82190 613340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 611340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 611340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_3_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 609340 1400590 613340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_4] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_4]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 627340
odb::dbWireEncoder_addPoint $enc 1398590 627340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 627340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 627340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_4_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 625340 82190 629340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 627340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 627340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_4_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 625340 1400590 629340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_5] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_5]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 636940
odb::dbWireEncoder_addPoint $enc 1398590 636940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 636940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 636940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_5_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 634940 82190 638940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 636940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 636940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_5_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 634940 1400590 638940
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_6] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_6]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 691340
odb::dbWireEncoder_addPoint $enc 1398590 691340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 691340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 691340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_6_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 689340 82190 693340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 691340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 691340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_6_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 689340 1400590 693340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_7] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_7]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 716940
odb::dbWireEncoder_addPoint $enc 1398590 716940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 716940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 716940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_7_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 714940 82190 718940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 716940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 716940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_7_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 714940 1400590 718940
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_8] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_8]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 729740
odb::dbWireEncoder_addPoint $enc 1398590 729740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 729740
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 729740
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_8_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 727740 82190 731740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 729740
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 729740
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_8_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 727740 1400590 731740
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_9] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_9]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 755340
odb::dbWireEncoder_addPoint $enc 1398590 755340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 755340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 755340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_9_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 753340 82190 757340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 755340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 755340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_9_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 753340 1400590 757340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_10] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_10]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 774540
odb::dbWireEncoder_addPoint $enc 1398590 774540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 774540
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 774540
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_10_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 772540 82190 776540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 774540
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 774540
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_10_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 772540 1400590 776540
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_11] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_11]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 787340
odb::dbWireEncoder_addPoint $enc 1398590 787340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 787340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 787340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_11_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 785340 82190 789340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 787340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 787340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_11_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 785340 1400590 789340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_12] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_12]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 812940
odb::dbWireEncoder_addPoint $enc 1398590 812940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 812940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 812940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_12_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 810940 82190 814940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 812940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 812940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_12_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 810940 1400590 814940
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_13] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_13]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 851340
odb::dbWireEncoder_addPoint $enc 1398590 851340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 851340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 851340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_13_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 849340 82190 853340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 851340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 851340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_13_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 849340 1400590 853340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_14] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_14]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 867340
odb::dbWireEncoder_addPoint $enc 1398590 867340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 867340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 867340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_14_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 865340 82190 869340
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 867340
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 867340
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_14_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 865340 1400590 869340
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
if {[$block findNet bv1_p3_probe_15] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block bv1_p3_probe_15]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 876940
odb::dbWireEncoder_addPoint $enc 1398590 876940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 876940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 80190 876940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_15_left]
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 78190 874940 82190 878940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 876940
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc 1398590 876940
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net bv1_p3_probe_15_right]
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] 1396590 874940 1400590 878940
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db probe.odb
write_def probe.def
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-282/tasks/revision300-preconnect-trial-m/probe-geometry.tcl}
bvgeom::export probe-geometry.tsv
drt::check_drc_cmd probe-native-drc.rpt 0 0 0 0 native_whole_drc
