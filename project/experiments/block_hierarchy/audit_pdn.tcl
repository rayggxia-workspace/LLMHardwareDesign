read_db $::env(LLHD_AUDIT_DB)
if { [info exists ::env(LLHD_PG_FILTER_AUDIT)] && $::env(LLHD_PG_FILTER_AUDIT) in {1 2} } {
  source $::env(LLHD_ATTEMPT)/filter_pg_access.tcl
}
set llhd_pdn_prefix $::env(LLHD_ATTEMPT)/pdn
source $::env(LLHD_ATTEMPT)/check_pdn_connectivity.tcl
if { [info exists ::env(LLHD_PG_FILTER_AUDIT)] && $::env(LLHD_PG_FILTER_AUDIT) == 1 } {
  write_db $::env(LLHD_ATTEMPT)/pdn-filtered.odb
}
