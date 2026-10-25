"""Actual accepted93 zero-RC/placement diagnostic; no hidden resizing or auto period."""
import argparse,traceback
from common import *
from admission97 import admit

def constraints(net,load_ff):
 x=['create_clock -name core -period 10 [get_ports clk]','set_clock_uncertainty 0 [get_clocks core]','set_clock_transition 0.05 [get_clocks core]']
 for n,p in net['ports'].items():
  if p['direction']=='input'and n!='clk':x += [f'set_input_delay -clock core -max 0.1 [get_ports {{{n}}}]',f'set_input_delay -clock core -min 0 [get_ports {{{n}}}]',f'set_input_transition 0.05 [get_ports {{{n}}}]']
  if p['direction']=='output':x += [f'set_output_delay -clock core -max 0.1 [get_ports {{{n}}}]',f'set_output_delay -clock core -min 0 [get_ports {{{n}}}]',f'set_load {load_ff} [get_ports {{{n}}}]']
 return x

def timing_reports(out,k):
 x=[f'puts "BEGIN_SCENARIO_{k}"','puts "BEGIN_CHECK_SETUP"','check_setup -verbose','puts "END_CHECK_SETUP"','puts "BEGIN_ELECTRICAL_REPORT"','report_check_types -max_slew -max_capacitance -max_fanout -max_delay -min_delay -violators -digits 9','puts "END_ELECTRICAL_REPORT"','report_checks -path_delay min_max -group_path_count 5 -digits 9 -format full_clock_expanded','puts "BEGIN_UNCONSTRAINED"','report_checks -unconstrained -path_delay max -group_path_count 100000','puts "END_UNCONSTRAINED"','set regs [all_registers -clock core -data_pins]','set starts [all_registers -clock core -output_pins]']
 for name,args in [('r2r','-from $starts -to $regs -path_delay max'),('setup','-path_delay max'),('hold','-path_delay min')]:
  x += [f'set f [open {{{out}/{name}-load{k}.tsv}} w]','puts $f "endpoint\tstartpoint\tslack"',f'set paths [find_timing_paths {args} -group_path_count 100000 -endpoint_path_count 1]','foreach path $paths {puts $f "[get_full_name [get_property $path endpoint]]\t[get_full_name [get_property $path startpoint]]\t[get_property $path slack]"}','close $f']
 x += [f'set f [open {{{out}/coverage-load{k}.tsv}} w]','puts $f "name\tvalue"','puts $f "register_data_pins\t[llength $regs]"','puts $f "input_ports\t[llength [all_inputs]]"','puts $f "output_ports\t[llength [all_outputs]]"','close $f',f'puts "END_SCENARIO_{k}"']
 return x

