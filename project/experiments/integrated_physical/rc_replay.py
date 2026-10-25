"""Independent-directory same-tool GRT replay, not independent RC physics."""
import argparse,traceback
from common import *
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);m={'status':'ERROR','source':sources(),'resources':resource_snapshot()}
try:
 sm=artifacts(a.stage);need(sm['stage']in('grt','routerepair','caprepair'),'actual routed estimate source');mods=load(a.stage/'final.json')['modules'];tops=[x for x in mods if x in('chain93','chain97')];need(len(tops)==1,'one actual integrated core');net=mods[tops[0]];m.update(stage_directory=str(a.stage),stage_manifest_sha256=sha(a.stage/'manifest.json'),inputs={n:sha(a.stage/n)for n in('final.odb','final.sdc','route.segments','route.spef','final.json')},views={str(q):sha(q)for q in(LIB,TECH,LEF,P/'setRC.tcl')})
 lines=['set_thread_count 8',f'read_liberty {{{LIB}}}',f'read_db {{{a.stage}/final.odb}}',f'read_sdc {{{a.stage}/final.sdc}}',f'source {{{P}/setRC.tcl}}',f'read_global_route_segments {{{a.stage}/route.segments}}',f'estimate_parasitics -global_routing -spef_file {{{a.out}/replay.spef}}',f'set cf [open {{{a.out}/counts.tsv}} w]','puts $cf "load_fF\tmax_slew\tmax_capacitance\tmax_fanout"']
 for k in(1,10):
  for n,v in net['ports'].items():
   if v['direction']=='output':lines += [f'set_load {k} [get_ports {{{n}}}]']
  lines += [f'puts $cf "{k}\t[sta::max_slew_violation_count]\t[sta::max_capacitance_violation_count]\t[sta::max_fanout_violation_count]"']
 lines+=['close $cf','puts "ACTUAL_GRT_REPLAY_COMPLETE"'];s=a.out/'replay.tcl';s.write_text(tcl_script(lines));command(a.out,'replay',[OR,'-exit',s],300);m.update(status='ACTUAL_GRT_RC_REPLAY_AND_ELECTRICAL_COUNTS_EXECUTED',original_spef_sha256=sha(a.stage/'route.spef'),replayed_spef_sha256=sha(a.out/'replay.spef'),byte_identical=sha(a.stage/'route.spef')==sha(a.out/'replay.spef'))
except Exception as e:m.update(error=str(e),traceback=traceback.format_exc());raise
finally:manifest(a.out,m)
print(m['status'])
