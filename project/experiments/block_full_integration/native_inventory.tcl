# Native OpenDB inventory; input database is read-only and output must be fresh.
# Called by native_inventory.py inside an allocated compute job.
namespace eval hpyinv {
  variable channels {}
  variable counts
  array set counts {}
  proc enc {s} {return [string map [list \\ \\\\ \t \\t \n \\n \r \\r] $s]}
  proc row {ch values} {
    set fields {}
    foreach x $values {lappend fields [enc $x]}
    puts $ch [join $fields "\t"]
  }
  proc output {name header} {
    variable channels
    set p [file join $::env(HPY_INVENTORY_OUTPUT) $name]
    if {[file exists $p]} {error "Output exists: $p"}
    set ch [open [list | gzip -n -c > $p] w]
    fconfigure $ch -encoding utf-8 -translation lf -buffering full -buffersize 1048576
    lappend channels $ch
    row $ch $header
    return $ch
  }
  proc rect {b} {return [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]}
  proc value_rect {b} {
    set result [rect $b]
    odb::delete_Rect $b
    return $result
  }
  proc layer {l} {
    if {$l eq "NULL"} {error "Geometry has no technology layer"}
    return [list [$l getName] [$l getType]]
  }
  proc shape {ch kind net sig obj lay box {via ""} {x ""} {y ""}} {
    variable counts
    lassign [layer $lay] lname ltype
    row $ch [list $kind $net $sig $obj $lname $ltype {*}$box $via $x $y]
    set key [list $kind $sig $lname $ltype]
    if {![info exists counts($key)]} {set counts($key) 0}
    incr counts($key)
  }
  proc via {ch kind net sig obj v x y} {
    if {$v eq "NULL"} {error "Missing via definition at $net / $obj"}
    foreach b [$v getBoxes] {
      set bb [list [expr {[$b xMin]+$x}] [expr {[$b yMin]+$y}] [expr {[$b xMax]+$x}] [expr {[$b yMax]+$y}]]
      shape $ch $kind $net $sig $obj [$b getTechLayer] $bb [$v getName] $x $y
    }
  }
  proc run {} {
    variable channels
    variable counts
    if {![info exists ::env(HPY_INVENTORY_ODB)] || ![info exists ::env(HPY_INVENTORY_OUTPUT)]} {
      error "HPY_INVENTORY_ODB and HPY_INVENTORY_OUTPUT required"
    }
    if {![file isdirectory $::env(HPY_INVENTORY_OUTPUT)]} {error "Output directory must be created by adapter"}
    if {[auto_execok gzip] eq ""} {error "gzip unavailable; no uncompressed fallback without space review"}
    read_db $::env(HPY_INVENTORY_ODB)
    set block [ord::get_db_block]
    set tech [ord::get_db_tech]
    set meta [output metadata.tsv.gz {key value}]
    row $meta [list block [$block getName]]
    row $meta [list dbu_per_um [$block getDbUnitsPerMicron]]
    row $meta [list manufacturing_grid_dbu [$tech getManufacturingGrid]]
    row $meta [list technology_name [$tech getName]]
    row $meta [list die_box [value_rect [$block getDieArea]]]
    set layers [output layers.tsv.gz {name type routing_level width spacing pitch_x pitch_y offset_x offset_y direction resistance capacitance}]
    foreach l [$tech getLayers] {
      set extras {}
      foreach method {getWidth getSpacing getPitchX getPitchY getOffsetX getOffsetY getDirection getResistance getCapacitance} {
        if {[catch {$l $method} value]} {set value "UNAVAILABLE:$method"}
        lappend extras $value
      }
      row $layers [list [$l getName] [$l getType] [$l getRoutingLevel] {*}$extras]
    }
    set viaout [output via_definitions.tsv.gz {scope name bottom_layer top_layer layer layer_type x0 y0 x1 y1}]
    foreach spec [list [list TECHNOLOGY [$tech getVias]] [list BLOCK [$block getVias]]] {
      lassign $spec scope definitions
      foreach v $definitions {
        foreach b [$v getBoxes] {
          row $viaout [list $scope [$v getName] [[$v getBottomLayer] getName] [[$v getTopLayer] getName] {*}[layer [$b getTechLayer]] {*}[rect $b]]
        }
      }
    }
    set shapes [output shapes.tsv.gz {kind net sig_type object layer layer_type x0 y0 x1 y1 via via_x via_y}]
    set insts [output instances.tsv.gz {name master master_type x y origin_x origin_y orient status x0 y0 x1 y1}]
    set masters [output masters.tsv.gz {master library master_type width height origin_x origin_y}]
    set mgeom [output master_geometry.tsv.gz {master category term io_type sig_type layer layer_type x0 y0 x1 y1}]
    set iterms [output iterms.tsv.gz {instance master term io_type sig_type net x0 y0 x1 y1}]
    set bterms [output bterms.tsv.gz {term io_type sig_type net pin_count}]
    set nets [output nets.tsv.gz {net sig_type iterm_count bterm_count has_wire special_wire_count}]
    set virtual [output virtual_connections.tsv.gz {net opcode junction_id from_junction}]
    set attachments [output wire_attachments.tsv.gz {net kind term_id x y layer}]
    set seen [dict create]
    foreach inst [$block getInsts] {
      set master [$inst getMaster]
      set mn [$master getName]
      lassign [$inst getLocation] ix iy
      if {[catch {$inst getOrigin} origin]} {set origin {UNAVAILABLE UNAVAILABLE}}
      row $insts [list [$inst getName] $mn [$master getType] $ix $iy {*}$origin [$inst getOrient] [$inst getPlacementStatus] {*}[rect [$inst getBBox]]]
      if {![dict exists $seen $mn]} {
        dict set seen $mn 1
        if {[catch {$master getOrigin} mo]} {set mo {UNAVAILABLE UNAVAILABLE}}
        row $masters [list $mn [[$master getLib] getName] [$master getType] [$master getWidth] [$master getHeight] {*}$mo]
        foreach term [$master getMTerms] {
          foreach pin [$term getMPins] {
            foreach b [$pin getGeometry] {
              row $mgeom [list $mn PIN [$term getName] [$term getIoType] [$term getSigType] {*}[layer [$b getTechLayer]] {*}[rect $b]]
            }
          }
        }
        foreach b [$master getObstructions] {
          row $mgeom [list $mn OBS "" "" "" {*}[layer [$b getTechLayer]] {*}[rect $b]]
        }
      }
      foreach term [$inst getITerms] {
        set mt [$term getMTerm]
        set net [$term getNet]
        set nn ""
        if {$net ne "NULL"} {set nn [$net getName]}
        row $iterms [list [$inst getName] $mn [$mt getName] [$mt getIoType] [$mt getSigType] $nn {*}[value_rect [$term getBBox]]]
      }
    }
    foreach term [$block getBTerms] {
      set net [$term getNet]
      set nn ""
      if {$net ne "NULL"} {set nn [$net getName]}
      set pins [$term getBPins]
      row $bterms [list [$term getName] [$term getIoType] [$term getSigType] $nn [llength $pins]]
      foreach pin $pins {
        foreach b [$pin getBoxes] {
          shape $shapes BPIN $nn [$term getSigType] [$term getName] [$b getTechLayer] [rect $b]
        }
      }
    }
    foreach obs [$block getObstructions] {
      set b [$obs getBBox]
      shape $shapes BLOCK_OBS "" "" [$obs getId] [$b getTechLayer] [rect $b]
    }
    set decoder [odb::dbWireDecoder]
    set net_count 0
    foreach net [$block getNets] {
      set nn [$net getName]
      set sig [$net getSigType]
      set w [$net getWire]
      set swires [$net getSWires]
      row $nets [list $nn $sig [llength [$net getITerms]] [llength [$net getBTerms]] [expr {$w ne "NULL"}] [llength $swires]]
      if {$w ne "NULL"} {
        set previous {}
        set lay "NULL"
        $decoder begin $w
        while {1} {
          set op [$decoder next]
          if {$op == 12} {break}
          set jid [$decoder getJunctionId]
          switch -- $op {
            0 - 1 - 2 - 3 {
              set previous {}
              set lay [$decoder getLayer]
              if {$op == 2 || $op == 3} {row $virtual [list $nn $op $jid [$decoder getJunctionValue]]}
            }
            4 - 5 {
              if {$op == 4} {set p [$decoder getPoint]} else {set p [$decoder getPoint_ext]}
              set xy [lrange $p 0 1]
              if {[llength $previous] && $previous ne $xy} {
                if {[lindex $previous 0] != [lindex $xy 0] && [lindex $previous 1] != [lindex $xy 1]} {error "Non-Manhattan wire: $nn"}
                set s [$w getShape $jid]
                set bb [value_rect [$s getBox]]
                shape $shapes WIRE $nn $sig $jid $lay $bb
                odb::delete_dbShape $s
              }
              set previous $xy
            }
            6 - 7 {
              if {![llength $previous]} {error "Via has no location: $nn"}
              if {$op == 6} {set v [$decoder getVia]} else {set v [$decoder getTechVia]}
              via $shapes WIRE_VIA $nn $sig $jid $v {*}$previous
              set lay [$decoder getLayer]
            }
            8 {
              if {![llength $previous]} {error "Patch has no location: $nn"}
              lassign $previous x y
              set bb [list [expr {$x+[$w getData $jid]}] [expr {$y+[$w getData [expr {$jid+1}]]}] [expr {$x+[$w getData [expr {$jid+2}]]}] [expr {$y+[$w getData [expr {$jid+3}]]}]]
              shape $shapes PATCH $nn $sig $jid $lay $bb
            }
            9 - 10 {
              if {$op == 9} {set p [$decoder getITerm];set k ITERM} else {set p [$decoder getBTerm];set k BTERM}
              row $attachments [list $nn $k [$p getId] {*}$previous [$lay getName]]
            }
            11 {}
            default {error "Unsupported wire opcode: $op"}
          }
        }
      }
      foreach sw $swires {
        foreach b [$sw getWires] {
          if {[$b isVia]} {
            set v [$b getTechVia]
            if {$v eq "NULL"} {set v [$b getBlockVia]}
            via $shapes SPECIAL_VIA $nn $sig [$b getId] $v {*}[$b getViaXY]
          } else {
            # All supplied Nangate designs use rectangular SBoxes. Reject any
            # octilinear representation rather than treating its bbox as exact.
            if {![catch {$b getDirection} direction] && $direction eq "OCTILINEAR"} {error "Unsupported octilinear special wire: $nn"}
            shape $shapes SPECIAL_WIRE $nn $sig [$b getId] [$b getTechLayer] [rect $b]
          }
        }
      }
      incr net_count
      if {$net_count % 50000 == 0} {puts "HPY_NATIVE_NETS $net_count";flush stdout}
    }
    odb::delete_dbWireDecoder $decoder
    set countout [output shape_counts.tsv.gz {kind sig_type layer layer_type count}]
    foreach key [lsort [array names counts]] {row $countout [list {*}$key $counts($key)]}
    row $meta [list net_count $net_count]
    row $meta [list instance_count [llength [$block getInsts]]]
    row $meta [list unique_master_count [dict size $seen]]
    row $meta [list complete true]
    foreach ch $channels {close $ch}
    puts "HPY_NATIVE_COMPLETE $net_count"
  }
}
hpyinv::run