def main():
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['zero','place','repair']);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--gate',type=Path);p.add_argument('--provisional',action='store_true');p.add_argument('--previous',type=Path);p.add_argument('--previous-receipt',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--seconds',type=int,default=1100);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);m={'status':'ERROR','stage':a.stage,'source':sources(),'resources':resource_snapshot()}
 try:
  pm=artifacts(a.prepared);ad=admit();need(pm['status']=='EXACT_ACCEPTED97_GATE_EXPORT_AND_DECLARED_MEMORY_CUT'and load(a.prepared/'admission.json')==ad,'precise actual source for physical stage');net=load(a.prepared/'cut.json')['modules']['chain97'];config=load(HERE/'config.json')
  if a.stage in('place','repair'):
   if a.provisional:
    need(a.gate is None,'provisional scheduling explicitly lacks final gate receipt');m['provisional_gate_pending']=True
   else:
    need(a.gate is not None,'qualified placement requires completed gate qualification');g=load(a.gate/'receipt.json');need(g['status']=='PASS97_EXACT_MAPPED_GATE_AND_ORIGINAL_ORACLE'and sha(a.gate/'receipt.json')==ad['raw_gate_receipt_sha256'],'exact complete gate dependency');m['gate_receipt_sha256']=sha(a.gate/'receipt.json');m['provisional_gate_pending']=False
  m.update(admission=ad,prepared_manifest_sha256=sha(a.prepared/'manifest.json'),prepared_directory=str(a.prepared),config_sha256=sha(HERE/'config.json'),views={str(q):sha(q)for q in(LIB,TECH,LEF,P/'setRC.tcl',P/'make_tracks.tcl',P/'fastroute.tcl')},automatic_repairs=False,retiming=False,remove_buffers=False,PG_tap_fill_inserted=False,pin_policy='v2-all-four-boundaries-M5-M6-two-track-Hungarian'if a.stage!='zero'else'not placed')
  lines=['set_thread_count 8',f'read_lef {{{TECH}}}',f'read_lef {{{LEF}}}',f'read_liberty {{{LIB}}}']
  if a.stage=='repair':
   need(a.previous is not None and a.previous_receipt is not None,'exact executed and received no-repair placement required');prev=artifacts(a.previous);pr=load(a.previous_receipt/'receipt.json');need(prev['status']=='ACTUAL97_PLACE_EXECUTED_NOT_RECEIVED'and prev['prepared_manifest_sha256']==sha(a.prepared/'manifest.json')and pr['result']['stage_manifest_sha256']==sha(a.previous/'manifest.json')and pr['result']['physical_geometry']['status']=='PASS_INDEPENDENT_SITE_BOUNDS_NO_OVERLAP_AND_ALL_SIGNAL_CONNECTIONS','all original placement geometry and source received before repair')
   m.update(previous_directory=str(a.previous),previous_manifest_sha256=sha(a.previous/'manifest.json'),previous_receipt_sha256=sha(a.previous_receipt/'receipt.json'),automatic_repairs=True,repair_recipe='tie-fanout16 then exactly electrical/hold/final-electrical; detailed-placement and same estimatedRC after each, no setup search')
   lines += [f'read_db {{{a.previous}/placed.odb}}']
  else:lines += [f'read_verilog {{{a.prepared}/cut.v}}','link_design chain97','initialize_floorplan -die_area {0 0 448 448} -core_area {24.51 25.2 423.51 424.2} -site FreePDK45_38x28_10R_NP_162NW_34O',f'source {{{P}/make_tracks.tcl}}']
  (a.out/'constraints-load10.sdc').write_text('\n'.join(constraints(net,10))+'\n');lines += [f'read_sdc {{{a.out}/constraints-load10.sdc}}']
  if a.stage=='place':
   lines += [f'place_pins -hor_layers metal5 -ver_layers metal6 -min_distance 2 -min_distance_in_tracks -write_pin_placement {{{a.out}/pinmap.tcl}}','puts "BEGIN_PLACEMENT"','global_placement -density 0.50 -initial_place_max_iter 20','detailed_placement -max_displacement {5 1}','puts "BEGIN_CHECK_PLACEMENT"',f'check_placement -verbose -report_file_name {{{a.out}/placement-check.json}}','puts "END_CHECK_PLACEMENT"',f'source {{{P}/setRC.tcl}}','estimate_parasitics -placement',f'write_db {{{a.out}/placed.odb}}',f'write_def {{{a.out}/placed.def}}','puts "END_PLACEMENT"']
  elif a.stage=='repair':
   lines += [f'source {{{P}/setRC.tcl}}','estimate_parasitics -placement','repair_tie_fanout LOGIC0_X1/Z -max_fanout 16 -verbose','repair_tie_fanout LOGIC1_X1/Z -max_fanout 16 -verbose','detailed_placement -max_displacement {5 1}','estimate_parasitics -placement']
   recipe=['repair_design -max_utilization 50 -slew_margin 0 -cap_margin 0 -verbose','repair_timing -hold -hold_margin 0.005 -max_passes 1 -max_iterations 1 -max_buffer_percent 10 -max_utilization 50 -verbose','repair_design -max_utilization 50 -slew_margin 0 -cap_margin 0 -verbose']
   for i,step in enumerate(recipe,1):lines += [f'puts "BEGIN_REPAIR_PASS_{i}"',step,'detailed_placement -max_displacement {5 1}','estimate_parasitics -placement','report_design_area','report_check_types -max_slew -max_capacitance -max_delay -min_delay -violators -digits 9',f'puts "END_REPAIR_PASS_{i}"']
   lines += ['puts "BEGIN_CHECK_PLACEMENT"',f'check_placement -verbose -report_file_name {{{a.out}/placement-check.json}}','puts "END_CHECK_PLACEMENT"',f'write_db {{{a.out}/placed.odb}}',f'write_def {{{a.out}/placed.def}}']
  else:lines += ['set_wire_rc -signal -resistance 0 -capacitance 0','set_wire_rc -clock -resistance 0 -capacitance 0']
  for k in (1,10):
   for n,d in net['ports'].items():
    if d['direction']=='output':lines += [f'set_load {k} [get_ports {{{n}}}]']
   lines += timing_reports(a.out,k)
  lines += ['report_design_area',f'write_verilog {{{a.out}/final.v}}',f'write_db {{{a.out}/final.odb}}',f'write_sdc -no_timestamp {{{a.out}/final.sdc}}','puts "FLOW_EXECUTION_COMPLETE"']
  script=a.out/'flow.tcl';script.write_text(tcl_script(lines));command(a.out,'flow',[OR,'-exit',script],a.seconds)
  ys=a.out/'reparse.ys';ys.write_text(f'read_liberty -lib {LIB}\nread_verilog {a.out}/final.v\nhierarchy -top chain97\ncheck -assert\nwrite_json {a.out}/final.json\ntee -o {a.out}/stat.json stat -liberty {LIB} -json\n');command(a.out,'reparse',['yosys','-s',ys],300)
  m['status']='ACTUAL97_'+a.stage.upper()+'_EXECUTED_NOT_RECEIVED'
 except Exception as e:m.update(error=str(e),traceback=traceback.format_exc());raise
 finally:manifest(a.out,m)
 print(m['status'])
if __name__=='__main__':main()
