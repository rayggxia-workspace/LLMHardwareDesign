# Actual master pin geometry; no design synthesis, placement or database writes.
read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef
set wanted {BUF_X1 BUF_X2 BUF_X4 BUF_X8 BUF_X16 BUF_X32 CLKBUF_X1 CLKBUF_X2 CLKBUF_X3 ANTENNA_X1}
set pins [open cell-pins.tsv w]
set dimensions [open cell-dimensions.tsv w]
set found {}
foreach library [[ord::get_db] getLibs] {
  foreach master [$library getMasters] {
    set name [$master getName]
    if {$name ni $wanted} {continue}
    if {$name in $found} {error "Duplicate library master $name"}
    lappend found $name
    puts $dimensions "$name\t[$master getWidth]\t[$master getHeight]"
    foreach term [$master getMTerms] {
      if {[$term getSigType] in {POWER GROUND}} {continue}
      foreach pin [$term getMPins] {
        foreach box [$pin getGeometry] {
          if {[$box isVia]} {error "Unsupported via in master signal pin"}
          puts $pins "$name\t[$term getName]\t[$term getIoType]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
        }
      }
    }
  }
}
close $pins
close $dimensions
if {[lsort $found] ne [lsort $wanted]} {error "Missing actual library master"}
