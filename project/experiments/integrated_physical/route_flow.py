"""One frozen pure global route attempt; no cell/clock/connection transformation."""
import argparse,traceback
from common import *
from flow import constraints,timing_reports

def main():
 p=argparse.ArgumentParser();p.add_argument('--target',type=int,choices=[93,97],required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--previous',type=Path,required=True);p.add_argument('--previous-receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);m={'status':'ERROR','stage':'grt','source':sources(),'resources':resource_snapshot(),'provisional_gate_pending':True}
 try:
  if a.target==93:from admission93 import admit
  else:from admission97 import admit
  ad=admit();pm=artifacts(a.prepared);prev=artifacts(a.previous);pr=load(a.previous_receipt/'receipt.json');top='chain'+str(a.target)
  need(pm['status']=='EXACT_ACCEPTED'+str(a.target)+'_GATE_EXPORT_AND_DECLARED_MEMORY_CUT'and load(a.prepared/'admission.json')==ad,'frozen source admission')
  need(prev['stage']=='ctsrepair'and prev['status']=='ACTUAL'+str(a.target)+'_CTSREPAIR_EXECUTED_NOT_RECEIVED'and type(prev['candidate'])is int and prev['candidate']in(3,4) and prev['prepared_manifest_sha256']==sha(a.prepared/'manifest.json'),'exact C3 source')
  need(pr['status']=='PASS_RECEPTION_OF_EXECUTED_PHYSICAL_STAGE_NOT_AUTOMATIC_CLOSURE'and pr['result']['stage_manifest_sha256']==sha(a.previous/'manifest.json')and pr['result']['all_declared_internal_timing_electrical_closed']is True,'all declared C3 timing/electrical constraints received before routing')
  net=load(a.prepared/'cut.json')['modules'][top]
  m.update(admission=ad,prepared_directory=str(a.prepared),prepared_manifest_sha256=sha(a.prepared/'manifest.json'),previous_directory=str(a.previous),previous_manifest_sha256=sha(a.previous/'manifest.json'),previous_receipt_sha256=sha(a.previous_receipt/'receipt.json'),config_sha256=sha(HERE/'config.json'),views={str(q):sha(q)for q in(LIB,TECH,LEF,P/'setRC.tcl',P/'make_tracks.tcl',P/'fastroute.tcl')},PG_tap_fill_inserted=False,retiming=False,remove_buffers=False,automatic_repairs=False,pin_policy='exact C3 pinmap and placement inherited',routing={'signal_layers':'metal2-metal10','clock_layers':'metal4-metal10','layer_adjustments':{'metal2-metal3':'0.5','metal4-metal10':'0.25'},'congestion_iterations':50,'allow_congestion':False,'allow_infinite_capacity':False,'skip_large_fanout_nets':False,'threads':8,'stage_child_limit_seconds':1100,'RC':'actual global routing with existing platform setRC.tcl; not detailed extraction','PG':'not generated; no PG capacity reservation or signoff'})
  lines=['set_thread_count 8',f'read_liberty {{{LIB}}}',f'read_db {{{a.previous}/final.odb}}']
  (a.out/'constraints-load10.sdc').write_text('\n'.join(constraints(net,10))+'\n');lines += [f'read_sdc {{{a.out}/constraints-load10.sdc}}','set_propagated_clock [get_clocks core]',f'source {{{P}/setRC.tcl}}','set ::env(MAX_ROUTING_LAYER) metal10','set ::env(MIN_ROUTING_LAYER) metal2','set ::env(MIN_CLK_ROUTING_LAYER) metal4',f'source {{{P}/fastroute.tcl}}','puts "BEGIN_GLOBAL_ROUTE"',f'global_route -congestion_iterations 50 -guide_file {{{a.out}/route.guide}} -congestion_report_file {{{a.out}/congestion.rpt}} -verbose','puts "END_GLOBAL_ROUTE"',f'write_global_route_segments {{{a.out}/route.segments}}',f'report_wire_length -net * -global_route -file {{{a.out}/wirelength.csv}}','report_wire_length -global_route -summary','puts "BEGIN_GLOBAL_RC"',f'estimate_parasitics -global_routing -spef_file {{{a.out}/route.spef}}','report_parasitic_annotation -report_unannotated','puts "END_GLOBAL_RC"','puts "BEGIN_CHECK_PLACEMENT"',f'check_placement -verbose -report_file_name {{{a.out}/placement-check.json}}','puts "END_CHECK_PLACEMENT"',f'write_def {{{a.out}/placed.def}}',f'write_db {{{a.out}/placed.odb}}']
  for k in(1,10):
   for n,v in net['ports'].items():
    if v['direction']=='output':lines += [f'set_load {k} [get_ports {{{n}}}]']
   lines += timing_reports(a.out,k)
  lines += [f'write_verilog {{{a.out}/final.v}}',f'write_db {{{a.out}/final.odb}}',f'write_sdc -no_timestamp {{{a.out}/final.sdc}}','puts "FLOW_EXECUTION_COMPLETE"'];s=a.out/'flow.tcl';s.write_text(tcl_script(lines));command(a.out,'flow',[OR,'-exit',s],1100)
  ys=a.out/'reparse.ys';ys.write_text(f'read_liberty -lib {LIB}\nread_verilog {a.out}/final.v\nhierarchy -top {top}\ncheck -assert\nwrite_json {a.out}/final.json\ntee -o {a.out}/stat.json stat -liberty {LIB} -json\n');command(a.out,'reparse',['yosys','-s',ys],300);m['status']='ACTUAL'+str(a.target)+'_GRT_EXECUTED_NOT_RECEIVED'
 except Exception as e:m.update(error=str(e),traceback=traceback.format_exc());raise
 finally:manifest(a.out,m)
 print(m['status'])
if __name__=='__main__':main()
