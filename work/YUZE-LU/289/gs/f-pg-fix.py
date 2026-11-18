"""Reapply original PG landing filtering to a routed new-S parent candidate."""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
src=Path(sys.argv[1]).resolve(); out=src.with_name(src.name+'-pgfix');out.mkdir()
config=(src/'config.mk').read_text();(out/'config.mk').write_text(config)
libs=re.search(r'^export ADDITIONAL_LIBS = (.*)$',config,re.M)[1].split()
platform='/OpenROAD-flow-scripts/flow/platforms/nangate45'
body='set_thread_count 8\n'+''.join('read_liberty {'+p+'}\n' for p in [platform+'/lib/NangateOpenCellLibrary_typical.lib']+libs)
body+=f'''read_db {{{src}/candidate.odb}}
read_sdc {{{src}/candidate.sdc}}
set_propagated_clock [all_clocks]
source /public/home/yuzelu/project-circuit/issue250-cfj-e32-20261111-03/source/project/experiments/cfj_leaf_base/filter_pg_landings.tcl
set macros {{}}
foreach inst [[ord::get_db_block] getInsts] {{
 if {{[[$inst getMaster] getName] in {{local_s_base block_v2_e_compact block_v2_g e_s32_ap64}}}} {{lappend macros [$inst getName]}}
}}
if {{[llength $macros] != 4}} {{error "Unexpected macro selection"}}
pj_filter_pg $macros pg-removed.tsv
write_db candidate.odb
write_def candidate.def
write_verilog candidate.v
write_sdc candidate.sdc
extract_parasitics -ext_model_file {platform}/rcx_patterns.rules
write_spef candidate.spef
read_spef candidate.spef
sta::find_timing
set f [open counts.tsv w]
puts $f "setup\t[sta::endpoint_violation_count max]"
puts $f "hold\t[sta::endpoint_violation_count min]"
foreach kind {{capacitance slew fanout}} {{puts $f "$kind\t[sta::max_${{kind}}_violation_count]"}}
close $f
report_worst_slack -max -digits 9 > setup.rpt
report_worst_slack -min -digits 9 > hold.rpt
check_antennas -report_file antenna.rpt
foreach net {{VDD VSS}} {{if {{[check_power_grid -net $net] ne "1"}} {{error "Incomplete $net"}}}}
drt::check_drc_cmd native-drc.rpt 0 0 0 0 f_pgfix_native
puts F_ECO_CANDIDATE_COMPLETE_NOT_QUALIFIED
'''
(out/'pgfix.tcl').write_text(body)
with (out/'implementation.log').open('w') as f:subprocess.run(['openroad','-no_init','-exit',str(out/'pgfix.tcl')],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(src/'candidate.v')==sha(out/'candidate.v'),'PG-only fix altered logical netlist'
(out/'pgfix-receipt.json').write_text(json.dumps({'logical_netlist_unchanged':True,'source':str(src),'source_sha256':{str(src/f):sha(src/f) for f in ['candidate.odb','candidate.v','candidate.sdc']},'full_qualification_required':True},indent=2))
