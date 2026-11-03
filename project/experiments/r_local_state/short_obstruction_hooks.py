"""Shared routing-hook lifecycle; PRE and POST are sourced in distinct scopes."""
from decimal import Decimal

def hooks(physical,rows,clearance):
 pre='''set here {'''+str(physical)+'''}
set block [ord::get_db_block]
set ::r166_short_obstructions {}
set ::r166_original_obstructions [llength [$block getObstructions]]
set f [open $here/SHORT_TEMP_OBSTRUCTIONS.tsv w]
set dbu [$block getDbUnitsPerMicron]
'''
 for _,_,x0,y0,x1,y1,layer in rows:
  coords=[Decimal(x0)-clearance,Decimal(y0)-clearance,Decimal(x1)+clearance,Decimal(y1)+clearance]
  pre+='set layer [[ord::get_db_tech] findLayer {'+layer+'}]\nif {$layer eq "NULL"} {error "Short layer absent"}\n'
  pre+='set rect [list '+' '.join('[expr {round('+str(c)+'*$dbu)}]'for c in coords)+']\n'
  pre+='''set obs [odb::dbObstruction_create $block $layer {*}$rect]
if {$obs eq "NULL"} {error "Keepout creation failed"}
lappend ::r166_short_obstructions [list $obs $layer $rect]
puts $f "[$obs getId]\t[$layer getName]\t$rect"
'''
 pre+='close $f\nif {[llength [$block getObstructions]]!=$::r166_original_obstructions+[llength $::r166_short_obstructions]} {error "Unexpected obstruction changes"}\n'
 post='''set here {'''+str(physical)+'''}
set block [ord::get_db_block]
foreach row $::r166_short_obstructions {
 lassign $row obs layer rect
 set box [$obs getBBox]
 if {[$box getTechLayer] ne $layer || [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]] ne $rect} {error "Temporary keepout identity changed"}
 odb::dbObstruction_destroy $obs
}
if {[llength [$block getObstructions]]!=$::r166_original_obstructions} {error "Temporary keepout removal incomplete"}
set f [open $here/SHORT_TEMP_OBSTRUCTIONS_REMOVED.tsv w]
puts $f "[llength $::r166_short_obstructions]\t$::r166_original_obstructions\t[llength [$block getObstructions]]"
close $f
'''
 return pre,post
