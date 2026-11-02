from pathlib import Path
import os,json,subprocess,hashlib,re,argparse
p=argparse.ArgumentParser();p.add_argument('--capacity',type=int,choices=[256,1024],required=True);p.add_argument('--mapped',type=Path,required=True);p.add_argument('--die',type=int,required=True);a=p.parse_args()
ROOT=Path.cwd();O=ROOT/'physical';O.mkdir(exist_ok=False)
r=json.loads((a.mapped/'receipt.json').read_text());assert r['passed'] and hashlib.sha256((a.mapped/'mapped.json').read_bytes()).hexdigest()==r['mapped_json_sha256']
raw=(a.mapped/'mapped.v').read_text();(O/'input.v').write_text(re.sub(r'\bwire signed\b','wire',raw))
P=Path(__file__).resolve().parent
(O/'input.sdc').write_bytes((P/'physical.sdc').read_bytes())
(O/'pins.tcl').write_text((P/'physical_pins.tcl').read_text().replace('160.0+4.0','80.0+4.0').replace('3000.0-',str(float(a.die))+'-'))
(O/'config.mk').write_text(f'''export PLATFORM = nangate45
export DESIGN_NAME = r_stream_local
export DESIGN_NICKNAME = r166_{a.capacity}
export VERILOG_FILES = {O}/input.v
export SYNTH_NETLIST_FILES = {O}/input.v
export SDC_FILE = {O}/input.sdc
export DIE_AREA = 0 0 {a.die} {a.die}
export CORE_AREA = 20 20 {a.die-20} {a.die-20}
export PLACE_DENSITY = 0.40
export FOOTPRINT_TCL = {O}/pins.tcl
export KEEP_VARS = 1
export GPL_TIMING_DRIVEN = 0
export ENABLE_PLACE_REPAIR_TIMING = 1
export CAP_MARGIN = 40
export SETUP_SLACK_MARGIN = 0
export HOLD_SLACK_MARGIN = 0.020
export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -apply_ndr none
override export MIN_ROUTING_LAYER = metal1
override export MAX_ROUTING_LAYER = metal10
export VIA_IN_PIN_MIN_LAYER = metal10
export VIA_IN_PIN_MAX_LAYER = metal10
export DETAILED_ROUTE_ARGS = -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5 -via_access_layer metal10
''')
rec={'capacity':a.capacity,'passed':False,'qualification_transferred':False,'mapped_source':str(a.mapped),'mapped_json_sha256':r['mapped_json_sha256'],'source_sha256':r['source_sha256'],'source_functional':r['functional_source']}
rec['input_sdc_sha256']=hashlib.sha256((O/'input.sdc').read_bytes()).hexdigest()
env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16')
cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(O/'config.mk'),'WORK_HOME='+str(O/'flow'),'finish']
with(O/'flow.log').open('w')as f:v=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
rec.update(exit=v.returncode,command=cmd)
(O/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');raise SystemExit(v.returncode)
