import sys,re,os,json,subprocess,hashlib,shutil
from pathlib import Path
from xml.etree import ElementTree as ET
c=Path(sys.argv[1]).resolve();q=c/'qualification';q.mkdir()
assert 'F_ECO_CANDIDATE_COMPLETE_NOT_QUALIFIED' in (c/'implementation.log').read_text()
counts=dict(line.split() for line in (c/'counts.tsv').read_text().splitlines())
assert all(int(v)==0 for v in counts.values()),counts
assert (c/'native-drc.rpt').stat().st_size==0
cfg=(c/'config.mk').read_text();(q/'config.mk').write_text(cfg)
libs=re.search(r'^export ADDITIONAL_LIBS = (.*)$',cfg,re.M)[1].split()
for kind in ('results','objects','reports','logs'):(q/'flow'/kind/'nangate45/f-native-frame/base').mkdir(parents=True)
res=q/'flow/results/nangate45/f-native-frame/base'
for ext in ('odb','def','v','sdc','spef'):shutil.copyfile(c/f'candidate.{ext}',res/f'6_final.{ext}')
def run(args,name):
 with (q/name).open('w') as f:subprocess.run(list(map(str,args)),cwd=q,stdout=f,stderr=subprocess.STDOUT,check=True)
run(['make','-C','/OpenROAD-flow-scripts/flow',f'DESIGN_CONFIG={q}/config.mk',f'WORK_HOME={q}/flow','NUM_CORES=8','do-gds'],'gds.log')
platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45');deck=platform/'drc/FreePDK45.lydrc'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(deck)=='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
run(['klayout','-b','-r',deck,'-rd',f'in_gds={res}/6_final.gds','-rd',f'report_file={q}/full-deck.lyrdb'],'full-deck.log')
items=len(ET.parse(q/'full-deck.lyrdb').findall('.//items/item'))
body='set_thread_count 8\n'+''.join(f'read_liberty {{{p}}}\n' for p in [platform/'lib/NangateOpenCellLibrary_typical.lib']+libs)
body+=f'''read_db {{{c}/candidate.odb}}
read_sdc {{{c}/candidate.sdc}}
read_spef {{{c}/candidate.spef}}
set_propagated_clock [all_clocks]
sta::find_timing
set f [open counts.tsv w]
puts $f "setup\\t[sta::endpoint_violation_count max]"
puts $f "hold\\t[sta::endpoint_violation_count min]"
foreach kind {{capacitance slew fanout}} {{puts $f "$kind\\t[sta::max_${{kind}}_violation_count]"}}
close $f
report_worst_slack -max -digits 9 > setup.rpt
report_worst_slack -min -digits 9 > hold.rpt
report_parasitic_annotation -report_unannotated > annotation.rpt
check_antennas -report_file antenna.rpt
foreach net {{VDD VSS}} {{if {{[check_power_grid -net $net] ne "1"}} {{error "Incomplete $net"}}}}
drt::check_drc_cmd native-drc.rpt 0 0 0 0 f_eco_qualification
write_timing_model -library_name cfj_group_f_tt -cell_name cfj_group_f cfj_group_f.lib
write_abstract_lef cfj_group_f.lef
'''
(q/'verify.tcl').write_text(body)
run(['openroad','-no_init','-exit',q/'verify.tcl'],'verify.log')
independent=dict(line.split() for line in (q/'counts.tsv').read_text().splitlines())
antenna_zero=all(x in (q/'verify.log').read_text() for x in ['Found 0 net violations.','Found 0 pin violations.'])
report=dict(antenna_zero=antenna_zero,physical_passed=antenna_zero and items==0 and (q/'native-drc.rpt').stat().st_size==0 and all(int(v)==0 for v in independent.values()),full_deck_items=items,counts=independent,formal_join_required=True,sha256={str(p):sha(p) for p in [c/'candidate.odb',c/'candidate.v',c/'candidate.sdc',res/'6_final.gds',deck,q/'cfj_group_f.lib',q/'cfj_group_f.lef']})
(q/'receipt.json').write_text(json.dumps(report,indent=2));assert report['physical_passed'],report
