read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/upper_layer_probe/r01/model/research12.tech.lef}
read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef
read_verilog {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/upper_cut_corner_probe/r01/fixture.v}
link_design hpy_cut_fixture
initialize_floorplan -die_area {0 0 50 50} -core_area {1 1 49 49} -site FreePDK45_38x28_10R_NP_162NW_34O
set b [ord::get_db_block];set tech [ord::get_db_tech]
if {[$b getDbUnitsPerMicron]!=2000} {error "Fixture unit mismatch"}
place_pin -pin_name a -layer metal11 -location {20.0 20.0} -pin_size {.8 .8}
set n [[$b findBTerm a] getNet];set w [odb::dbWire_create $n];set e [odb::dbWireEncoder];$e begin $w;$e newPath [$tech findLayer metal11] ROUTED;$e addPoint 40000 40000;$e addTechVia [$tech findVia via11_0];$e end
place_pin -pin_name b -layer metal11 -location {21.6 20.0} -pin_size {.8 .8}
set n [[$b findBTerm b] getNet];set w [odb::dbWire_create $n];set e [odb::dbWireEncoder];$e begin $w;$e newPath [$tech findLayer metal11] ROUTED;$e addPoint 43200 40000;$e addTechVia [$tech findVia via11_0];$e end
write_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/upper_cut_corner_probe/r01/orthogonal_gap_0p8_EXPECT_FAIL/fixture_NOT_SYSTEM.odb}
write_def {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/upper_cut_corner_probe/r01/orthogonal_gap_0p8_EXPECT_FAIL/fixture.def}
set_routing_layers -signal metal11-metal12 -clock metal11-metal12
drt::check_drc -output_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/upper_cut_corner_probe/r01/orthogonal_gap_0p8_EXPECT_FAIL/independent.drc}
