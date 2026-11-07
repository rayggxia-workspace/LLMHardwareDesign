"""Independent MC+16KiB real-PM physical candidate, frozen #180 source."""
import argparse,hashlib,json,os,re,sys,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'compact_local_s'))
import physical as compact

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--candidate',type=int,choices=range(2),required=True);p.add_argument('--reuse-synth',type=Path);p.add_argument('--generation',type=Path,required=True);a=p.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);cpus=int(os.environ['SLURM_CPUS_PER_TASK']);assert cpus in (10,12) and len(os.sched_getaffinity(0))==cpus
 width,height=[(1104,768),(1160,800)][a.candidate];top='mother_control_64'
 generation=json.loads((a.generation/'generation.json').read_text());views={k:Path(generation['views'][k]['path']) for k in compact.BANK_HASHES}
 for k,f in views.items():assert compact.sha(f)==compact.BANK_HASHES[k],(k,f)
 rtl=ROOT/'project/rtl/mother_control_v1';lock=json.loads((rtl/'upstream-lock.json').read_text());
 for name,h in lock['files_sha256'].items():assert compact.sha(rtl/Path(name).name)==h
 mc=(rtl/'mc_min_controller.sv').read_text();mc=re.sub(r'`include "([^"]+)"',lambda m:(rtl/m[1]).read_text(),mc)
 code='\n'.join([mc,(rtl/'control_pm.sv').read_text(),(ROOT/'project/rtl/s_sram/block_feed_s16k_sram.sv').read_text(),(rtl/(top+'.sv')).read_text()]);(out/'input.v').write_text(code)
 ports=[]
 for d,w,n in re.findall(r'(input|output) wire (\[[^\]]+\])?\s*(\w+)',(rtl/'mother_control_64.sv').read_text().split(');',1)[0]):
  b=1 if not w else int(w.strip('[]').split(':')[0])+1
  ports.extend((n if b==1 else f'{n}[{i}]',d) for i in range(b))
 assert len(ports)==2446
 # 2um M10 landings on the common 4um research grid, in four outer
 # bands. Native DRC/access is checked; simultaneous coarse escape is separate.
 slots=[]
 for side in range(4):
  length=height if side<2 else width
  count=int((length-128)//4)
  for band,depth in enumerate((12,28,44,60)):
   for j in range(count):
    along=(.070 if side<2 else .095)+64+j*4
    cross=(.095 if side<2 else .070)+(depth if side%2==0 else (width if side<2 else height)-depth)
    xy=[cross,along] if side<2 else [along,cross];slots.append((j/count,band,side,xy))
 slots.sort();assert len(slots)>=len(ports)
 (out/'pins.tcl').write_text('\n'.join(f'place_pin -pin_name {{{n}}} -layer metal10 -location {{{xy[0]:.3f} {xy[1]:.3f}}} -pin_size {{2 2}}' for (n,d),(_,b,s,xy) in zip(ports,slots))+'\n')
 (out/'input.sdc').write_text('''create_clock -name core -period 3.333333333 [get_ports clk_i]
set_clock_transition 0.05 [get_clocks core]
set_clock_uncertainty -setup 0.05 [get_clocks core]
set_clock_uncertainty -hold 0.02 [get_clocks core]
set inputs [all_inputs -no_clocks]
set_input_delay -max 0.5 -clock core $inputs
set_input_delay -min 0.05 -clock core $inputs
set_input_transition 0.05 $inputs
set_output_delay -max 0.5 -clock core [all_outputs]
set_output_delay -min 0.05 -clock core [all_outputs]
set_load 5.0 [all_outputs]
''')
 commands=[]
 def run(argv,log):
  with (out/log).open('w') as f:r=subprocess.run(list(map(str,argv)),cwd=out,stdout=f,stderr=subprocess.STDOUT)
  commands.append({'argv':list(map(str,argv)),'log':log,'returncode':r.returncode});(out/'commands.json').write_text(json.dumps(commands,indent=2));r.check_returncode()
 compact.make_native(out,top,width,height,60,60,12,.45,views,run,35,.035,True,None)
 (out/'repair-cts.tcl').write_text('''report_checks -path_delay min -group_path_count 8
repair_timing -setup_margin 0.030 -hold_margin 0.035 -repair_tns 100 -max_buffer_percent 50 -verbose
detailed_placement
check_placement -verbose
estimate_parasitics -placement
report_checks -path_delay min_max -group_path_count 8
''')
 cfg=(out/'config.mk').read_text();cfg+='\nexport DONT_USE_CELLS = TAPCELL_X1 FILLCELL_X1 AOI211_X1 OAI211_X1 OAI221_X4\nexport SETUP_SLACK_MARGIN = .030\n'
 cfg+='export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -apply_ndr none -no_insertion_delay -balance_levels -root_buf BUF_X32 -buf_list {BUF_X8 BUF_X16 BUF_X32}\nexport SKIP_CTS_REPAIR_TIMING = 1\nexport POST_CTS_TCL = '+str(out/'repair-cts.tcl')+'\n'
 (out/'config.mk').write_text(cfg)
 receipt={'schema':'mother-native-candidate/1','top':top,'candidate':a.candidate,'die_um':[width,height],'job':os.environ['SLURM_JOB_ID'],'cpus':cpus,'source_commit':lock['commit'],'source_sha256':{str(f.relative_to(ROOT)):compact.sha(f) for f in rtl.iterdir() if f.is_file()},'input_rtl_sha256':compact.sha(out/'input.v'),'bank_sha256':{k:compact.sha(v) for k,v in views.items()},'external_signal_bits':len(ports),'pin_contract':'2um M10 landings in four bands; native access only, simultaneous coarse escape not qualified','qualified':False}
 (out/'inputs.json').write_text(json.dumps(receipt,indent=2)+'\n')
 cmd=['make','-C',compact.FLOW,f'DESIGN_CONFIG={out}/config.mk',f'WORK_HOME={out}/flow',f'NUM_CORES={cpus}','DONT_USE_CELLS=TAPCELL_X1 FILLCELL_X1 AOI211_X1 OAI211_X1 OAI221_X4']
 if a.reuse_synth:
  import shutil
  old=a.reuse_synth.resolve();assert compact.sha(old/'input.v')==compact.sha(out/'input.v'),'Cannot reuse mapped RTL from a different input'
  target=out/'flow/results/nangate45'/top/'base';target.mkdir(parents=True)
  netlist=old/'flow/results/nangate45'/top/'base/1_2_yosys.v';shutil.copyfile(netlist,target/'1_2_yosys.v');shutil.copyfile(out/'input.sdc',target/'1_2_yosys.sdc')
  receipt['reused_synthesis']={'candidate':str(old),'mapped_netlist_sha256':compact.sha(netlist),'input_rtl_sha256':compact.sha(old/'input.v')}
  stages=['do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish','do-gds']
 else:stages=['synth','do-floorplan','do-place','do-cts','do-route','do-finish','do-gds']
 for stage in stages:run(cmd+[stage],stage+'.log')
 receipt['pipeline_completed']=True;(out/'inputs.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
