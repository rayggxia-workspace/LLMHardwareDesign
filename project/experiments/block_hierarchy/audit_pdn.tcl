read_db $::env(LLHD_AUDIT_DB)
set llhd_pdn_prefix $::env(LLHD_ATTEMPT)/pdn
source $::env(LLHD_ATTEMPT)/check_pdn_connectivity.tcl
