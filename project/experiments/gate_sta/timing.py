"""Ideal-clock Nangate45 logic timing with explicit storage interface cuts."""
import csv,json
from pathlib import Path

def timing(a,cmd,STA,LIB,put,load,sha):
 prep=load(a.prepared/'manifest.json')
 for e in prep['artifacts']:
  if sha(a.prepared/e['path'])!=e['sha256']:raise ValueError('prepared SHA')
 net=load(a.prepared/'cut.json')['modules']['chain84'];ports=net['ports'];input_names=[n for n,p in ports.items()if p['direction']=='input'and n!='clk'];output_names=[n for n,p in ports.items()if p['direction']=='output']
 fs=[(n,c)for n,c in net['cells'].items()if c['type'].startswith('DFF')];scenarios=[]
 for load_ff in (1,10):
  lines=[f'read_liberty {{{LIB}}}',f'read_verilog {{{a.prepared}/cut.v}}','link_design chain84','create_clock -name core -period 10 [get_ports clk]','set_clock_uncertainty 0 [get_clocks core]','set_clock_transition 0.05 [get_clocks core]']
  for n in input_names:lines += [f'set_input_delay -clock core -max 0.1 [get_ports {{{n}}}]',f'set_input_delay -clock core -min 0 [get_ports {{{n}}}]',f'set_input_transition 0.05 [get_ports {{{n}}}]']
  for n in output_names:lines += [f'set_output_delay -clock core -max 0.1 [get_ports {{{n}}}]',f'set_output_delay -clock core -min 0 [get_ports {{{n}}}]',f'set_load {load_ff} [get_ports {{{n}}}]']
  lines+=['puts "BEGIN_CHECK_SETUP"','check_setup -verbose','puts "END_CHECK_SETUP"','report_checks -path_delay max -group_path_count 5 -format full_clock_expanded','report_checks -unconstrained -path_delay max -group_path_count 5','report_wns','report_tns','report_check_types -max_slew -max_capacitance -violators','set regs [all_registers -clock core -data_pins]','set starts [all_registers -clock core -output_pins]',f'set f [open {{{a.out}/r2r-load{load_ff}.tsv}} w]','puts $f "endpoint\tstartpoint\tslack\tarrival"','set paths [find_timing_paths -from $starts -to $regs -path_delay max -group_path_count 100000 -endpoint_path_count 1]','foreach path $paths {','  set ep [get_full_name [get_property $path endpoint]]','  set sp [get_full_name [get_property $path startpoint]]','  puts $f "$ep\t$sp\t[get_property $path slack]\t[get_property $path arrival]"','}','close $f',f'set f [open {{{a.out}/coverage-load{load_ff}.txt}} w]','puts $f "register_data_pins [llength $regs]"','puts $f "r2r_endpoint_paths [llength $paths]"','puts $f "input_ports [llength [all_inputs]]"','puts $f "output_ports [llength [all_outputs]]"','close $f']
  script='if {[catch {\n'+'\n'.join(lines)+'\n} message]} {puts stderr $message; exit 1}\nexit 0\n'
  path=a.out/f'timing-load{load_ff}.tcl';path.write_text(script);cmd(f'sta-load{load_ff}',[STA,'-exit',path],300)
  rows=list(csv.DictReader((a.out/f'r2r-load{load_ff}.tsv').read_text().splitlines(),delimiter='\t'))
  if not rows:raise ValueError('no analyzed r2r paths')
  endpoints=[r['endpoint']for r in rows]
  if len(set(endpoints))!=len(endpoints):raise ValueError('duplicate timing endpoint')
  worst=min(rows,key=lambda r:float(r['slack']));summary={'output_load_fF':load_ff,'r2r_endpoints_analyzed':len(rows),'mapped_DFF_cells':len(fs),'worst_r2r_path':worst,'ideal_logic_setup_period_bound_ns':10-float(worst['slack']),'coverage_text':(a.out/f'coverage-load{load_ff}.txt').read_text(),'constraints':{'clock_ns':10,'clock_uncertainty_ns':0,'clock_and_input_slew_ns':0.05,'input_output_max_delay_ns':0.1,'input_output_min_delay_ns':0,'parasitics':'none','clock_tree':'ideal','memory':'store82 absent; data/control pins exposed as IO'}}
  scenarios.append(summary)
 put(a.out/'timing-summary.json',{'status':'EXECUTED_DECLARED_CUT_LOGIC_TIMING_REQUIRES_COVERAGE_REVIEW','scenarios':scenarios,'cut':load(a.prepared/'cut-contract.json'),'prepared_manifest_sha256':sha(a.prepared/'manifest.json'),'library_sha256':sha(LIB),'sta_binary_sha256':sha(STA)})
 return scenarios