read_db $::env(PINXY_ODB)
set b [ord::get_db_block]
foreach inst [$b getInsts] {
 if {![[$inst getMaster] isBlock]} {continue}
 set t [$inst getTransform]
 foreach s [[$inst getMaster] getObstructions] {
  set r [odb::Rect [$s xMin] [$s yMin] [$s xMax] [$s yMax]]
  catch {$t apply $r} e
  puts "APPLY_RESULT $e GLOBAL [$r xMin] [$r yMin] [$r xMax] [$r yMax]"
  break
 }
 break
}
