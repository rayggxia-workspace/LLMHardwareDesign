"""Issue88 bounded pre-placement electrical repair, exact cut and inventory."""
import argparse,hashlib,json,subprocess,time,traceback
from pathlib import Path
from probe import ROOT,EDA,DOCKER,ORFS,OR,STA,LIB,TECH,LEF,sha
R86=Path('/public/home/yuzelu/RuizhiLiang/issue86-gate-sta-20261025')
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--variant',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);binding=json.loads((ROOT/'binding.json').read_text());m={'status':'ERROR','variant':a.variant,'source':binding}
 for n,h in binding['sources'].items():
  if sha(ROOT/n)!=h:raise ValueError('source SHA')
 source=R86/f'prepare-v{a.variant}01';pm=json.loads((source/'manifest.json').read_text())
 for e in pm['artifacts']:
  if sha(source/e['path'])!=e['sha256']:raise ValueError('prior artifact SHA')
 cut=json.loads((source/'cut.json').read_text())['modules']['chain84'];inputs=[n for n,p in cut['ports'].items()if p['direction']=='input'and n!='clk'];outputs=[n for n,p in cut['ports'].items()if p['direction']=='output']
 # Lower only explicit 0/1 nets to existing research-library tie cells; charge them.
 ys=a.out/'ties.ys';ys.write_text(f'read_liberty -lib {LIB}\nread_verilog {source}/cut.v\nhierarchy -top chain84\nwrite_json {a.out}/baseline.json\nhilomap -singleton -hicell LOGIC1_X1 Z -locell LOGIC0_X1 Z\ncheck -assert\nwrite_json {a.out}/tied.json\nwrite_verilog -noattr -noexpr {a.out}/tied.v\n')
 prefix=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind',str(EDA)+':/eda:ro','--pwd',str(a.out),str(EDA/'containers/orfs-26Q1-repacked.sif')]
 with (a.out/'ties.log').open('w')as f:tr=subprocess.run([*prefix,'yosys','-s',str(ys)],stdout=f,stderr=subprocess.STDOUT,timeout=120,stdin=subprocess.DEVNULL)
 if tr.returncode:raise ValueError('explicit tie lowering failed')
 lines=[f'read_lef {{{TECH}}}',f'read_lef {{{LEF}}}',f'read_liberty {{{LIB}}}',f'read_verilog {{{a.out}/tied.v}}','link_design chain84','initialize_floorplan -die_area {0 0 400 400} -core_area {0 0 400 400} -site FreePDK45_38x28_10R_NP_162NW_34O','set_wire_rc -signal -resistance 0 -capacitance 0','set_wire_rc -clock -resistance 0 -capacitance 0','create_clock -name core -period 10 [get_ports clk]','set_clock_uncertainty 0 [get_clocks core]','set_clock_transition 0.05 [get_clocks core]']
 for n in inputs:lines += [f'set_input_delay -clock core -max 0.1 [get_ports {{{n}}}]',f'set_input_delay -clock core -min 0 [get_ports {{{n}}}]',f'set_input_transition 0.05 [get_ports {{{n}}}]']
 for n in outputs:lines += [f'set_output_delay -clock core -max 0.1 [get_ports {{{n}}}]',f'set_output_delay -clock core -min 0 [get_ports {{{n}}}]',f'set_load 10 [get_ports {{{n}}}]']
 lines+=['puts "REPAIR_BASELINE"','report_design_area','check_setup -verbose',f'report_check_types -max_slew -max_capacitance -violators > {{{a.out}/electrical-before.rpt}}',f'report_checks -path_delay min_max -group_path_count 5 > {{{a.out}/timing-before.rpt}}','repair_tie_fanout LOGIC0_X1/Z -max_fanout 16 -verbose','repair_tie_fanout LOGIC1_X1/Z -max_fanout 16 -verbose','repair_design -pre_placement -max_utilization 50 -slew_margin 0 -cap_margin 0 -verbose','puts "REPAIR_PASS1"','report_design_area','check_setup -verbose',f'report_check_types -max_slew -max_capacitance -violators > {{{a.out}/electrical-after.rpt}}',f'report_checks -path_delay min_max -group_path_count 5 > {{{a.out}/timing-after.rpt}}','repair_timing -hold -hold_margin 0.005 -max_passes 1 -max_iterations 1 -max_buffer_percent 10 -max_utilization 50 -verbose','puts "REPAIR_PASS2_HOLD"','report_design_area','check_setup -verbose',f'report_check_types -max_slew -max_capacitance -violators > {{{a.out}/electrical-final.rpt}}',f'report_checks -path_delay min_max -group_path_count 5 -digits 9 > {{{a.out}/timing-final.rpt}}',f'write_verilog {{{a.out}/repaired.v}}',f'write_db {{{a.out}/repaired.odb}}']
 script=a.out/'repair.tcl';script.write_text('if {[catch {\n'+'\n'.join(lines)+'\n} msg]} {puts stderr $msg;exit 1}\nexit 0\n')
 cmd=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind',str(EDA)+':/eda:ro','--pwd',str(a.out),str(EDA/'containers/orfs-26Q1-repacked.sif'),str(DOCKER/'lib64/ld-linux-x86-64.so.2'),'--library-path',str(DOCKER/'usr/lib/x86_64-linux-gnu'),str(OR),'-exit',str(script)]
 try:
  start=time.monotonic()
  with (a.out/'repair.log').open('w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=600,stdin=subprocess.DEVNULL)
  m.update(command=cmd,exit=r.returncode,seconds=time.monotonic()-start,prior_prepared_manifest_sha256=sha(source/'manifest.json'),inputs={str(q):sha(q)for q in(LIB,TECH,LEF,OR)})
  if r.returncode:raise ValueError('repair tool failed')
  m['tie_lowering']={'command':[*prefix,'yosys','-s',str(ys)],'status':'EXPLICIT_EXISTING_LIBERTY_TIE_CELLS','library_dont_use_unchanged':True,'tie_fanout_limit':16};m['status']='REPAIR_EXECUTED_NOT_RECEIVED'
 except Exception as e:m['error']=str(e);m['traceback']=traceback.format_exc();raise
 finally:
  m['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in a.out.iterdir()if q.is_file()and q.name!='manifest.json'];put(a.out/'manifest.json',m)
 print(m['status'])
if __name__=='__main__':main()