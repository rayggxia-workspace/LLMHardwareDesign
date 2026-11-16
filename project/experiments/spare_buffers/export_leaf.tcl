set_thread_count 2
read_db $::env(LEAF_ODB)
set block [ord::get_db_block]
set bounds [$block getDieArea]
puts "LEAF [$block getName] [$block getDbUnitsPerMicron] [$bounds xMin] [$bounds yMin] [$bounds xMax] [$bounds yMax]"
write_def leaf.def
