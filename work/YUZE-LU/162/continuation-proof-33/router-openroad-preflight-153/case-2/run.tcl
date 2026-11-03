read_lef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-153/technology/research12.tech.lef}
read_lef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-153/search-landing-markers.lef}
set db [ord::get_db]
set chip [odb::dbChip_create $db [$db getTech]]
set block [odb::dbBlock_create $chip search_probe]
$block setDefUnits 2000
set die [odb::new_Rect 0 0 384000 384000]
$block setDieArea $die
set layer [[$db getTech] findLayer metal11]
set_thread_count 16
set net [odb::dbNet_create $block bus_0]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_0_p0]
$inst setLocation 62190 62140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_0_p1]
$inst setLocation 302190 302140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_0_p2]
$inst setLocation 62190 318140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_1]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_1_p0]
$inst setLocation 78190 62140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_1_p1]
$inst setLocation 286190 302140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_1_p2]
$inst setLocation 78190 318140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_2]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_2_p0]
$inst setLocation 94190 62140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_2_p1]
$inst setLocation 270190 302140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_2_p2]
$inst setLocation 94190 318140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_3]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_3_p0]
$inst setLocation 110190 62140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_3_p1]
$inst setLocation 254190 302140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_3_p2]
$inst setLocation 110190 318140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_4]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_4_p0]
$inst setLocation 126190 62140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_4_p1]
$inst setLocation 238190 302140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_4_p2]
$inst setLocation 126190 318140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_5]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_5_p0]
$inst setLocation 142190 62140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_5_p1]
$inst setLocation 222190 302140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_5_p2]
$inst setLocation 142190 318140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_6]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_6_p0]
$inst setLocation 158190 62140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_6_p1]
$inst setLocation 206190 302140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_6_p2]
$inst setLocation 158190 318140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_7]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_7_p0]
$inst setLocation 174190 62140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_7_p1]
$inst setLocation 190190 302140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_7_p2]
$inst setLocation 174190 318140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_8]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_8_p0]
$inst setLocation 190190 62140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_8_p1]
$inst setLocation 174190 302140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_8_p2]
$inst setLocation 190190 318140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_9]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_9_p0]
$inst setLocation 206190 62140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_9_p1]
$inst setLocation 158190 302140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_9_p2]
$inst setLocation 206190 318140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
for {set i 1} {$i <= 10} {incr i} { make_tracks metal$i -x_offset 0.095 -x_pitch 4 -y_offset 0.070 -y_pitch 4 }
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-153/search-custom-tracks.tcl}
foreach name {metal11 metal12} { [[$db getTech] findLayer $name] setRightWayOnGridOnly true }
set_routing_layers -signal metal11-metal12 -clock metal11-metal12
help global_route
help detailed_route
write_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-153/case-2/before.odb}
global_route -use_cugr -guide_file {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-153/case-2/route.guide} -verbose
detailed_route -output_drc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-153/case-2/drc.rpt} -output_maze {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-153/case-2/maze.log} -via_in_pin_bottom_layer metal11 -via_in_pin_top_layer metal11 -verbose 1
write_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-153/case-2/routed.odb}
write_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-153/case-2/routed.def}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/source-153/project/experiments/block_v1/odb_geometry.tcl}
bvgeom::export {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-openroad-preflight-153/case-2/geometry.tsv}
