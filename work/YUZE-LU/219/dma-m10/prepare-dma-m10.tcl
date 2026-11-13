set_thread_count $::env(SLURM_CPUS_PER_TASK)
read_db $::env(NATIVE_DMA_ODB)
set block [ord::get_db_block]
set metal10 [[[ord::get_db] getTech] findLayer metal10]
set grid [$block findTrackGrid $metal10]
proc coords {box} {return [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}
set out [open $::env(NATIVE_DMA_GEOMETRY) w]
puts $out [join [list die {*}[coords [$block getDieArea]]] "\t"]
puts $out [join [list core {*}[coords [$block getCoreArea]]] "\t"]
puts $out "x_grid\t[$grid getGridX]"
puts $out "y_grid\t[$grid getGridY]"
foreach inst [$block getInsts] {
    if {[[$inst getMaster] getType] eq "BLOCK"} {
        puts $out [join [list obstacle {*}[coords [$inst getBBox]]] "\t"]
    }
}
foreach obs [$block getObstructions] {
    if {[$obs getTechLayer] eq $metal10} {
        puts $out [join [list obstacle {*}[coords [$obs getBBox]]] "\t"]
    }
}
foreach net [$block getNets] {
    foreach swire [$net getSWires] {
        foreach shape [$swire getWires] {
            if {[$shape isVia]} {
                set via [$shape getTechVia]
                if {$via eq "NULL"} {set via [$shape getBlockVia]}
                lassign [$shape getViaXY] x y
                foreach box [$via getBoxes] {
                    if {[$box getTechLayer] eq $metal10} {
                        lassign [coords $box] x0 y0 x1 y1
                        puts $out "obstacle\t[expr {$x+$x0}]\t[expr {$y+$y0}]\t[expr {$x+$x1}]\t[expr {$y+$y1}]"
                    }
                }
            } elseif {[$shape getTechLayer] eq $metal10} {
                puts $out [join [list obstacle {*}[coords $shape]] "\t"]
            }
        }
    }
}
foreach term [$block getBTerms] {
    foreach pin [$term getBPins] {
        foreach box [$pin getBoxes] {
            if {[$box getTechLayer] eq $metal10} {
                puts $out [join [list obstacle {*}[coords $box]] "\t"]
            }
        }
    }
}
close $out
