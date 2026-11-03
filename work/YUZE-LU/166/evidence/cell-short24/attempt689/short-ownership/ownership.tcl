set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt658/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
set block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron]
set f [open ownership.tsv w]
set bounds [list 550.6800 1137.3600 550.7500 1137.6400]
set net [$block findNet {clknet_leaf_884_clk}]
if {$net eq "NULL"} {error "Short net missing"}
foreach term [$net getITerms] {
 set inst [$term getInst];set b [$inst getBBox];lassign $bounds x0 y0 x1 y1
 if {[$b xMin]>($x1+.5)*$dbu || [$b xMax]<($x0-.5)*$dbu || [$b yMin]>($y1+.5)*$dbu || [$b yMax]<($y0-.5)*$dbu} {continue}
 puts $f [join [list CELL 0 [$net getName] [$net getSigType] [$inst getName] [[$inst getMaster] getName] [[$term getMTerm] getName] [$inst getLocation] [$inst getOrient] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 set code [catch {$term getGeometries} geometries]
 if {$code} {puts $f [join [list API_ERROR $geometries] "	"];continue}
 foreach item $geometries {
  lassign $item lay box
  set code [catch {list [$lay getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]} shape]
  if {$code} {puts $f [join [list API_ERROR $item $shape] "	"]} else {puts $f [join [list PIN [$inst getName] [[$term getMTerm] getName] $shape] "	"]}
 }
}
set net [$block findNet {net17426}]
if {$net eq "NULL"} {error "Short net missing"}
foreach term [$net getITerms] {
 set inst [$term getInst];set b [$inst getBBox];lassign $bounds x0 y0 x1 y1
 if {[$b xMin]>($x1+.5)*$dbu || [$b xMax]<($x0-.5)*$dbu || [$b yMin]>($y1+.5)*$dbu || [$b yMax]<($y0-.5)*$dbu} {continue}
 puts $f [join [list CELL 0 [$net getName] [$net getSigType] [$inst getName] [[$inst getMaster] getName] [[$term getMTerm] getName] [$inst getLocation] [$inst getOrient] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 set code [catch {$term getGeometries} geometries]
 if {$code} {puts $f [join [list API_ERROR $geometries] "	"];continue}
 foreach item $geometries {
  lassign $item lay box
  set code [catch {list [$lay getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]} shape]
  if {$code} {puts $f [join [list API_ERROR $item $shape] "	"]} else {puts $f [join [list PIN [$inst getName] [[$term getMTerm] getName] $shape] "	"]}
 }
}
set bounds [list 555.2400 1106.7350 555.3100 1106.8050]
set net [$block findNet {$abc$862551$new_n312309}]
if {$net eq "NULL"} {error "Short net missing"}
foreach term [$net getITerms] {
 set inst [$term getInst];set b [$inst getBBox];lassign $bounds x0 y0 x1 y1
 if {[$b xMin]>($x1+.5)*$dbu || [$b xMax]<($x0-.5)*$dbu || [$b yMin]>($y1+.5)*$dbu || [$b yMax]<($y0-.5)*$dbu} {continue}
 puts $f [join [list CELL 1 [$net getName] [$net getSigType] [$inst getName] [[$inst getMaster] getName] [[$term getMTerm] getName] [$inst getLocation] [$inst getOrient] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 set code [catch {$term getGeometries} geometries]
 if {$code} {puts $f [join [list API_ERROR $geometries] "	"];continue}
 foreach item $geometries {
  lassign $item lay box
  set code [catch {list [$lay getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]} shape]
  if {$code} {puts $f [join [list API_ERROR $item $shape] "	"]} else {puts $f [join [list PIN [$inst getName] [[$term getMTerm] getName] $shape] "	"]}
 }
}
set net [$block findNet {clknet_leaf_905_clk}]
if {$net eq "NULL"} {error "Short net missing"}
foreach term [$net getITerms] {
 set inst [$term getInst];set b [$inst getBBox];lassign $bounds x0 y0 x1 y1
 if {[$b xMin]>($x1+.5)*$dbu || [$b xMax]<($x0-.5)*$dbu || [$b yMin]>($y1+.5)*$dbu || [$b yMax]<($y0-.5)*$dbu} {continue}
 puts $f [join [list CELL 1 [$net getName] [$net getSigType] [$inst getName] [[$inst getMaster] getName] [[$term getMTerm] getName] [$inst getLocation] [$inst getOrient] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 set code [catch {$term getGeometries} geometries]
 if {$code} {puts $f [join [list API_ERROR $geometries] "	"];continue}
 foreach item $geometries {
  lassign $item lay box
  set code [catch {list [$lay getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]} shape]
  if {$code} {puts $f [join [list API_ERROR $item $shape] "	"]} else {puts $f [join [list PIN [$inst getName] [[$term getMTerm] getName] $shape] "	"]}
 }
}
set bounds [list 555.2400 1106.7350 555.3100 1108.5200]
set net [$block findNet {$abc$862551$new_n312309}]
if {$net eq "NULL"} {error "Short net missing"}
foreach term [$net getITerms] {
 set inst [$term getInst];set b [$inst getBBox];lassign $bounds x0 y0 x1 y1
 if {[$b xMin]>($x1+.5)*$dbu || [$b xMax]<($x0-.5)*$dbu || [$b yMin]>($y1+.5)*$dbu || [$b yMax]<($y0-.5)*$dbu} {continue}
 puts $f [join [list CELL 2 [$net getName] [$net getSigType] [$inst getName] [[$inst getMaster] getName] [[$term getMTerm] getName] [$inst getLocation] [$inst getOrient] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 set code [catch {$term getGeometries} geometries]
 if {$code} {puts $f [join [list API_ERROR $geometries] "	"];continue}
 foreach item $geometries {
  lassign $item lay box
  set code [catch {list [$lay getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]} shape]
  if {$code} {puts $f [join [list API_ERROR $item $shape] "	"]} else {puts $f [join [list PIN [$inst getName] [[$term getMTerm] getName] $shape] "	"]}
 }
}
set net [$block findNet {clknet_leaf_905_clk}]
if {$net eq "NULL"} {error "Short net missing"}
foreach term [$net getITerms] {
 set inst [$term getInst];set b [$inst getBBox];lassign $bounds x0 y0 x1 y1
 if {[$b xMin]>($x1+.5)*$dbu || [$b xMax]<($x0-.5)*$dbu || [$b yMin]>($y1+.5)*$dbu || [$b yMax]<($y0-.5)*$dbu} {continue}
 puts $f [join [list CELL 2 [$net getName] [$net getSigType] [$inst getName] [[$inst getMaster] getName] [[$term getMTerm] getName] [$inst getLocation] [$inst getOrient] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 set code [catch {$term getGeometries} geometries]
 if {$code} {puts $f [join [list API_ERROR $geometries] "	"];continue}
 foreach item $geometries {
  lassign $item lay box
  set code [catch {list [$lay getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]} shape]
  if {$code} {puts $f [join [list API_ERROR $item $shape] "	"]} else {puts $f [join [list PIN [$inst getName] [[$term getMTerm] getName] $shape] "	"]}
 }
}
set bounds [list 555.2400 1137.5000 555.3100 1137.6400]
set net [$block findNet {clknet_leaf_819_clk}]
if {$net eq "NULL"} {error "Short net missing"}
foreach term [$net getITerms] {
 set inst [$term getInst];set b [$inst getBBox];lassign $bounds x0 y0 x1 y1
 if {[$b xMin]>($x1+.5)*$dbu || [$b xMax]<($x0-.5)*$dbu || [$b yMin]>($y1+.5)*$dbu || [$b yMax]<($y0-.5)*$dbu} {continue}
 puts $f [join [list CELL 3 [$net getName] [$net getSigType] [$inst getName] [[$inst getMaster] getName] [[$term getMTerm] getName] [$inst getLocation] [$inst getOrient] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 set code [catch {$term getGeometries} geometries]
 if {$code} {puts $f [join [list API_ERROR $geometries] "	"];continue}
 foreach item $geometries {
  lassign $item lay box
  set code [catch {list [$lay getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]} shape]
  if {$code} {puts $f [join [list API_ERROR $item $shape] "	"]} else {puts $f [join [list PIN [$inst getName] [[$term getMTerm] getName] $shape] "	"]}
 }
}
set net [$block findNet {net14774}]
if {$net eq "NULL"} {error "Short net missing"}
foreach term [$net getITerms] {
 set inst [$term getInst];set b [$inst getBBox];lassign $bounds x0 y0 x1 y1
 if {[$b xMin]>($x1+.5)*$dbu || [$b xMax]<($x0-.5)*$dbu || [$b yMin]>($y1+.5)*$dbu || [$b yMax]<($y0-.5)*$dbu} {continue}
 puts $f [join [list CELL 3 [$net getName] [$net getSigType] [$inst getName] [[$inst getMaster] getName] [[$term getMTerm] getName] [$inst getLocation] [$inst getOrient] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 set code [catch {$term getGeometries} geometries]
 if {$code} {puts $f [join [list API_ERROR $geometries] "	"];continue}
 foreach item $geometries {
  lassign $item lay box
  set code [catch {list [$lay getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]} shape]
  if {$code} {puts $f [join [list API_ERROR $item $shape] "	"]} else {puts $f [join [list PIN [$inst getName] [[$term getMTerm] getName] $shape] "	"]}
 }
}
set bounds [list 555.2400 1137.5350 555.3100 1137.6050]
set net [$block findNet {clknet_leaf_819_clk}]
if {$net eq "NULL"} {error "Short net missing"}
foreach term [$net getITerms] {
 set inst [$term getInst];set b [$inst getBBox];lassign $bounds x0 y0 x1 y1
 if {[$b xMin]>($x1+.5)*$dbu || [$b xMax]<($x0-.5)*$dbu || [$b yMin]>($y1+.5)*$dbu || [$b yMax]<($y0-.5)*$dbu} {continue}
 puts $f [join [list CELL 4 [$net getName] [$net getSigType] [$inst getName] [[$inst getMaster] getName] [[$term getMTerm] getName] [$inst getLocation] [$inst getOrient] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 set code [catch {$term getGeometries} geometries]
 if {$code} {puts $f [join [list API_ERROR $geometries] "	"];continue}
 foreach item $geometries {
  lassign $item lay box
  set code [catch {list [$lay getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]} shape]
  if {$code} {puts $f [join [list API_ERROR $item $shape] "	"]} else {puts $f [join [list PIN [$inst getName] [[$term getMTerm] getName] $shape] "	"]}
 }
}
set net [$block findNet {net14774}]
if {$net eq "NULL"} {error "Short net missing"}
foreach term [$net getITerms] {
 set inst [$term getInst];set b [$inst getBBox];lassign $bounds x0 y0 x1 y1
 if {[$b xMin]>($x1+.5)*$dbu || [$b xMax]<($x0-.5)*$dbu || [$b yMin]>($y1+.5)*$dbu || [$b yMax]<($y0-.5)*$dbu} {continue}
 puts $f [join [list CELL 4 [$net getName] [$net getSigType] [$inst getName] [[$inst getMaster] getName] [[$term getMTerm] getName] [$inst getLocation] [$inst getOrient] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 set code [catch {$term getGeometries} geometries]
 if {$code} {puts $f [join [list API_ERROR $geometries] "	"];continue}
 foreach item $geometries {
  lassign $item lay box
  set code [catch {list [$lay getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]} shape]
  if {$code} {puts $f [join [list API_ERROR $item $shape] "	"]} else {puts $f [join [list PIN [$inst getName] [[$term getMTerm] getName] $shape] "	"]}
 }
}
close $f
