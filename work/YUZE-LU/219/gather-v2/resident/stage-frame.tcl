set_thread_count $::env(SLURM_CPUS_PER_TASK)
set frame $::env(FRAME_SOURCE)
set out $::env(GATHER_STAGE)
set fp [open "$frame/place.tcl" r]
set recipe [read $fp]
close $fp
set boundary [string first "source native-pads.tcl" $recipe]
if {$boundary < 0} {error "Archived placement boundary is missing"}
# Retain exact U39 size, tracks, leaf positions and qualified LEFs.
set recipe [string range $recipe 0 [expr {$boundary-1}]]
set recipe [string map [list \
    "read_lef local_s_base-detail.lef" "read_lef $frame/local_s_base-detail.lef" \
    "read_lef block_v2_e_compact-detail.lef" "read_lef $frame/block_v2_e_compact-detail.lef" \
    "read_verilog mapped.v" "read_verilog $out/mapped.v"] $recipe]
eval $recipe
set m10 [[[ord::get_db] getTech] findLayer metal10]
set p [open "$out/landings.tsv" r]
set ports 0
set seen {}
while {[gets $p row]>=0} {
    lassign [split $row "\t"] name x0 y0 x1 y1
    set term [$block findBTerm $name]
    if {$term eq "NULL" || [llength [$term getBPins]]} {error "Invalid landing $name"}
    if {[string match dma_* $name]} {
        set net [$term getNet]
        if {$net eq "NULL" || ![llength [$net getITerms]] || [llength [$net getBTerms]]!=1} {
            error "Nonindependent or unconnected Gather bit $name"
        }
        dict set seen $name [$net getName]
    }
    set pin [odb::dbBPin_create $term]
    $pin setPlacementStatus FIRM
    odb::dbBox_create $pin $m10 $x0 $y0 $x1 $y1
    incr ports
}
close $p
if {[dict size $seen]!=650} {error "Required 650 distinct DMA boundary signals"}
cut_rows -halo_width_x 3.2 -halo_width_y 3.2
global_placement -skip_io -density 0.38
detailed_placement
check_placement -verbose
write_db "$out/staged-u.odb"
write_def "$out/staged-u.def"
puts "GATHER_CANDIDATE_PLACEMENT preserved=[expr {$ports-650}] dma=650"

