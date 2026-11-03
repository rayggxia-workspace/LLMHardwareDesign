read_lef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-cugr24phase-preflight-178/technology/research12.tech.lef}
read_lef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-cugr24phase-preflight-178/search-landing-markers.lef}
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
$inst setLocation 302190 270140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_1]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_1_p0]
$inst setLocation 62190 78140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_1_p1]
$inst setLocation 302190 254140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_2]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_2_p0]
$inst setLocation 62190 94140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_2_p1]
$inst setLocation 302190 238140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_3]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_3_p0]
$inst setLocation 62190 110140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_3_p1]
$inst setLocation 302190 222140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_4]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_4_p0]
$inst setLocation 62190 126140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_4_p1]
$inst setLocation 302190 206140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_5]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_5_p0]
$inst setLocation 62190 142140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_5_p1]
$inst setLocation 302190 190140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_6]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_6_p0]
$inst setLocation 62190 158140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_6_p1]
$inst setLocation 302190 174140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_7]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_7_p0]
$inst setLocation 62190 174140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_7_p1]
$inst setLocation 302190 158140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_8]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_8_p0]
$inst setLocation 62190 190140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_8_p1]
$inst setLocation 302190 142140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_9]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_9_p0]
$inst setLocation 62190 206140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_9_p1]
$inst setLocation 302190 126140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_10]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_10_p0]
$inst setLocation 62190 222140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_10_p1]
$inst setLocation 302190 110140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set net [odb::dbNet_create $block bus_11]
set master [$db findMaster search_landing_output]
set inst [odb::dbInst_create $block $master bus_11_p0]
$inst setLocation 62190 238140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set master [$db findMaster search_landing_input]
set inst [odb::dbInst_create $block $master bus_11_p1]
$inst setLocation 302190 94140
$inst setPlacementStatus FIRM
set term [$inst findITerm P]
$term connect $net
set guard_layer [[$db getTech] findLayer metal11]
odb::dbObstruction_create $block $guard_layer 0 0 26190 384000
odb::dbObstruction_create $block $guard_layer 350190 0 384000 384000
odb::dbObstruction_create $block $guard_layer 0 0 384000 26140
odb::dbObstruction_create $block $guard_layer 0 350140 384000 384000
set guard_layer [[$db getTech] findLayer metal12]
odb::dbObstruction_create $block $guard_layer 0 0 26190 384000
odb::dbObstruction_create $block $guard_layer 350190 0 384000 384000
odb::dbObstruction_create $block $guard_layer 0 0 384000 26140
odb::dbObstruction_create $block $guard_layer 0 350140 384000 384000
set cut_layer [[$db getTech] findLayer via11]
for {set x 4} {$x < 44} {incr x} { for {set y 4} {$y < 44} {incr y} {
 if {($x+$y)%2} { set xx [expr {190+8000*$x}]; set yy [expr {140+8000*$y}];
 odb::dbObstruction_create $block $cut_layer [expr {$xx-1}] [expr {$yy-1}] [expr {$xx+1}] [expr {$yy+1}] }
} }
for {set i 1} {$i <= 10} {incr i} { make_tracks metal$i -x_offset 0.095 -x_pitch 1.6 -y_offset 0.070 -y_pitch 1.6 }
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-cugr24phase-preflight-178/search-custom-tracks.tcl}
set_routing_layers -signal metal11-metal12 -clock metal11-metal12
help global_route
help detailed_route
write_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-cugr24phase-preflight-178/case-0/before.odb}
global_route -use_cugr -grid_origin {190 140} -congestion_iterations 50 -guide_file {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-cugr24phase-preflight-178/case-0/route.guide} -verbose
detailed_route -output_drc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-cugr24phase-preflight-178/case-0/drc.rpt} -output_maze {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-cugr24phase-preflight-178/case-0/maze.log} -via_in_pin_bottom_layer metal11 -via_in_pin_top_layer metal11 -verbose 1
write_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-cugr24phase-preflight-178/case-0/routed.odb}
write_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-cugr24phase-preflight-178/case-0/routed.def}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/source-172/project/experiments/block_v1/odb_geometry.tcl}
bvgeom::export {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-cugr24phase-preflight-178/case-0/geometry.tsv}
