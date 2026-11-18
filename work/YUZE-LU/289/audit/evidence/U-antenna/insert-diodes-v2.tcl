# Source after loading the CURRENT spacing-clean candidate; no original file is mutated.
# Exact guard+antenna v1 residual foundry-antenna net map. Stop on any topology mismatch; do not fall back.
set block [ord::get_db_block]
set master [[ord::get_db] findMaster ANTENNA_X1]
if {$master eq "NULL"} {error "Missing verified ANTENNA_X1 master"}
set plan {
  {{cfg_req_capacity_id_i[21]} {input259} {A} {i289_foundry_ant_r2_0}}
  {{cfg_req_capacity_id_i[29]} {input267} {A} {i289_foundry_ant_r2_1}}
  {{cfg_req_data_i[7]} {hold40057} {A} {i289_foundry_ant_r2_2}}
  {{deploy_generation_i[3]} {input549} {A} {i289_foundry_ant_r2_3}}
  {{dma_rd_rsp_data[128]} {hold40323} {A} {i289_foundry_ant_r2_4}}
  {{dma_rd_rsp_data[161]} {hold39936} {A} {i289_foundry_ant_r2_5}}
  {{dma_rd_rsp_data[187]} {hold39455} {A} {i289_foundry_ant_r2_6}}
  {{dma_rd_rsp_data[18]} {hold44329} {A} {i289_foundry_ant_r2_7}}
  {{dma_rd_rsp_data[284]} {hold39935} {A} {i289_foundry_ant_r2_8}}
  {{dma_rd_rsp_data[297]} {hold39998} {A} {i289_foundry_ant_r2_9}}
  {{dma_rd_rsp_data[419]} {hold39641} {A} {i289_foundry_ant_r2_10}}
  {{dma_rd_rsp_data[58]} {hold44587} {A} {i289_foundry_ant_r2_11}}
  {{dma_rd_rsp_data[97]} {hold42125} {A} {i289_foundry_ant_r2_12}}
  {{task_packet_i[392]} {input2051} {A} {i289_foundry_ant_r2_13}}
  {{task_packet_i[433]} {input2097} {A} {i289_foundry_ant_r2_14}}
}
# Validate the complete plan before editing anything.
foreach spec $plan {
 lassign $spec netname anchorname pinname newname
 set net [$block findNet $netname];set anchor [$block findInst $anchorname]
 if {$net eq "NULL" || $anchor eq "NULL"} {error "Antenna anchor missing: $spec"}
 set term [$anchor findITerm $pinname]
 if {$term eq "NULL" || [$term getNet] ne $net} {error "Antenna anchor topology changed: $spec"}
 if {[$block findInst $newname] ne "NULL"} {error "Antenna instance already exists $newname"}
 foreach t [$net getITerms] {
  if {[[[$t getInst] getMaster] getName] eq "ANTENNA_X1"} {error "Existing diode needs separate physical review: $netname"}
 }
}
set log [open antenna-insertions.tsv w]
foreach spec $plan {
 lassign $spec netname anchorname pinname newname
 set net [$block findNet $netname];set anchor [$block findInst $anchorname]
 lassign [$anchor getLocation] x y
 set diode [odb::dbInst_create $block $master $newname]
 $diode setOrient [$anchor getOrient]
 $diode setLocation [expr {$x+[[$anchor getMaster] getWidth]}] $y
 $diode setPlacementStatus PLACED
 [$diode findITerm A] connect $net
 foreach rail {VDD VSS} {[$diode findITerm $rail] connect [$block findNet $rail]}
 puts $log "$netname\t$newname\t$anchorname\t$pinname\t$x\t$y"
}
close $log
puts "FOUNDRY_ANTENNA_DIODES_INSERTED [llength $plan]; legalization, affected-net routing, extraction, fresh STA, PG, antenna and full foundry GDS signoff still required"
