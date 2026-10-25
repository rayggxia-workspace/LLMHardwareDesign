"""Frozen, bounded research CTS and separately bounded post-CTS repair."""
import argparse,traceback
from common import *
from admission97 import admit
from flow import constraints,timing_reports

def main():
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['cts','ctsrepair']);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--previous',type=Path,required=True);p.add_argument('--previous-receipt',type=Path,required=True);p.add_argument('--candidate',type=int,choices=[1,2],default=1);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);m={'status':'ERROR','stage':a.stage,'source':sources(),'resources':resource_snapshot(),'provisional_gate_pending':True,'raw_gate_reused':True,'postphysical_gate_pending':True,'candidate':a.candidate}
 try:
  need(a.stage=='ctsrepair'or a.candidate==1,'candidate2 only from original CTS baseline repair');hold_margin='0.005'if a.candidate==1 else'0.125';m['repair_hold_margin_ns']=hold_margin
  ad=admit();pm=artifacts(a.prepared);prev=artifacts(a.previous);pr=load(a.previous_receipt/'receipt.json');need(pm['status']=='EXACT_ACCEPTED97_GATE_EXPORT_AND_DECLARED_MEMORY_CUT'and load(a.prepared/'admission.json')==ad,'frozen source admission');need(prev['stage']==('repair'if a.stage=='cts'else'cts')and prev['status']=='ACTUAL97_'+prev['stage'].upper()+'_EXECUTED_NOT_RECEIVED'and prev['prepared_manifest_sha256']==sha(a.prepared/'manifest.json'),'same preceding physical netlist');need(pr['status']=='PASS_RECEPTION_OF_EXECUTED_PHYSICAL_STAGE_NOT_AUTOMATIC_CLOSURE'and pr['result']['stage_manifest_sha256']==sha(a.previous/'manifest.json')and pr['result']['physical_geometry']['status']=='PASS_INDEPENDENT_SITE_BOUNDS_NO_OVERLAP_AND_ALL_SIGNAL_CONNECTIONS','independently received preceding geometry/graph')
  if a.stage=='cts':need(pr['result']['all_declared_internal_timing_electrical_closed']is True,'pre-CTS actual placement all declared constraints closed')
  net=load(a.prepared/'cut.json')['modules']['chain97'];m.update(admission=ad,prepared_directory=str(a.prepared),prepared_manifest_sha256=sha(a.prepared/'manifest.json'),previous_directory=str(a.previous),previous_manifest_sha256=sha(a.previous/'manifest.json'),previous_receipt_sha256=sha(a.previous_receipt/'receipt.json'),config_sha256=sha(HERE/'config.json'),views={str(q):sha(q)for q in(LIB,TECH,LEF,P/'setRC.tcl',P/'make_tracks.tcl',P/'fastroute.tcl')},PG_tap_fill_inserted=False,retiming=False,remove_buffers=False,pin_policy='exact v2 pinmap inherited; no pin regeneration',clock_policy={'root_buffer':'BUF_X4','tree_buffer':'BUF_X4','allowed_buffers':['BUF_X4'],'sink_buffer':'BUF_X4','sink_clustering_size':20,'sink_clustering_max_diameter_um':50,'dummy_loads':False,'propagated':True},automatic_repairs=a.stage=='ctsrepair')
  lines=['set_thread_count 8',f'read_liberty {{{LIB}}}',f'read_db {{{a.previous}/final.odb}}'];(a.out/'constraints-load10.sdc').write_text('\n'.join(constraints(net,10))+'\n');lines += [f'read_sdc {{{a.out}/constraints-load10.sdc}}',f'source {{{P}/setRC.tcl}}','set_routing_layers -signal metal2-metal10 -clock metal4-metal10','estimate_parasitics -placement']
  if a.stage=='cts':
   lines += ['puts "BEGIN_CTS"','clock_tree_synthesis -root_buf BUF_X4 -tree_buf BUF_X4 -buf_list {BUF_X4} -sink_clustering_buffer BUF_X4 -sink_clustering_enable -sink_clustering_size 20 -sink_clustering_max_diameter 50 -dont_use_dummy_load -repair_clock_nets','detailed_placement -max_displacement {5 1}','estimate_parasitics -placement',f'report_cts -out_file {{{a.out}/cts-report.txt}}','puts "END_CTS"']
  lines += ['set_propagated_clock [get_clocks core]']
  if a.stage=='ctsrepair':
   recipe=['repair_design -max_utilization 50 -slew_margin 0 -cap_margin 0 -verbose',f'repair_timing -hold -hold_margin {hold_margin} -max_passes 1 -max_iterations 1 -max_buffer_percent 10 -max_utilization 50 -verbose','repair_design -max_utilization 50 -slew_margin 0 -cap_margin 0 -verbose']
   for i,step in enumerate(recipe,1):lines += [f'puts "BEGIN_CTS_REPAIR_PASS_{i}"',step,'detailed_placement -max_displacement {5 1}','estimate_parasitics -placement','report_design_area','report_check_types -max_slew -max_capacitance -max_delay -min_delay -violators -digits 9',f'puts "END_CTS_REPAIR_PASS_{i}"']
  lines += ['puts "BEGIN_CHECK_PLACEMENT"',f'check_placement -verbose -report_file_name {{{a.out}/placement-check.json}}','puts "END_CHECK_PLACEMENT"','puts "BEGIN_PROPAGATED_CLOCK_REPORT"','report_clock_latency -digits 9','report_clock_skew -setup -digits 9','report_clock_skew -hold -digits 9','puts "END_PROPAGATED_CLOCK_REPORT"',f'write_def {{{a.out}/placed.def}}',f'write_db {{{a.out}/placed.odb}}']
  for k in(1,10):
   for n,d in net['ports'].items():
    if d['direction']=='output':lines += [f'set_load {k} [get_ports {{{n}}}]']
   lines += timing_reports(a.out,k)
  lines += ['report_design_area',f'write_verilog {{{a.out}/final.v}}',f'write_db {{{a.out}/final.odb}}',f'write_sdc -no_timestamp {{{a.out}/final.sdc}}','puts "FLOW_EXECUTION_COMPLETE"'];script=a.out/'flow.tcl';script.write_text(tcl_script(lines));command(a.out,'flow',[OR,'-exit',script],1100)
  ys=a.out/'reparse.ys';ys.write_text(f'read_liberty -lib {LIB}\nread_verilog {a.out}/final.v\nhierarchy -top chain97\ncheck -assert\nwrite_json {a.out}/final.json\ntee -o {a.out}/stat.json stat -liberty {LIB} -json\n');command(a.out,'reparse',['yosys','-s',ys],300);m['status']='ACTUAL97_'+a.stage.upper()+'_EXECUTED_NOT_RECEIVED'
 except Exception as e:m.update(error=str(e),traceback=traceback.format_exc());raise
 finally:manifest(a.out,m)
 print(m['status'])
if __name__=='__main__':main()
