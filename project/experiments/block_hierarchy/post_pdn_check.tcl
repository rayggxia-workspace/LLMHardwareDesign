# The actual mirror's pdn.tcl sources POST_PDN_TCL before writing its ODB.
if { $::env(LLHD_MACRO_PDN) == "legal-m10" } {
  source $::env(LLHD_ATTEMPT)/filter_pg_access.tcl
}
set llhd_pdn_prefix $::env(LLHD_ATTEMPT)/post-pdn
source $::env(LLHD_ATTEMPT)/check_pdn_connectivity.tcl
