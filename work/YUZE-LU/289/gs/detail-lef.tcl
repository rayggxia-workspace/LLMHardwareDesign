set c $::env(GS_CANDIDATE)
set role $::env(GS_ROLE)
set top block_v2_g
if {$role eq "S"} {set top local_s_base}
set_thread_count 8
read_db $c/candidate.odb
write_abstract_lef $c/abstract-detailed/${top}.lef
puts GS_DETAILED_ABSTRACT_EXPORTED
