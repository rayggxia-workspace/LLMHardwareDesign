read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef}
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_verilog {/public/home/yuzelu/PingyangHuang/issue177-s-production-20261104T023042Z/gates/n4/physical/controls/boundary/fixture.v}
link_design revision300_boundary_fixture
read_sdc {/public/home/yuzelu/PingyangHuang/issue177-s-production-20261104T023042Z/gates/n4/physical/controls/boundary/positive-input.sdc}
write_sdc -no_timestamp -digits 12 {/public/home/yuzelu/PingyangHuang/issue177-s-production-20261104T023042Z/gates/n4/physical/controls/boundary/positive-readback.sdc}
