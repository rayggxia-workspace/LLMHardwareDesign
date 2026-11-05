read_lef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-148/technology/research12.tech.lef}
set db [ord::get_db]
set chip [odb::dbChip_create $db [$db getTech]]
set block [odb::dbBlock_create $chip search_probe]
$block setDefUnits 2000
set die [odb::new_Rect 0 0 384000 384000]
$block setDieArea $die
set layer [[$db getTech] findLayer metal11]
set_thread_count 16
set net [odb::dbNet_create $block bus_0]
set port [odb::dbBTerm_create $net bus_0_p0]
$port setSigType SIGNAL
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 62190 62140 66190 66140
set port [odb::dbBTerm_create $net bus_0_p1]
$port setSigType SIGNAL
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 302190 270140 306190 274140
set net [odb::dbNet_create $block bus_1]
set port [odb::dbBTerm_create $net bus_1_p0]
$port setSigType SIGNAL
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 62190 78140 66190 82140
set port [odb::dbBTerm_create $net bus_1_p1]
$port setSigType SIGNAL
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 302190 254140 306190 258140
set net [odb::dbNet_create $block bus_2]
set port [odb::dbBTerm_create $net bus_2_p0]
$port setSigType SIGNAL
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 62190 94140 66190 98140
set port [odb::dbBTerm_create $net bus_2_p1]
$port setSigType SIGNAL
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 302190 238140 306190 242140
set net [odb::dbNet_create $block bus_3]
set port [odb::dbBTerm_create $net bus_3_p0]
$port setSigType SIGNAL
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 62190 110140 66190 114140
set port [odb::dbBTerm_create $net bus_3_p1]
$port setSigType SIGNAL
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 302190 222140 306190 226140
set net [odb::dbNet_create $block bus_4]
set port [odb::dbBTerm_create $net bus_4_p0]
$port setSigType SIGNAL
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 62190 126140 66190 130140
set port [odb::dbBTerm_create $net bus_4_p1]
$port setSigType SIGNAL
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 302190 206140 306190 210140
set net [odb::dbNet_create $block bus_5]
set port [odb::dbBTerm_create $net bus_5_p0]
$port setSigType SIGNAL
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 62190 142140 66190 146140
set port [odb::dbBTerm_create $net bus_5_p1]
$port setSigType SIGNAL
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 302190 190140 306190 194140
set net [odb::dbNet_create $block bus_6]
set port [odb::dbBTerm_create $net bus_6_p0]
$port setSigType SIGNAL
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 62190 158140 66190 162140
set port [odb::dbBTerm_create $net bus_6_p1]
$port setSigType SIGNAL
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 302190 174140 306190 178140
set net [odb::dbNet_create $block bus_7]
set port [odb::dbBTerm_create $net bus_7_p0]
$port setSigType SIGNAL
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 62190 174140 66190 178140
set port [odb::dbBTerm_create $net bus_7_p1]
$port setSigType SIGNAL
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 302190 158140 306190 162140
set net [odb::dbNet_create $block bus_8]
set port [odb::dbBTerm_create $net bus_8_p0]
$port setSigType SIGNAL
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 62190 190140 66190 194140
set port [odb::dbBTerm_create $net bus_8_p1]
$port setSigType SIGNAL
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 302190 142140 306190 146140
set net [odb::dbNet_create $block bus_9]
set port [odb::dbBTerm_create $net bus_9_p0]
$port setSigType SIGNAL
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 62190 206140 66190 210140
set port [odb::dbBTerm_create $net bus_9_p1]
$port setSigType SIGNAL
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 302190 126140 306190 130140
set net [odb::dbNet_create $block bus_10]
set port [odb::dbBTerm_create $net bus_10_p0]
$port setSigType SIGNAL
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 62190 222140 66190 226140
set port [odb::dbBTerm_create $net bus_10_p1]
$port setSigType SIGNAL
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 302190 110140 306190 114140
set net [odb::dbNet_create $block bus_11]
set port [odb::dbBTerm_create $net bus_11_p0]
$port setSigType SIGNAL
$port setIoType INPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 62190 238140 66190 242140
set port [odb::dbBTerm_create $net bus_11_p1]
$port setSigType SIGNAL
$port setIoType OUTPUT
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin $layer 302190 94140 306190 98140
make_tracks
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-148/technology/new_tracks.tcl}
set_routing_layers -signal metal11-metal12 -clock metal11-metal12
help global_route
help detailed_route
write_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-148/case-0/before.odb}
global_route -guide_file {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-148/case-0/route.guide} -verbose
detailed_route -output_drc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-148/case-0/drc.rpt} -output_maze {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-148/case-0/maze.log} -via_in_pin_bottom_layer metal11 -via_in_pin_top_layer metal11 -verbose 1
write_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-148/case-0/routed.odb}
write_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-148/case-0/routed.def}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/source-148/project/experiments/block_v1/odb_geometry.tcl}
bvgeom::export {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-148/case-0/geometry.tsv}
