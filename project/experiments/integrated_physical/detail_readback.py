"""Read exact extracted SPEF in a fresh process and reproduce complete STA."""
import argparse
from common import *
from flow import timing_reports
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);sm=artifacts(a.stage);need(sm['stage']=='drt','actual detailed RCX stage');mods=load(a.stage/'final.json')['modules'];top=next(k for k in mods if k in('chain93','chain97'));net=mods[top]
lines=['set_thread_count 8',f'read_liberty {{{LIB}}}',f'read_db {{{a.stage}/final.odb}}',f'read_sdc {{{a.stage}/final.sdc}}',f'read_spef -coupling_reduction_factor 1.0 {{{a.stage}/route.spef}}',f'set cf [open {{{a.out}/counts.tsv}} w]','puts $cf "load_fF\tmax_slew\tmax_capacitance\tmax_fanout"']
for k in(1,10):
 for n,v in net['ports'].items():
  if v['direction']=='output':lines += [f'set_load {k} [get_ports {{{n}}}]']
 lines+=timing_reports(a.out,k);lines += [f'puts $cf "{k}\t[sta::max_slew_violation_count]\t[sta::max_capacitance_violation_count]\t[sta::max_fanout_violation_count]"']
lines+=['close $cf','puts "EXACT_EXTRACTED_RCX_READBACK_COMPLETE"'];s=a.out/'readback.tcl';s.write_text(tcl_script(lines));command(a.out,'readback',[OR,'-exit',s],300);manifest(a.out,{'status':'EXACT_EXTRACTED_RCX_READBACK_EXECUTED_NOT_RECEIVED','source':sources(),'resources':resource_snapshot(),'stage_directory':str(a.stage),'stage_manifest_sha256':sha(a.stage/'manifest.json'),'inputs':{n:sha(a.stage/n)for n in('final.odb','final.sdc','route.spef','final.json')},'views':{str(q):sha(q)for q in(LIB,TECH,LEF,P/'rcx_patterns.rules')}});print('EXACT_EXTRACTED_RCX_READBACK_EXECUTED_NOT_RECEIVED')
